---
title: Unit 3 · Week 1 · SLI 定义
updated: 2026-05-05
tags: [part-4, practice, unit3, week]
---

# Unit 3 · Week 1 · SLI 定义（延迟 / 容量 / 质量三类）

> [← Unit 3 总览](总览.md)  ·  [← 返回目录](../../README.md)

## 本周目标

为一个你熟悉的 LLM 推理服务（自建或托管）**写出完整的 SLI 清单**，分三类：**延迟 / 容量 / 质量**。

## 任务清单

### 准备（15 分钟）
- [ ] 选一个推理服务作为本周对象：
  - 自建的（vLLM / SGLang 部署的）
  - 或公司内调的托管 API（把它当黑盒，监控能拿到什么就算什么）
- [ ] 列出能拿到的 metrics（不要先列"应该有"，先列"现在有什么"）

### 阅读 · B3 · 45 分钟（无 AI）

**主读**：Anthropic · 《A postmortem of three recent issues》
  - URL: https://www.anthropic.com/engineering/a-postmortem-of-three-recent-issues
  - **这一轮重点看"哪些指标原本应该早捕捉到"**

**辅读**：vLLM docs · metrics / observability 章节
  - URL: https://docs.vllm.ai/en/latest/
  - 看它暴露了什么 Prometheus 指标

**关注**：
- 三类 SLI 各有什么代表性指标？
- 为什么 TTFT 和 tokens/s 必须分开看？（回顾 [深入 01](../../深入/01-首包延迟与吞吐的影响因素.md)）
- 哪些指标是"**状态**"哪些是"**速率**"？

### 产出 · B2 · 60-90 分钟

写 **SLI 设计文档**。

#### Section 1 · 延迟类 SLI

至少 **4 个**：

| SLI | 定义 | 测量位置 | 目标 | 备注 |
|---|---|---|---|---|
| TTFT p50 / p95 / p99 | 首 token 延迟分位数 | 客户端侧计时 | 对话类 p99 < 1s | ... |
| tokens/s p50 / p95 | 输出速度分位数 | 客户端每 token 间隔 | 取决于模型 | |
| End-to-end latency p99 | 整个请求 | 客户端 | 业务对齐 | |
| Queue wait time | 等调度时间 | 服务端 | < batch_size × avg_step | |

**注意**：每个 SLI 标注**是客户端测还是服务端测**——两端数字不同。

#### Section 2 · 容量类 SLI

至少 **4 个**：

| SLI | 定义 | 目标 | 告警阈值 |
|---|---|---|---|
| KV cache utilization | 显存占比 | < 85% | > 95% |
| Queue depth | 排队请求数 | < 2× batch_size | > 5× |
| GPU util | 算力利用率 | ... | ... |
| Preemption rate | 抢占频率 | < 1% | > 5% |
| Active concurrency | 同时服务数 | ... | ... |
| Input size p99 | 输入长度分位 | 监控漂移 | 突增 2× |

#### Section 3 · 质量类 SLI（最容易忽略）

至少 **3 个**：

| SLI | 定义 | 实现 |
|---|---|---|
| 任务专属 assertion 通过率 | L1 检查通过比例 | 见 Unit 2 |
| Judge 评分均值（按任务类型分桶）| L2 分数 | 见 Unit 2 |
| 输出长度分布 | 每任务类型的 p50 / p99 | 突变报警 |

**关键**：**按任务类型分桶**，不要只看全局。

#### Section 4 · 这些指标的关联（150 字）

- 哪些指标会**同步变化**（一起好 / 一起坏）？
- 哪些指标会**反向变化**（一个好代表另一个会坏）？
  - 例：cache hit rate 低 → TTFT 飙升
  - 例：tokens/s 高通常意味着 batch size 大 → TTFT 不稳

### AI 挑错

**关键问题**：
- "我的质量类 SLI 真的可**机械测量**吗，还是需要人工？"
- "延迟 SLI 是客户端测还是服务端测？两者都有指标吗？"
- "我遗漏了哪些 dark metrics？"

### 预测 · B1 · 每日 5 分钟

本周每次查看现有监控仪表盘，猜：
- "这个指标突变时，我的哪些 SLI 会先反应？"
- "如果 SLI X 变坏，根因最可能在哪个组件？"

## 周末自检

- [ ] 三类 SLI 各 ≥ 规定数量
- [ ] **每个 SLI 有目标值 + 测量方式**（不是"越小越好"）
- [ ] 明确**客户端测 vs 服务端测**的区别
- [ ] 关联分析至少 3 对
- [ ] 经过 AI 挑错 + 自己改

**未达标的表现**：
- SLI 没有目标值 = 没法 operationalize
- 全部从服务端拿（丢了客户端视角）
- 质量 SLI 是"用户满意度"这种抽象词

## 学习科学标注

- **Bloom 层级**：**分析（Analyze）+ 应用（Apply）**
- **关联章节**：[第 5 章](../../知识/05-AI推理服务的可靠性工程.md)、[深入 01](../../深入/01-首包延迟与吞吐的影响因素.md)

---

下一步 → [Unit 3 · Week 2 · 容量规划（三角约束）](Week2-容量规划.md)
