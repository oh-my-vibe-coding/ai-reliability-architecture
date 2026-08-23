"""前缀缓存命中实验（贯穿部署线 Stage 4）。

用法:
  python prefix_cache_hit.py --base-url http://localhost:8000/v1 \
      --model Qwen/Qwen3.8-27B --prefix-len 2000 --rounds 6

对比: 第 1 次（未命中）vs 第 2+ 次（命中）的 TTFT。
同前缀、不同 user 尾巴。vLLM V1 引擎默认开启 prefix caching。
"""
import argparse
import time

import requests
from openai import OpenAI

PREFIX_TEXT = "下面是一段产品说明，请记住其中的要点："  # 重复拼成长前缀


def fetch_hit_rate(base_url):
    # /metrics 挂在根路径，不在 /v1 下
    metrics_url = base_url.rstrip("/").replace("/v1", "") + "/metrics"
    try:
        metrics = requests.get(metrics_url, timeout=2).text
        for line in metrics.splitlines():
            if line.startswith("vllm:prefix_cache_hit_rate"):
                return line.split()[-1]
    except Exception:
        pass
    return "n/a"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default="http://localhost:8000/v1")
    ap.add_argument("--model", required=True)
    ap.add_argument("--prefix-len", type=int, default=2000)
    ap.add_argument("--rounds", type=int, default=6)
    args = ap.parse_args()

    n_repeat = max(1, args.prefix_len // 15)  # 每行 PREFIX_TEXT 约 15 token
    system = PREFIX_TEXT * n_repeat
    client = OpenAI(base_url=args.base_url, api_key="not-needed")

    print(f"prefix ~{args.prefix_len} tokens, rounds={args.rounds}\n")
    print(f"{'round':>6} {'ttft(s)':>10}  备注")
    for i in range(args.rounds):
        tail = f"问题 {i + 1}：总结一下这段说明。"
        t0 = time.perf_counter()
        stream = client.chat.completions.create(
            model=args.model,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": tail}],
            max_tokens=32,
            stream=True,
        )
        ttft = None
        for chunk in stream:
            delta = chunk.choices[0].delta.content if chunk.choices else None
            if delta:
                ttft = time.perf_counter() - t0
                break
        note = "未命中（前缀第一次见）" if i == 0 else "命中（同前缀）"
        print(f"{i + 1:>6} {ttft:>10.3f}  {note}" if ttft else f"{i + 1:>6} {'no-output':>10}  {note}")

    print(f"\nprefix_cache_hit_rate = {fetch_hit_rate(args.base_url)}")


if __name__ == "__main__":
    main()
