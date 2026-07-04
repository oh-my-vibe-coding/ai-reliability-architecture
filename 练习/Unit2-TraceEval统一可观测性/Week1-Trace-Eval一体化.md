---
title: Unit 2 · Week 1 · 理解 "trace = eval dataset" 一体化
updated: 2026-05-05
tags: [part-4, practice, unit2, week]
---

# Unit 2 · Week 1 · 理解 "trace = eval dataset" 一体化

> [← Unit 2 总览](总览.md)  ·  [← 返回目录](../../README.md)

## 本周目标

建立**"生产 trace 本身就是 eval 数据集"**的心智模型——破除"observability 和 quality 是两套东西"的错觉。

## 任务清单

### 准备（15 分钟）
- [ ] 找一个你当前在维护或熟悉的 AI 产品（真实的，不是假想的）
- [ ] 确认能访问它的 trace / log 系统（如果没有，用一个有的项目）

> **贯穿项目读者**：此时项目还没有完整 trace pipeline。**Part 1 trace pipeline 图**画 "as-is"：当前只有 stdout 打印 + 偶尔 commit eval 结果到 markdown，没有持久化。**to-be** 才是本周要设计的（具体落到 `app/trace.py` 在本 Unit W2/W3 实现）。Part 3 重叠分析就分析 as-is 与 to-be 之间的差距。

### 阅读 · B3 · 45 分钟（无 AI）

**主读**：Hamel Husain · 《Your AI Product Needs Evals》前半部分（about 3000 字）
  - URL: https://hamel.dev/blog/posts/evals/

**辅读**（15 分钟）：Anthropic · 《A postmortem of three recent issues》
  - URL: https://www.anthropic.com/engineering/a-postmortem-of-three-recent-issues
  - **从"为什么他们的线下 eval 没发现问题"的角度读**

阅读要求：
- 不开 AI 辅助
- 带问题读：**"作者说的 eval 和我印象中的 eval 有什么不同？"**
- 记录 3 个让你"停顿 > 3 秒"的句子

### 产出 · B2 · 60 分钟

给自己选的那个产品画两张图，然后写结合分析。**不用 AI 代笔**。

#### Part 1 · Trace Pipeline 图

```
[用户请求] → [应用代码] → [?] → [?] → ...
                          ↓
                     [trace 存哪儿]
                          ↓
                     [保留多久]
                          ↓
                     [谁 / 什么时候看]
```

要答出：
- Trace 去哪里（日志系统 / tracing 后端 / 自建）
- 保留 N 天
- 谁看、看什么字段

#### Part 2 · Eval Pipeline 图

同样格式。如果**没有** eval pipeline：

- 标记"我的系统没有 eval pipeline"
- 列出**目前靠什么替代**（用户反馈？人工抽查？线上监控？）
- 这本身是有价值的发现

#### Part 3 · 重叠分析（200 字）

对着两张图写：

1. Trace 里的哪些信息**理论上可以**作为 eval 样本？
2. Eval 里的哪些维度**理论上可以**从 trace 生成？
3. 它们现在是**两套系统**还是**一套系统**？为什么会这样（历史原因？组织原因？）？

#### 写完之后：AI 挑错

把三部分贴给 AI：

> "挑这份分析的漏洞。我有没有把 trace 或 eval 理解错？两套合一遇到的实际难点是什么？"

根据反馈**自己改**（不许 AI 重写）。

### 预测 · B1 · 每日 5 分钟

本周每次在生产看到 issue（bug、质量问题、用户反馈）时，先猜：

- "**这个问题线上 eval 能捕捉到吗？**"
- 猜不到的话 → 缺什么指标？
- 猜能 → 为什么现在没捕捉到？

周末统计：多少次能捕捉、多少次不能。**捕捉不到的占比就是 eval 盲区大小**。

## 周末自检（5 分钟）

- [ ] 能用 2 分钟对同事解释"trace = eval dataset"这个洞察
- [ ] 两张图画完了
- [ ] 重叠分析经过至少 1 轮 AI 挑错 + 自己改
- [ ] 本周 B1 预测"猜不到"的占比知道
- [ ] 能列出自己系统 eval 的 3 个最大盲区

**未达标的表现**：
- 画了图但没做重叠分析（停留在"观察"不到"综合"）
- 认为"观察到的 trace 数据没法做 eval 素材"——这是没想通
- AI 挑错后没真改

## 学习科学标注

- **Bloom 层级**：**分析 + 综合**（不是记忆/理解）
- **对应训练动作**：[B2 主产出] + [B3 无 AI 阅读] + [B1 日常预测]
- **关联章节**：[第 7 章 · 质量可观测性](../../知识/07-质量可观测性与DataFlywheel.md)、[深入 06 · Eval Pipeline](../../深入/06-Eval-Pipeline设计.md)

---

下一步 → [Unit 2 · Week 2 · 三层 Eval 体系设计](Week2-三层Eval体系设计.md)
