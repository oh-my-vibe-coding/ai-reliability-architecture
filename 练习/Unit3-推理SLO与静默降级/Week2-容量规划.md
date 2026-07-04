---
title: Unit 3 · Week 2 · 容量规划（三角约束）
updated: 2026-07-02
tags: [part-4, practice, unit3, week]
---

# Unit 3 · Week 2 · 容量规划（三角约束）

> [← Unit 3 总览](总览.md)  ·  [← 返回目录](../../README.md)

## 本周目标

为本周对象服务做一次**端到端容量规划**（不是抄公式，是**你自己算数字**）。

## 任务清单

### 准备（15 分钟）
- [ ] 搞清楚本服务的**workload 画像**：
  - 平均输入 token 数 p50 / p95（如果没测过，跑 100 条样本）
  - 平均输出 token 数
  - QPS 当前 / 预期峰值
  - 使用的模型 + 量化精度
  - 每个实例 GPU 配置（型号 + 数量）

> **数据从哪来的速查**：
> - **贯穿项目读者**：用 Unit 2 已有的 gold set（30 条）+ smoke set（5 条）= 35 条作为代理样本，p95 取 max + 25% 留 buffer
> - **真实工作场景读者**：grep 一周生产日志的 input/output token 字段；如果还没埋点，先补埋点再回来
> - **完全没有数据的读者**：用 [深入 05 · §7 SRE 助手 worked example](../../深入/05-LLM推理服务的容量规划.md#7-worked-examplesre-事故助手的完整容量规划) 的数字做代练习

### 阅读 · B3 · 45 分钟（无 AI）

**主读**：[深入 05 · LLM 推理服务的容量规划](../../深入/05-LLM推理服务的容量规划.md)
  - 这是对应的理论章节，本周要**反过来用**

**辅读**：NVIDIA H100 或 B200 架构白皮书（任选一个你用的 GPU 档位）
  - https://www.nvidia.com/en-us/data-center/

**重点**：
- 三角约束（HBM × context × QPS）的数学形式
- Prefill 和 Decode 容量的**分开计算**方法
- Prefix caching 对有效容量的放大

### 产出 · B2 · 90-120 分钟

#### Section 1 · Workload 画像

表格化列出：

| 维度 | 当前 | 预期峰值 | 备注 |
|---|---|---|---|
| 并发活跃用户 | | | |
| QPS | | | |
| 平均输入 token (p50/p95) | | | |
| 平均输出 token (p50/p95) | | | |
| 上下文分布 | | | 是否有长尾 |

#### Section 2 · Prefill 容量计算

按 [深入 05](../../深入/05-LLM推理服务的容量规划.md) §4 公式算：

```
Prefill 计算量 ≈ 2 × 参数量 × 输入 token 数
单请求 prefill 时间 = FLOPs / (GPU TFLOPS × 效率)
单卡每秒 prefill 数 = 1 / 单请求时间
```

**算出**：
- 单实例每秒能处理多少 prefill 请求
- 为支撑预期 QPS，需要几个实例
- 如果开 prefix caching，有效乘数是多少

#### Section 3 · Decode 容量计算

```
单用户感知 tokens/s ≤ HBM 带宽 / 模型权重大小   ← 单流上限：每个 decode step 权重只读一次，与 batch 基本无关，随 KV 读取增加缓慢下降
单实例可同时 decode 的用户数 = KV cache 并发数   ← 由 Section 4 算出，不是拿单流上限去除以并发
单实例聚合 tokens/s ≈ 并发数 × 单用户感知 tokens/s   ← 随 batch 近似线性增长，直到 KV 读带宽 / 显存成瓶颈
```

**算出**：
- 单用户感知上限是否满足 20+ tokens/s（不满足 → 换量化 / 换卡，加并发救不了单流速度）
- KV cache 容量允许单实例几个并发（Section 4 的数字）
- 聚合吞吐需求（峰值 QPS × 平均输出 token 数）÷ 单实例聚合 tokens/s → Decode 维度需要几个实例——这是吞吐那条腿，并发那条腿的实例数在 Section 4 算

#### Section 4 · KV Cache 容量校验

```
KV cache per token = 2 × layers × heads × head_dim × bytes
KV cache per request = per_token × avg_context_tokens
单实例可容纳并发 = 可用显存 / KV cache per request
```

**算出**：
- 预期总并发 ÷ 单实例可容纳并发 → KV 并发维度需要几个实例
- 三个容量（Prefill / Decode / KV Cache 并发）各自对应的实例数
- **取 max**——瓶颈在这

#### Section 5 · 对比 max(prefill, decode, kv) + 冗余

决策：
- 3 个数里谁最大？**那是瓶颈**
- 加 30% 冗余应对长尾
- 最终实例数 + 美元/小时预算

#### Section 6 · Long-tail 处理

**关键**：p95 规划 ≠ p99.9 能扛。至少写一条：
- 输入 > 50k token 的请求占多少？
- 这些请求是独立 pool 还是共享？

### AI 挑错

**关键问题**：
- "我的 workload 画像是抽样了多少条？样本是否覆盖长尾？"
- "Prefill 效率我估的是 80%——这个数字对我的硬件 + 模型靠谱吗？"
- "没开 prefix caching 的情况下容量估得对不对？"

### 预测 · B1 · 每日 5 分钟

本周每次看到别人说"我们需要 N 张 GPU"，先猜：
- 他们按**三角**哪一维算的？
- 有没有分 Prefill / Decode？
- 长尾 workload 考虑了吗？

## 周末自检

- [ ] 三个容量（Prefill / Decode / KV）**分别算了数字**（不是笼统估）
- [ ] 总实例数有**依据和冗余**
- [ ] Long-tail 有说法
- [ ] 美元成本估算了

**未达标的表现**：
- 只算了总 QPS × avg latency（传统 web 思维）
- 忽略 KV cache 占用
- 没考虑 prefix caching 放大

## 学习科学标注

- **Bloom 层级**：**应用（Apply）**——用理论公式算真实场景
- **关联章节**：[深入 05](../../深入/05-LLM推理服务的容量规划.md)

---

下一步 → [Unit 3 · Week 3 · 静默降级检测](Week3-静默降级检测.md)

上一步 → [Unit 3 · Week 1](Week1-SLI定义.md)
