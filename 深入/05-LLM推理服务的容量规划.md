---
title: 深入 05 · LLM 推理服务的容量规划
updated: 2026-05-05
tags: [deep-dive, capacity-planning, inference, gpu]
---

# 深入 05 · LLM 推理服务的容量规划

> [← 返回目录](../README.md)  ·  相关：[深入 01 · TTFT 与吞吐](01-首包延迟与吞吐的影响因素.md)  ·  [深入 02 · Prompt Caching](02-Prompt-Caching原理.md)

给 SRE 架构师用的工程手册。传统 web service 的容量规划（QPS × 平均处理时间 = 核数）在 LLM 推理上**完全不够用**。这篇告诉你为什么，以及怎么算。

---

## 0. 为什么 LLM 容量规划是个新学科

传统服务：**QPS 是主变量，内存和 CPU 是资源**。

LLM 推理：**显存、带宽、算力三者共同约束，并且 prefill 和 decode 两阶段完全不同**。

| 维度 | 传统 Web Service | LLM 推理服务 |
|---|---|---|
| 主要资源 | CPU / 内存 | GPU 算力 + HBM + HBM 带宽 |
| 处理时间 | 稳定（ms 级） | 变化 10-1000×（prefill 3s vs decode 300ms）|
| 请求形态 | 固定大小 payload | Token 数可以差 1000× |
| 批处理 | 没必要 | **必须**（continuous batching）|
| 容量建模 | `concurrency = QPS × avg_latency` | 三角约束 |

> [!WARNING]
> 用传统 Web 容量模型算 GPU 集群，**预估会差 3-10 倍**。要么买多了烧钱，要么买少了扛不住。

---

## 1. 三角约束：HBM × Context × QPS

GPU 推理的三个主要资源互相约束：

```mermaid
flowchart TD
    H[HBM 显存<br/>装模型权重 + KV cache + activation]
    C[Context 长度<br/>KV cache 按 token 线性增长]
    Q[QPS 并发<br/>同时活跃的请求数]

    H <-.任二增 第三必减.-> C
    C <-.任二增 第三必减.-> Q
    Q <-.任二增 第三必减.-> H

    style H fill:#fef
    style C fill:#fef
    style Q fill:#fef
```

- **HBM 显存**：装模型权重 + KV cache + activation buffer
- **Context 长度**：每个活跃请求占的 KV cache 随输入 token 数线性增长
- **QPS（并发数）**：同时活跃的请求数

**三角规则**：**任何两个增加 → 第三个必须减**。

### 举个直观例子

- 在 H100 上跑 70B bf16，模型权重占 140GB
- H100 有 80GB HBM → **单卡装不下**，需要 TP=2（两卡共享 140GB 权重，剩余显存放 KV cache）
- 假设每请求 context 2k token，KV cache 约 1.2 GB/请求
- 两卡剩余显存 ~20GB ÷ 1.2 GB = **~16 个并发请求**
- 如果 context 升到 32k，KV cache 变 19.2GB/请求 → **并发跌到 1**

这就是为什么**"1M context"在实际部署中基本用不满**——显存扛不住。

---

## 2. KV Cache 占用：精确公式

这是容量规划的**核心公式**，必须会背：

```
KV cache size per token
  = 2 (K + V)
  × num_layers
  × num_heads
  × head_dim
  × bytes_per_element
```

### 典型模型的 KV cache 大小

| 模型 | 层数 | Heads | Head Dim | 每 token (bf16) |
|---|---|---|---|---|
| Llama 3 8B | 32 | 32 (KV=8 GQA) | 128 | ~0.13 MB |
| Llama 3 70B | 80 | 64 (KV=8 GQA) | 128 | ~0.32 MB |
| Llama 3 405B | 126 | 128 (KV=8 GQA) | 128 | ~0.50 MB |
| GPT-NeoX 20B | 44 | 64 | 96 | ~1.1 MB |

> [!TIP]
> **GQA（Grouped Query Attention）是 KV cache 省钱的秘诀**。Llama 3 用 `KV heads = 8`（不是 64/128），KV cache 立即缩 8-16×。现代模型几乎都用 GQA。

