---
title: Unit 2 · Week 2 · 三层 Eval 体系设计
updated: 2026-07-02
tags: [part-4, practice, unit2, week]
---

# Unit 2 · Week 2 · 三层 Eval 体系设计

> [← Unit 2 总览](总览.md)  ·  [← 返回目录](../../README.md)

## 本周目标

为上周选的那个产品的**一个关键能力（capability）**设计完整的**三层 Eval**：L1 Assertion + L2 Judge + L3 A/B。

## 任务清单

### 准备（15 分钟）
- [ ] 选定本周聚焦的**单一 capability**（不要贪多）。例：
  - "从客服对话中抽取投诉原因"
  - "为工单生成 runbook 建议"
  - "给代码做 PR review"
- [ ] 准备 10-20 条**真实或接近真实**的样例数据（脱敏）

### 阅读 · B3 · 45 分钟（无 AI）

**主读**：Langfuse 官方 docs · Evaluators 章节
  - URL: https://langfuse.com/docs/evaluation/overview

**对照读**：OpenAI Evals 仓库 README + 一个 example
  - URL: https://github.com/openai/evals
  - 注：该仓库已停止活跃维护（2026-05 快照 🕒）——读它是为了理解 eval template 的结构范式，不是工具选型对象。

**关注**：
- Langfuse 怎么把 trace 直接变成 eval 样本？
- OpenAI Evals 的"template"是什么、怎么用？
- **两者的 L1 / L2 / L3 分别对应什么？**

### 产出 · B2 · 60-90 分钟

为你选定的 capability 写**设计文档**。

#### Section 1 · L1 Assertion（硬规则）

列出 5-10 条硬规则。每条：

| 规则 | 检查方式 | 失败意味着 |
|---|---|---|
| 输出必须是 valid JSON | `json.loads()` | 解析失败 |
| 字段 `severity` ∈ {low, medium, high} | enum check | 字段污染 |
| 引用文档的 source 必须存在 | 查证是否是已知 source | 虚构来源 |
| 长度 ≤ 500 字 | `len()` check | 啰嗦 |
| 不包含黑名单词（PII / 竞品名）| regex | 内容违规 |

#### Section 2 · L2 Judge（模型评分）

选 1-3 个主维度（不要 > 5）。每个：

```
维度名：relevance / faithfulness / completeness / ...
0-10 分
评分 prompt 草稿：
  "你是一个严格的评委。根据以下标准给出 0-10 分..."
```

**设计 Judge 校准机制**：
- 你打算怎么检查 judge 自己可靠？（Cohen's κ？简单 agreement？）
- 多久校准一次？

#### Section 3 · L3 A/B（线上对比）

- 主指标：thumbs-up / 留存 / 任务完成率 / 其他？
- 副指标：编辑距离 / 后续提问率 / ...
- 统计显著性门槛：样本量 + confidence level
- 分流策略：用户级 / 请求级 / 按分区

#### Section 4 · 三层如何互动

写 150 字：
- L1 失败怎么处理（直接拒绝 / 记录 / 尝试修复）
- L2 低分是否触发 L3？
- L1/L2 的数据是否回流作为 Flywheel 输入？

#### 写完后：AI 挑错

**关键问题**：
- "L1 规则里有没有**过严**的？（正当的语义正确但不合规则的会被误杀）"
- "Judge prompt 有没有隐藏偏见？（偏好长回答 / 礼貌度）"
- "L3 主指标是否真的和业务价值对齐？"

### 预测 · B1 · 每日 5 分钟

本周每次看到 AI 输出时，先猜：
- **"L1 assertion 会不会挂？"**（格式 / 字段）
- "L2 各维度大致多少分？"

周末对比你的猜测和后来的实际 eval 结果。

## 周末自检

- [ ] L1 规则**≥ 5 条**，每条明确可执行
- [ ] L2 Judge 设计**包含校准机制**（不只是"让 LLM 打分"）
- [ ] L3 主指标**和业务 KPI 有对应关系**
- [ ] 三层互动**有回流 Data Flywheel 的设计**
- [ ] 经过至少 1 轮 AI 挑错 + 自己改

**未达标的表现**：
- L1 全是"输出不为空"这种形式
- Judge 没有校准计划 = 盲信
- L3 主指标是"用户满意度" = 没 operationalize
- 三层互相孤立

## 学习科学标注

- **Bloom 层级**：**综合（Create）**
- **关联章节**：[深入 06 · Eval Pipeline](../../深入/06-Eval-Pipeline设计.md)

---

下一步 → [Unit 2 · Week 3 · Judge 模型选型与校准](Week3-Judge模型选型与校准.md)

上一步 → [Unit 2 · Week 1](Week1-Trace-Eval一体化.md)
