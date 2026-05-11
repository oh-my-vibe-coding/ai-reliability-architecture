---
title: Unit 4 · Week 2 · Verifier / Gate 设计
updated: 2026-05-05
tags: [part-3, practice, unit4, week]
---

# Unit 4 · Week 2 · Verifier / Gate 设计

> [← Unit 4 总览](总览.md)  ·  [← 返回目录](../../README.md)

## 本周目标

**在上周的链路里插入 verifier / gate**，让端到端正确率**可控地提升**，然后重新算数字。

## 任务清单

### 阅读 · B3 · 45 分钟（无 AI）

**主读**：DSPy 官方文档 · Optimizer / Assertion
  - URL: https://dspy.ai/

**辅读**（15 分钟）：一篇讲 Self-Refine 或 Self-Consistency 的论文摘要
  - arXiv 搜 "self-refine LLM"

**重点**：
- Verifier 的几种形式（规则 / 小模型 / 大模型 judge / retrieval 对照）
- 什么样的 verifier 对成本 / 延迟的代价最小
- **何时 verifier 反而让系统更差**（false positive、误杀）

### 产出 · B2 · 60-90 分钟

#### Section 1 · 识别高风险 step

对 W1 的 step 图，标出：
- **最容易错** 的 step（p_i 最低）
- **错了后果最严重**（不可回滚 / blast radius 大）的 step

Verifier 最值得插在这两类交集。

#### Section 2 · Verifier 类型矩阵

| 类型 | 实现 | 代价 | 适合 |
|---|---|---|---|
| **硬规则** | regex / schema / assert | 极低 | 格式 / 结构错误 |
| **检索对照** | 回源查文档 | 低（RAG 复用）| 事实准确性 |
| **小模型 judge** | 用 Haiku / Flash 打分 | 中 | 质量评估 |
| **大模型 judge** | Opus / GPT-5 打分 | 高 | 复杂场景 |
| **执行验证** | 运行 code / SQL 看是否对 | 低（对有工具的场景）| 代码 / 数学 |
| **多路 voting** | N 次生成取多数 | 高（N×）| 关键决策 |

#### Section 3 · 为每个高风险 step 设计 verifier

格式：

```
Step X · <步骤名>
─────────────────
当前 p_i: 0.80
插入 verifier：<类型 + 实现>
  - 预期把 p_i 提升到: 0.92
  - 额外延迟: ~500ms
  - 额外成本: ~$0.0005/req
  - 失败处理: 触发重试 / 降级 / 人工介入
```

至少为 **3 个 step** 设计 verifier。

#### Section 4 · 重算端到端正确率

用新的 p_i 算一次：

```
原始: p1 × p2 × ... × pN
加 gate: p1 × max(p2, verifier_2) × ... 
```

对比：
- 改进了多少？
- 额外代价（成本 / 延迟 / 复杂度）？
- **ROI 是否划算**？

#### Section 5 · Verifier 的失败模式

每个 verifier 自己会失败：

- **False positive**（好回答被误判为坏）→ 用户体验差
- **False negative**（坏回答溜过去）→ verifier 形同虚设
- **Verifier 本身挂了** → 需要 fallback

设计**每个 verifier 的失败处理**：
- 硬失败（完全挂了）：系统 degrade 到什么行为？
- 软失败（准确度下降）：怎么监控发现？

#### Section 6 · Gate 之间的相互作用

多个 verifier 叠加可能：
- **过度保守**（多个 gate 都严，用户请求大量被拒）
- **漏洞相关**（两个 gate 都对同一类错误敏感，另一类全漏）

写 200 字分析这两个风险是否存在，怎么缓解。

### AI 挑错

**关键问题**：
- "我的 verifier 会不会**把正确答案误杀**？测过 false positive rate 吗？"
- "加了 3 个 verifier 延迟 +1.5s，用户真能接受吗？"
- "每个 verifier 真的独立吗？还是它们共享盲点？"

### 预测 · B1 · 每日 5 分钟

本周每次看 Agent 输出，猜：
- "如果这里加一个 verifier，会让结果更好吗？代价多少？"

## 周末自检

- [ ] ≥3 个高风险 step 有 verifier 设计
- [ ] **重算的端到端正确率有数字**
- [ ] 每个 verifier 的**失败处理**设计了
- [ ] 考虑了 verifier 间相互作用的风险

**未达标的表现**：
- 到处加 verifier（过度保守）
- 没算 false positive 代价
- "加 gate 一定更好"的迷信

## 学习科学标注

- **Bloom 层级**：**综合（Create）**
- **关联章节**：[第 4 章](../../知识/04-系统架构与复合AI可靠性数学.md)

---

下一步 → [Unit 4 · Week 3 · 合成评审与失效放大分析](Week3-合成评审.md)

上一步 → [Unit 4 · Week 1](Week1-Step预算与端到端正确率.md)
