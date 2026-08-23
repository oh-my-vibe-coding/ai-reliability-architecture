"""并发压测：吞吐与延迟权衡（贯穿部署线 Stage 2 / 6）。

用法:
  python bench_concurrency.py --base-url http://localhost:8000/v1 \
      --model Qwen/Qwen3.8-27B --concurrency 1 4 8 16 --max-tokens 256

对每个并发档输出:
  - 吞吐（requests/s）、聚合 tokens/s
  - TTFT p50 / p95、TPOT p50 / p95
画成"并发 × 延迟 × 吞吐"曲线，就是容量规划的原始数据。
"""
import argparse
import statistics
from concurrent.futures import ThreadPoolExecutor
import time

from openai import OpenAI

USER_MSG = "讲一个三分钟能讲完的、关于数据中心的故事。"


def run_one(base_url, model, max_tokens, results, idx):
    client = OpenAI(base_url=base_url, api_key="not-needed")
    t0 = time.perf_counter()
    stream = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": USER_MSG}],
        max_tokens=max_tokens,
        stream=True,
    )
    chunk_times = []
    for chunk in stream:
        delta = chunk.choices[0].delta.content if chunk.choices else None
        if delta:
            chunk_times.append(time.perf_counter() - t0)
    tpots = [b - a for a, b in zip(chunk_times, chunk_times[1:])]
    results[idx] = {
        "ttft": chunk_times[0] if chunk_times else float("nan"),
        "tokens": len(chunk_times),
        "tpot": statistics.mean(tpots) if tpots else float("nan"),
        "wall": time.perf_counter() - t0,
    }


def pct(sorted_vals, q):
    if not sorted_vals:
        return float("nan")
    return sorted_vals[min(int(q * len(sorted_vals)), len(sorted_vals) - 1)]


def bench_once(base_url, model, concurrency, max_tokens, n_requests):
    results = [None] * n_requests
    with ThreadPoolExecutor(max_workers=concurrency) as ex:
        futs = [
            ex.submit(run_one, base_url, model, max_tokens, results, i)
            for i in range(n_requests)
        ]
        for f in futs:
            f.result()
    ttfts = sorted(r["ttft"] for r in results)
    tpots = sorted(r["tpot"] for r in results)
    total_tokens = sum(r["tokens"] for r in results)
    wall = max(r["wall"] for r in results)
    return {
        "concurrency": concurrency,
        "req_per_s": n_requests / wall,
        "tok_per_s": total_tokens / wall,
        "ttft_p50": pct(ttfts, 0.5),
        "ttft_p95": pct(ttfts, 0.95),
        "tpot_p50": pct(tpots, 0.5),
        "tpot_p95": pct(tpots, 0.95),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default="http://localhost:8000/v1")
    ap.add_argument("--model", required=True)
    ap.add_argument("--concurrency", nargs="+", type=int, default=[1, 4, 8, 16])
    ap.add_argument("--requests", type=int, default=40, help="每个并发档的请求总数")
    ap.add_argument("--max-tokens", type=int, default=256)
    args = ap.parse_args()

    print(f"model={args.model}  requests/concurrency={args.requests}\n")
    print(f"{'conc':>5} {'req/s':>7} {'tok/s':>9} {'ttft_p50':>9} {'ttft_p95':>9} {'tpot_p50':>9} {'tpot_p95':>9}")
    for c in args.concurrency:
        r = bench_once(args.base_url, args.model, c, args.max_tokens, args.requests)
        print(
            f"{c:>5} {r['req_per_s']:>7.2f} {r['tok_per_s']:>9.1f} "
            f"{r['ttft_p50']:>9.3f} {r['ttft_p95']:>9.3f} "
            f"{r['tpot_p50']:>9.3f} {r['tpot_p95']:>9.3f}"
        )


if __name__ == "__main__":
    main()
