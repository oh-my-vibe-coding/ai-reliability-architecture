---
title: Unit 2 · Week 3 · Judge 模型选型与校准
updated: 2026-05-05
tags: [part-4, practice, unit2, week]
---

# Unit 2 · Week 3 · Judge 模型选型与校准

> [← Unit 2 总览](总览.md)  ·  [← 返回目录](../../README.md)

## 本周目标

**不盲信 Judge**——本周设计 Judge 模型的可信度监测和校准流程。

## 任务清单

### 准备（15 分钟）
- [ ] 用上周设计的 L2 Judge prompt
- [ ] 从你的 10-20 条样例里挑 20 条（这次只要 20）

### 阅读 · B3 · 45 分钟（无 AI）

**主读**：Eugene Yan · 《Evaluating Long-form Responses with LLM Judges》
  - URL: https://eugeneyan.com/writing/llm-evaluators/

**辅读**（15 分钟）：查一篇 Judge-Human agreement 的研究论文摘要
  - arXiv 搜 "LLM-as-judge calibration"

**重点记录**：
- 不同 Judge 模型的**家族偏见**（OpenAI 家偏好哪种回答？Claude 家呢？）
- Cohen's κ vs Pearson / Spearman 三者的差异
- Position bias、length bias、self-preference 是什么

### 产出 · B2 · 60-90 分钟

#### Part 1 · 人工打分（30 分钟）

**关键步骤**：你**亲自**给 20 条样例打分（只打 L2 的主维度，比如 relevance 0-10）。

- 用 **纸笔或纯 spreadsheet**，不要让 AI 看
- 打完之后**封存**你的分数

#### Part 2 · Judge 打分（5 分钟）

跑你设计的 L2 Judge 让它给同样 20 条打分。记录结果。

#### Part 3 · 对齐度计算（15 分钟）

算三种指标：

1. **Agreement rate**：`|human - judge| ≤ 1` 的比例
2. **Cohen's κ**（可选，更严格）
3. **Bias**：`mean(judge) - mean(human)`——正则 Judge 比你松；负则严

目标参考：
- Agreement rate ≥ 70% = 可用
- κ ≥ 0.6 = 适度一致
- |bias| < 1 = 无系统偏移

#### Part 4 · 选型决策（20 分钟）

如果当前 Judge 对齐不好，尝试：

| 调整 | 代价 | 建议 |
|---|---|---|
| 换**不同家族的模型**做 Judge | 低（改 model 参数）| 最常用 |
| 多家投票 | 中（成本 × 2-3）| 重要场景 |
| 改 prompt（加更多例子、更严规则）| 低 | 先试 |
| 换 rubric（不打 0-10 打 high/mid/low）| 中 | 简化会提升 κ |

设计**你的校准 SOP**：
- 每 N 周校准一次
- 每次抽 M 条
- κ 跌破多少时触发人工介入
- 如何存证校准结果（可追溯）

#### Part 5 · 常见偏见自检

对照你的 Judge prompt，自问：

- [ ] **Length bias**：如果改长回答，会被打更高分吗？
- [ ] **Position bias**：对比两个回答时，哪个在前会赢？
- [ ] **Self-preference**：用 Claude 判 Claude 输出会高分吗？
- [ ] **Style bias**：是否偏爱特定格式（列表 / markdown / 完整句）？

至少识别出 **1 个自己 Judge 有的偏见**，并给出缓解方案。

### AI 挑错

**挑战问题**：
- "我的校准方法有没有 **N 太小** 的问题？20 条样本能得出稳定 κ 吗？"
- "我识别的偏见清单有遗漏吗？"

### 预测 · B1 · 每日 5 分钟

本周每次看到 LLM 做的打分（不限于你的 Judge），先猜：
- "这个分数是客观的还是带偏见？"
- "如果让人打，会不会差 ±1 以上？"

## 周末自检

- [ ] Agreement rate 或 Cohen's κ **算出来了数字**（不是"大概差不多"）
- [ ] 识别出 **≥1 个偏见**
- [ ] 写出了校准 SOP
- [ ] 如果对齐度差（<60%），至少**试了 1 种调整**再重测

**未达标的表现**：
- 没有人工打分（直接跳 Judge）→ 没有基线怎么校准
- 盲信 Judge 高分
- 偏见分析停在"LLM 可能有偏见"这种空话

## 学习科学标注

- **Bloom 层级**：**评估（Evaluate）**——对 Judge 本身进行评估
- **关联章节**：[深入 06 · §2](../../深入/06-Eval-Pipeline设计.md)

---

下一步 → [Unit 2 · Week 4 · 合成方案 + Data Flywheel](Week4-合成方案与Flywheel.md)

上一步 → [Unit 2 · Week 2](Week2-三层Eval体系设计.md)
