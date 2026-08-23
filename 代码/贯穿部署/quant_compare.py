"""量化档位对比（贯穿部署线 Stage 5）。

用法:
  python quant_compare.py \
    --base-urls http://localhost:8001/v1,http://localhost:8002/v1,http://localhost:8003/v1 \
    --models Qwen/Qwen3.8-27B,Qwen/Qwen3.8-27B,Qwen/Qwen3.8-27B-AWQ \
    --names bf16,fp8,awq-int4

对同一组 prompt 跑多个端点，比较 TTFT / TPOT / 精确答案是否命中。
质量深挖（分桶 eval）见 科学 03 §5.2，可用 04-eval-skeleton.py 扩展。
"""
import argparse
import statistics
import time

from openai import OpenAI

PROMPTS = [
    "2+2=?",
    '输出一个 JSON：{"用户":"张三","年龄":30}',
    "讲一个 50 字的小故事。",
]
EXPECTED = {  # 精确答案类 prompt 的期望子串
    "2+2=?": "4",
    '输出一个 JSON：{"用户":"张三","年龄":30}': "张三",
}


def run_one(client, model, prompt, max_tokens):
    t0 = time.perf_counter()
    stream = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=max_tokens,
        stream=True,
    )
    out = []
    chunk_times = []
    for chunk in stream:
        delta = chunk.choices[0].delta.content if chunk.choices else None
        if delta:
            out.append(delta)
            chunk_times.append(time.perf_counter() - t0)
    ttft = chunk_times[0] if chunk_times else float("nan")
    tpots = [b - a for a, b in zip(chunk_times, chunk_times[1:])]
    tpot = statistics.mean(tpots) if tpots else float("nan")
    return ttft, tpot, "".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-urls", required=True, help="逗号分隔的端点列表")
    ap.add_argument("--models", required=True, help="逗号分隔的模型名，与端点一一对应")
    ap.add_argument("--names", default=None, help="逗号分隔的标签，默认 instance-0/1/2")
    ap.add_argument("--max-tokens", type=int, default=128)
    args = ap.parse_args()

    urls = args.base_urls.split(",")
    models = args.models.split(",")
    names = args.names.split(",") if args.names else [f"instance-{i}" for i in range(len(urls))]
    if not (len(urls) == len(models) == len(names)):
        ap.error("--base-urls / --models / --names 长度必须一致")

    print(f"{'endpoint':>10} {'prompt':>10} {'ttft(s)':>9} {'tpot(s)':>9} {'exact-ok':>9}")
    for url, model, name in zip(urls, models, names):
        client = OpenAI(base_url=url, api_key="not-needed")
        for prompt in PROMPTS:
            ttft, tpot, text = run_one(client, model, prompt, args.max_tokens)
            expected = EXPECTED.get(prompt)
            ok = "-" if expected is None else ("OK" if expected in text else "MISS")
            print(f"{name:>10} {prompt[:10]:>10} {ttft:>9.3f} {tpot:>9.3f} {ok:>9}")


if __name__ == "__main__":
    main()
