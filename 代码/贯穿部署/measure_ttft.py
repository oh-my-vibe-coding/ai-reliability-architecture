"""测量 TTFT 与 TPOT（贯穿部署线 Stage 1）。

用法:
  python measure_ttft.py --base-url http://localhost:8000/v1 \
      --model Qwen/Qwen3.8-27B --input-lens 100 1000 4000 --repeat 3

原理:
  请求走 stream=True，记录到第一个内容 chunk 的时间 = TTFT，
  各内容 chunk 之间的时间间隔均值 = TPOT（Time Per Output Token）。
  输入长度用填充文本"凑个量级"，不追求精确——你要看的是趋势，
  不是精确值。
"""
import argparse
import statistics
import time

from openai import OpenAI

FILLER = "这是一段用来把输入凑到目标长度的填充文本。请忽略它的含义。"


def estimate_tokens(text: str) -> int:
    # 中英混排粗略估计：中文约 1-1.5 token/字，英文约 1 token/3-4 字符。
    # 只用于凑量级。
    cjk = sum(1 for c in text if "一" <= c <= "鿿")
    other = len(text) - cjk
    return cjk + other // 4


def measure_once(client, model, n_input, max_tokens):
    n_repeat = max(1, n_input // estimate_tokens(FILLER))
    system = FILLER * n_repeat
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": "把上一句复述一遍。"},
    ]
    t0 = time.perf_counter()
    stream = client.chat.completions.create(
        model=model, messages=messages, max_tokens=max_tokens, stream=True
    )
    chunk_times = []
    for chunk in stream:
        delta = chunk.choices[0].delta.content if chunk.choices else None
        if delta:
            chunk_times.append(time.perf_counter() - t0)
    if not chunk_times:
        return None
    ttft = chunk_times[0]
    tpots = [b - a for a, b in zip(chunk_times, chunk_times[1:])]
    tpot = statistics.mean(tpots) if tpots else float("nan")
    return ttft, tpot, len(chunk_times)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default="http://localhost:8000/v1")
    ap.add_argument("--model", required=True)
    ap.add_argument("--input-lens", nargs="+", type=int, default=[100, 1000, 4000])
    ap.add_argument("--repeat", type=int, default=3)
    ap.add_argument("--max-tokens", type=int, default=64)
    args = ap.parse_args()

    client = OpenAI(base_url=args.base_url, api_key="not-needed")
    print(f"model={args.model}  base_url={args.base_url}\n")
    print(f"{'input_tokens':>12} {'ttft_med(s)':>12} {'tpot_med(s)':>12} {'out_tokens':>10}")
    for n in args.input_lens:
        samples = []
        for _ in range(args.repeat):
            r = measure_once(client, args.model, n, args.max_tokens)
            if r:
                samples.append(r)
        if not samples:
            print(f"{n:>12} {'no-output':>12}")
            continue
        ttft = statistics.median(s[0] for s in samples)
        tpot = statistics.median(s[1] for s in samples)
        out = int(statistics.median(s[2] for s in samples))
        print(f"{n:>12} {ttft:>12.3f} {tpot:>12.3f} {out:>10}")


if __name__ == "__main__":
    main()