### 一个 context 要多少显存

```
context KV = tokens × per-token size
```

- Llama 3 70B，4k context：4096 × 0.32 MB ≈ **1.3 GB**
- Llama 3 70B，32k context：32768 × 0.32 MB ≈ **10.5 GB**
- Llama 3 70B，128k context：128k × 0.32 MB ≈ **42 GB**（一个用户独占半张 H100）

---

## 3. 单实例极限（Worked Example）

### 场景设定

- 硬件：2× H100（TP=2，共 160GB HBM）
- 模型：Llama 3 70B bf16（140GB 权重）
- 目标：找到单实例最大并发

### 逐项计算

```
总 HBM          : 160 GB
模型权重        : 140 GB
预留（activation / CUDA context / framework buffer）: 8 GB
----------------------------------------------------
KV cache 可用    : 12 GB
```

**场景 A：平均 context 4k token**
- 每请求 KV cache：1.3 GB
- 理论并发：`12 / 1.3 ≈ 9 个请求`
- 实际 vLLM continuous batching + PagedAttention 可做到 ~**12-14**（内存碎片处理更好）

**场景 B：平均 context 32k token**
- 每请求 KV cache：10.5 GB
- 理论并发：`12 / 10.5 ≈ 1 个请求`
- 这是极限——实际只能服务 1-2 并发

**场景 C：混合 context（80% 是 2k 短，20% 是 32k 长）**
- 平均 KV cache per request：`0.8 × 0.65 + 0.2 × 10.5 ≈ 2.6 GB`
- 理论并发：`12 / 2.6 ≈ 4-5 个请求`
- 但**长请求挤占严重**，可能被 preemption

### 引入 Prefix Caching

如果开启 Anthropic / vLLM 式 prefix caching：
- 相同前缀（system prompt + tools + CLAUDE.md，约 14k token）**只占一份**
- 假设 100 个活跃请求共享 **14k × 0.32 MB = 4.5 GB** 前缀
- 剩余显存 `12 - 4.5 = 7.5 GB` 服务**独立部分**
- 每请求独立 context 2k：7.5 / 0.65 ≈ **11-12 并发**
- **有效吞吐提升 2-3×**（看场景）

> [!IMPORTANT]
> 没开启 prefix caching 的容量规划会**高估 2-3×成本**。

---

## 4. Prefill 和 Decode 容量要分开算

### Prefill 容量（Compute-bound）

- **瓶颈**：GPU FLOPs
- **公式**：`FLOPs ≈ 2 × 参数量 × 输入 token 数`
- Llama 3 70B × 4k token ≈ 560 TFLOPs
- H100 bf16 峰值 989 TFLOPS → **每请求 prefill ≈ 0.57s**（理论）
- 实际 80-90% 效率 → **~0.7s**

**容量含义**：
- 单张 H100 每秒能处理约 **1.4 个 4k token 的 prefill**
- 2× H100 TP 约 **2-2.5 个/秒**（通信开销）
- 如果 QPS > 2.5，必须加实例

### Decode 容量（Bandwidth-bound）

- **瓶颈**：HBM 带宽
- **公式**：`tokens/s ≤ HBM bandwidth / model size`
- Llama 3 70B bf16 / H100 TP=2：`3.35 × 2 / 140 ≈ 48 tokens/s 聚合上限`
- 加上 continuous batching，可以让多个请求共享这个带宽

**容量含义**：
- 如果每个用户需要 20 tokens/s 的感知速度
- 单实例最多同时服务 **~2 个用户 decode**（聚合 48 tokens/s 分给 2 个）
- 想要更高并发 → 开 speculative decoding 或加实例

### Prefill ≠ Decode 的意义

服务生命周期有两个阶段，**它们的瓶颈和可服务并发数不同**：

