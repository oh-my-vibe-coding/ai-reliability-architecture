---
title: 代码 04 · Eval Pipeline 骨架 · 教学指南
updated: 2026-05-05
tags: [code, guide, eval, pydantic]
---

# 代码 04 · Eval Pipeline 骨架 · 教学指南

> [← 代码索引](README.md)  ·  主代码：[04-eval-skeleton.py](04-eval-skeleton.py)  ·  关联章节：[深入 06 · Eval Pipeline 设计](../深入/06-Eval-Pipeline设计.md)、[Unit 2 · Week 2](../练习/Unit2-TraceEval统一可观测性/Week2-三层Eval体系设计.md)

> [!WARNING]
> **价格 / 模型名快照日期**：2026-05-05。单样本 / 总额估算会随定价变动。以 **数量级** 而非精确数字来理解。生产前查官方 pricing：
> - https://www.anthropic.com/pricing
> - https://openai.com/api/pricing

---

## 1. 运行前提

### 环境

- Python 3.10+
- Anthropic API key（也可改用 OpenAI）
- 100 条左右测试 prompt（可用代码里 demo 的 3 条起步）

### 安装

```bash
pip install 'anthropic>=0.40' pydantic 'pytest>=8'
export ANTHROPIC_API_KEY=sk-ant-...
```

### 成本

- 每 eval sample：~$0.02（生成 + judge）
- 100 条完整 eval：~$2

**建议**：先用 haiku 4.5 做主模型省钱，稳定后切 sonnet。

---

## 2. 预期输出

```
=== Eval Report ===
Total: 3
L1 pass rate: 100.0%
L2 scores: {'relevance': 8.33, 'safety': 9.0, 'completeness': 7.67}
```

如果某些 sample L1 fail：

```
Total: 3
L1 pass rate: 66.7%
L2 scores: {'relevance': 8.5, 'safety': 9.0, 'completeness': 8.0}

1 failures detected
```

**关键观察**：
- L1 pass rate 是**快速过滤**（格式对不对）
- L2 分数按维度分（不是单一总分）
- L1 fail 的样本**不进 L2**（省钱）

---

## 3. 常见报错

### A · Pydantic ValidationError

```
pydantic.ValidationError: 1 validation error for RunbookResponse
steps -> 0 -> safety
  value is not a valid enumeration member
```

模型输出的 schema 不对。这是 **L1 catch 到了的问题**——它就是为此设计的。

**修复方向**：
- 调 prompt 明确 enum 值
- 用 Anthropic 的 JSON mode 强制 schema
- 加重试机制（L1 fail → 用更严 prompt 重问）

### B · JSON 解析失败

```
json.JSONDecodeError: Expecting value
```

模型输出带了 markdown fence（```json ... ```）或其他。

代码里有处理：

```python
if text.startswith("```"):
    text = text.split("```")[1]
    if text.startswith("json"):
        text = text[4:]
```

但不够 robust。更严的处理：

```python
import re
match = re.search(r'\{.*\}', text, re.DOTALL)
if match:
    text = match.group(0)
```

### C · Judge 分数超出范围

模型输出 11、`high`、`"10/10"` 等。

**修复**：Pydantic constraint

```python
class JudgeScore(BaseModel):
    relevance: int = Field(ge=1, le=10)
    safety: int = Field(ge=1, le=10)
    completeness: int = Field(ge=1, le=10)
```

### D · Judge 自己结构化失败

罕见但会发生。代码里有：

```python
except (json.JSONDecodeError, TypeError):
    return None
```

生产上要**统计这种失败率**——如果 > 5%，说明 judge prompt 不够明确。

---

## 4. 改造任务

### 任务 1 · 加 Judge 校准（必做）

当前代码用 judge 给分，但没有 **人工校准**。

- 每周让人工给 20 条样本打分
- 计算 **agreement rate**：`|human - judge| <= 1` 的比例
- agreement < 70% → 暂停 judge 自动决策

**思考**：N = 20 够吗？什么时候需要更多？

### 任务 2 · 加 L3 A/B（中等）

当前只有 L1 + L2。加一个最小 L3：

- 同一批 prompt 跑两个不同 prompt 模板（A 和 B）
- 让 Judge 对比打分
- 统计显著性检验（scipy.stats.mannwhitneyu）

### 任务 3 · Eval 自身的 SLO 监控（中等）

给 eval pipeline 加监控：

- **覆盖率**：过去 24h 线上样本多少被 eval
- **延迟**：从 trace 到 eval 结果的 p95 时长
- **失败率**：judge 返回 None 的比例
- **Judge 对齐度**（上个任务的产出）

导出 Prometheus 指标。

### 任务 4 · 失败样本回流（较难）

L1/L2 失败的样本应该**自动回流到数据集**，供下次改 prompt / 训练用：

```python
def on_failure(sample, l1_result, l2_result):
    save_to_failure_db({
        "prompt": sample,
        "l1": l1_result,
        "l2": l2_result,
        "timestamp": now(),
        "prompt_version": CURRENT_VERSION,
    })
