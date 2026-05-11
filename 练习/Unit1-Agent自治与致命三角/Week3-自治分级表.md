---
title: Unit 1 · Week 3 · 自治分级表
updated: 2026-05-05
tags: [part-3, practice, unit1, week]
---

# Unit 1 · Week 3 · 自治分级表

> [← Unit 1 总览](总览.md)  ·  [← 返回目录](../../README.md)

## 本周目标
为你的场景，画出 **Auto / Confirm / Forbidden** 三档自治分级表，每行给出判断依据。

## 阅读 · B3 · 45 分钟（无 AI）
**Simon Willison · 《Designing Agentic Loops》（2025）**
（simonwillison.net/2025/Sep/30/designing-agentic-loops/）

重点关注：
- 他怎么定义"agentic loop"和"autonomous loop"
- 哪些操作他明确说"永远不要让 AI 自己做"
- "reversibility"（可回滚性）为什么是分级的核心判据

## 产出 · B2 · 60 分钟（不用 AI 写）

### 第一步 · 列出 Agent 可能执行的所有操作
按类别列，至少 15 个：
- 读类：查询数据库、读日志、调查询 API……
- 变更类：修改配置、发布、扩缩容……
- 交互类：发消息、创建工单、推送通知……
- 高危类：删除数据、切流量、改权限……

### 第二步 · 为每个操作标注三个属性
| 操作 | 可回滚性 | Blast radius | 可审计性 |
|---|---|---|---|
| `kubectl get pods` | - | 无 | 高 |
| `kubectl rollout restart` | 中（需要时间） | 单服务 | 高 |
| `DROP TABLE xxx` | 低（需从备份恢复） | 全量 | 中 |
| ... | | | |

### 第三步 · 根据属性划分 Auto / Confirm / Forbidden

**Auto（可自治）判据**：
- 可回滚性 = 高 **且** blast radius = 小 **且** 可审计

**Confirm（需人工确认）判据**：
- 可回滚性 = 中 **或** blast radius = 中
- 必须有 human-in-the-loop 机制

**Forbidden（禁止 AI 操作）判据**：
- 可回滚性 = 低 **或** blast radius = 大
- 不论 AI 多聪明，这类操作人类手工做

### 第四步 · 用表格落盘
| 操作 | 自治级别 | 判据 | 护栏措施 |
|---|---|---|---|
| ... | Auto | 只读 + 无副作用 | audit log |
| ... | Confirm | 可回滚 + 单服务影响 | 二人确认 + 变更窗口 |
| ... | Forbidden | 不可回滚 + 全量影响 | 完全禁止 tool 暴露 |

## 写完之后：让 AI 挑错
贴给 AI 并问：
1. "这份分级表里有没有**看起来安全但其实能被链式调用放大**的 Auto 项？"（举例：只读 API 被反复调用可能触发限流、泄露访问模式）
2. "Confirm 档里的人工确认机制，有哪些反模式会让它形同虚设？"（举例：确认弹窗疲劳、批量审批）

## 预测 · B1 · 每日 5 分钟
本周每次 AI 要做操作前，先猜：
- "这个操作在我的分级表里是哪一档？"
- "如果它出错，回滚代价多大？"

## 周末自检
- [ ] 至少 15 个操作，每个都有三属性标注和分级
- [ ] Auto 档的数量 < 总数的 50%（如果超过，说明你对自治过于乐观）
- [ ] Forbidden 档**必须**非空（如果为空，说明你的系统没有不可回滚操作——不太可能，再想想）
- [ ] 本周预测"没想到"的次数：____

---

下一步 → [Unit 1 · Week 4 · 合成产出](Week4-合成产出.md)

上一步 → [Unit 1 · Week 2](Week2-架构选项三套.md)
