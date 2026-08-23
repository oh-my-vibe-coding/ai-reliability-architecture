---
title: 贯穿部署线 · 参考脚本
updated: 2026-08-23
tags: [code, reference, deployment]
---

# 贯穿部署线 · 参考脚本

> [← 代码 README](../README.md)

配合 [贯穿部署线 · H20 推理服务](../../练习/贯穿部署-H20推理服务.md) 使用。所有脚本是最小可运行参考实现，优化可读性而非性能，**Copy 过去改造用**。

## 依赖

```bash
pip install openai requests
```

## 脚本

| 文件 | 作用 | 对应 Stage |
|---|---|---|
| [measure_ttft.py](measure_ttft.py) | 同一问题在不同输入长度下测 TTFT / TPOT | Stage 1 |
| [bench_concurrency.py](bench_concurrency.py) | 多档并发压测：吞吐、聚合 tokens/s、TTFT / TPOT 分位 | Stage 2 / 6 |
| [prefix_cache_hit.py](prefix_cache_hit.py) | 同前缀不同尾巴，比较第 1 次 vs 第 2+ 次的 TTFT | Stage 4 |
| [quant_compare.py](quant_compare.py) | 多端点（bf16 / FP8 / int4）跑同一组 prompt 对比 | Stage 5 |

## 用法速查

```bash
# Stage 1 · 输入长度对 TTFT 的影响
python measure_ttft.py --base-url http://localhost:8000/v1 \
  --model Qwen/Qwen3.8-27B --input-lens 100 1000 4000 --repeat 3

# Stage 2 · 并发压测
python bench_concurrency.py --base-url http://localhost:8000/v1 \
  --model Qwen/Qwen3.8-27B --concurrency 1 4 8 16 --max-tokens 256

# Stage 4 · 前缀缓存命中
python prefix_cache_hit.py --base-url http://localhost:8000/v1 \
  --model Qwen/Qwen3.8-27B --prefix-len 2000 --rounds 6

# Stage 5 · 量化档位对比（三个实例各起一档）
python quant_compare.py \
  --base-urls http://localhost:8001/v1,http://localhost:8002/v1,http://localhost:8003/v1 \
  --models Qwen/Qwen3.8-27B,Qwen/Qwen3.8-27B,Qwen/Qwen3.8-27B-AWQ \
  --names bf16,fp8,awq-int4
```

> [!NOTE]
> 输入长度用填充文本"凑量级"，不追求精确 token 数——脚本要的是**趋势**（TTFT 随输入变长、第 2 次请求 TTFT 断崖），不是精确测量。
>
> 生产使用前必做：加错误处理、加日志、加超时。范本见[代码 README 使用原则](../README.md#使用原则)。

---

[📖 目录](../../README.md)