```

**关键**：配合 [Data Flywheel](../深入/06-Eval-Pipeline设计.md#5--data-flywheelseval--改进--再-eval-的循环) 的完整闭环。

### 任务 5 · 多 Judge Ensemble（较难）

用两个不同厂商的 judge 对同一 sample 打分：

```python
judge_claude = l2_judge_claude(sample)
judge_openai = l2_judge_openai(sample)
# 分歧 > 2 时送人工
if abs(judge_claude.score - judge_openai.score) > 2:
    send_to_human_queue(sample)
```

**意义**：对抗单家 judge 的偏见。

---

## 5. 读者作业（自检答案见下）

### 作业 1
为什么 L1 fail 的样本不进 L2？省钱以外还有什么原因？

<details><summary>参考答案</summary>

1. **省钱**：judge 调用有成本
2. **L2 噪声**：L1 fail 说明输出结构都不对，L2 分数是噪声（judge 也 confused）
3. **聚焦改进**：L1 fail 的问题是 prompt / schema 问题；让它先跑 L2 会把注意力分散

但要**记录** L1 fail 率，按失败类型分桶——这是改 prompt 的信号。

</details>

### 作业 2
Judge 模型的 agreement rate 掉到 55% 你会怎么处理？

<details><summary>参考答案</summary>

**先诊断**：
1. 是所有维度都掉，还是某一维？
2. 分布偏移了？（比如被评模型换了新版本）
3. Judge 自己是不是被升级了？

**短期**：暂停自动决策，转人工 review 模式
**中期**：校准 prompt（加例子、改 rubric）或换 judge 模型
**长期**：投 judge 校准流水线（自动每周抽样 + 触发告警）

参考 [深入 06 · §2](../深入/06-Eval-Pipeline设计.md)。

</details>

### 作业 3
你的 L2 Judge 给所有长回答都打高分。这是什么问题？怎么发现？怎么改？

<details><summary>参考答案</summary>

**问题**：**Length bias**。Judge 学了"长 = 好"的伪相关。

**发现**：
- 故意生成 2 个版本：短回答（但信息完整）vs 长回答（注水）
- 跑 Judge，看分数差
- 有显著偏好长的 → 有 length bias

**修复**：
- 在 judge prompt 显式说"回答长度不是评分依据"
- 或者在 rubric 里加"简洁度"作为一个负向维度
- 严重时换 judge 模型

参考 [深入 06 · §2.1](../深入/06-Eval-Pipeline设计.md) 的对齐度追踪和偏见。

</details>

### 作业 4
你的 eval pipeline 挂了 1 小时。系统应该如何 degrade？

<details><summary>参考答案</summary>

参考 [深入 06 · §4](../深入/06-Eval-Pipeline设计.md) Eval 自身 SLO。

**立即**：
- 告警升级到 SRE
- 暂停所有**基于 eval 结果的自动决策**（如自动 rollback、自动模型切换）
- 转人工 review 模式

**对业务**：
- 正常服务**不 degrade**（eval 是观察者）
- 但失去"线上质量监控"，风险上升

**错误预算**：1 小时挂机扣 10% 月度 budget。超预算 = 需要改 eval 基础设施。

</details>

---

## 6. 生产化清单

- [ ] Judge 校准流水线（见任务 1）
- [ ] L1 失败按类型分桶监控
- [ ] 失败样本自动入库（见任务 4）
- [ ] Judge SLO + 告警
- [ ] Gold Set 版本化（prod 数据和 eval 数据严格隔离）
- [ ] 成本 dashboard（eval 自己的成本也是一笔账）
- [ ] 集成到 CI：代码 PR 合并前必过 eval gate
- [ ] Eval 结果持久化（可追溯历史）

---

## 7. 多厂商说明

本代码用 Anthropic 做主模型 + 主 judge（用 haiku 省钱）。**相对 vendor-neutral**：

- 切 OpenAI：`import openai; client = openai.OpenAI()`
- 切 Gemini：`import google.generativeai as genai`
- 混合：**主模型一家，judge 另一家**（推荐，避免自家偏见）

Eval 框架本身（L1/L2/L3、Pydantic 校验、统计分析）完全 vendor-agnostic。

---

[← 代码索引](README.md)  ·  [📖 目录](../README.md)