```mermaid
flowchart LR
    R[请求到达] --> P[Prefill 阶段<br/>compute-bound<br/>吃 GPU FLOPs]
    P --> D[Decode 阶段<br/>bandwidth-bound<br/>吃 HBM 带宽]
    D --> OUT[流式输出]

    P -.扩容路径.-> PE[加 FLOPs 大卡<br/>QPS 指标]
    D -.扩容路径.-> DE[加高带宽卡 / spec decode<br/>tokens/s 指标]

    style P fill:#fef
    style D fill:#efe
```

- Prefill 吞吐：QPS 级别
- Decode 吞吐：tokens/s 级别

**这就是为什么 2025-2026 推理服务走向 PD 解耦**（见 [深入 03 · 1.6](03-模型与工具场景化最佳实践.md#16-推理基础设施的三个关键演化)）：prefill 用大卡堆算力，decode 用高带宽卡堆带宽。

---

## 5. 请求形态的影响（重要但常被忽略）

不同业务场景的 token 分布完全不同：

| 场景 | 输入 token | 输出 token | 瓶颈 |
|---|---|---|---|
| Chat 短对话 | 500 | 300 | 均衡 |
| RAG 文档问答 | 8000 | 500 | **Prefill** |
| 代码生成（Claude Code）| 14000 | 2000 | **Prefill** |
| Agent 长任务 | 50000+ | 10000+ | **Decode + KV cache 压力** |
| 总结一本书 | 500000 | 2000 | **Prefill 极限，可能 OOM** |

**做容量规划前，一定要先搞清楚你的 workload 分布**。

### 实用方法：用 p50/p95/p99 而非平均值

如果用平均值（比如"平均输入 5k token"），你会因为**长尾请求**挤爆显存。

建议监控：
- `input_tokens_p50 / p95 / p99`
- `output_tokens_p50 / p95 / p99`
- `total_tokens_per_request_p99`

按 **p95 规划**，p99 作为 preemption 容忍边界。

---

## 6. Autoscaling 的陷阱

LLM 推理的 autoscaling **比 web 服务难 10 倍**。

### 陷阱 1：冷启动很长

- 70B 模型装载：**30s - 数分钟**（从对象存储）
- CUDA warmup + JIT 编译：**数十秒**
- 第一个请求延迟会被 HPA 的 "probe" 误判为"健康"

> [!WARNING]
> 不要用 HPA default。准备好：
> - 最小副本数 ≥ 2（避免 0→1 的超长冷启动影响用户）
> - `minReadySeconds` 和 `initialDelaySeconds` 足够长（>60s）
> - Model weight pin 在本地 SSD / NVMe cache

### 陷阱 2：扩缩容丢缓存

- Scale-down 把实例杀掉 → **prefix cache 全失**
- 新上来的实例 cache 是空的 → **cold period 成本飙升 3-5×**
- 业务高峰后的"凉下来"阶段特别疼

**缓解**：
- Scale-down 要慢（冷却期 10+ 分钟）
- Warm pool / sticky routing

### 陷阱 3：指标滞后

- CPU 利用率在 LLM 场景**没啥意义**（GPU 忙但 CPU 闲）
- 应该看：**GPU utilization、KV cache utilization、queue depth**
- 这些指标从容器内 exporter 拿到 Prometheus 有 30-60s 延迟

**按 queue depth 自动扩容**更有效，因为它直接反映"积压压力"。

### 陷阱 4：按 QPS 扩容很危险

QPS 相同，token 流量可能差 100×。举例：
- 100 QPS × 平均 500 token = 50k token/s
- 100 QPS × 平均 50000 token = 5M token/s（100×）

**按 token 流量规划**，不要按 QPS。

---

## 7. Worked Example：为 100 个活跃用户规划

### 需求
- 100 个活跃用户
- 每人 0.5 QPS（每 2 秒一次请求）
- 每请求 p95 输入 10k token、输出 1k token
- 感知 tokens/s 目标 ≥ 25
- TTFT p99 < 3s

### 步骤 1：prefill 容量

- 总 prefill 负载：`100 × 0.5 × 10k = 500k token/s 的 prefill 流量`
- 单卡 H100 prefill：70B × 10k 约 1.4s × 2 TP = ~0.7s → **每秒 ~1.4 请求**
- 需要实例数：`50 请求/s ÷ 1.4 ≈ 36 个 TP=2 实例` = **72 张 H100**

### 步骤 2：decode 容量

- 总 decode：`50 请求并发 × 25 tokens/s = 1250 tokens/s 聚合`
- 单实例 decode：48 tokens/s（见 §3）
- 实例数：`1250 / 48 ≈ 26 个` = **52 张 H100**

**取 max(36, 26) = 36 个实例 = 72 张 H100**

### 步骤 3：KV cache 校验

- 同时活跃请求数 ≈ 50（高峰期）
- 每实例平均并发：`50 / 36 ≈ 1.4`
- 每请求 10k KV cache ≈ 3.2 GB
- 单实例可用 KV cache：12 GB → ~3-4 并发 ✓（够）

### 步骤 4：余量和韧性

- +30% 冗余应对长尾：**~47 个实例 = 94 张 H100**
- 多可用区部署
- 预留 minReadySeconds、PodDisruptionBudget

### 最终账单（估算）

- 94× H100 on-demand @ ~$3/h = **$282/h = ~$6,800/天 = ~$200k/月**
- Reserved / 年包可降 40-60%
- 同负载用 **DeepSeek V4 Flash API** 托管：**$0.14 × 500k × 3600 / 1M ≈ $250/h**
- **自建 vs 托管**，规模没到千张卡前，托管大概率更便宜

---

## 8. 核心监控指标

### 实例级
- `gpu_utilization` p50/p95
- `kv_cache_usage` / `gpu_memory_usage`
- `preemption_count` 累计和速率
- `queue_depth`（等待调度的请求数）
- `batch_size` 分布

### 请求级
- `ttft_p50 / p95 / p99`
- `output_tokens_per_second_p50 / p95`
- `input_tokens_p50 / p95 / p99`
- `end_to_end_latency_p99`

### 缓存级（如果启用 prefix caching）
- `cache_hit_rate`
- `cache_hit_prefix_length_p50`
- `cache_memory_usage`

### 业务级
- `token_cost_per_user_per_day`
- `failed_request_rate`（timeout / OOM / preemption 被拒）
- `long_tail_request_ratio`（输入 > 50k 的请求占比）

---

## 9. 常见错误

- ❌ **按 QPS 规划**：token 流量才是主变量
- ❌ **用平均值而非 p95**：长尾会爆
- ❌ **忘了 KV cache**：算完权重就以为容量够了
- ❌ **不开 prefix caching**：容量估算虚高 2-3×
- ❌ **只看 GPU 利用率**：HBM 满了但算力闲着，看不出瓶颈
- ❌ **Autoscale 太激进**：冷启动和 cache 丢失惩罚大
- ❌ **单实例而非 TP 配置**：大模型装不下 → OOM
- ❌ **不区分 prefill / decode**：buy too much or too little
- ❌ **忽略长尾输入**：一个 500k 输入的请求能让整个实例卡死

---

## 10. 给 SRE 的一句话总结

> [!IMPORTANT]
> LLM 容量规划 = **三个独立的容量模型叠加**（prefill 吞吐 / decode 吞吐 / KV cache 并发），按 max 取实例数，再加冗余。
>
> 不要复用 web 服务的 `QPS × latency` 心智模型——**那个在这里会差 3-10×**。

---

## 11. 参考资料

- vLLM · Scheduler & PagedAttention 设计文档 — https://docs.vllm.ai/en/latest/
- SGLang · RadixAttention 论文 — https://arxiv.org/abs/2312.07104
- NVIDIA · H100 / H200 / B200 架构白皮书
- 《Efficient Memory Management for LLM Serving with PagedAttention》(vLLM) — https://arxiv.org/abs/2309.06180
- Anyscale · LLM inference benchmarking 系列博客
- Character.AI · Optimizing inference (blog) — 讲如何把单用户成本降到 $0.0001

---

← [深入 04 · 为什么"你好"消耗数万 Token](04-为什么简单你好也消耗数万token.md)  ·  [📖 目录](../README.md)  ·  [深入 06 · Eval Pipeline 设计 →](06-Eval-Pipeline设计.md)
