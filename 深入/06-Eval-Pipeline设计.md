---
title: 深入 06 · Eval Pipeline 设计
updated: 2026-05-05
tags: [deep-dive, eval, observability, data-flywheel]
---

# 深入 06 · Eval Pipeline 设计

> [← 返回目录](../README.md)  ·  相关：[第 7 章 · 质量可观测性与 Data Flywheel](../知识/07-质量可观测性与DataFlywheel.md)  ·  [Unit 2 · Trace-Eval 统一可观测性](../练习/Unit2-TraceEval统一可观测性/总览.md)

SRE 架构师级别的 Eval Pipeline 工程化手册。重点不是"怎么打分"，而是**怎么把 eval 做成一个持续运转、自我演化、SLO 保护的系统**。

---

## 0. 为什么 LLM Eval 是个独立学科

传统软件测试：

```
输入 X → 期望输出 Y → 实际输出 Y? → pass/fail
```

LLM 应用测试：

```
输入 X → 期望 "something reasonable" → 实际输出 Y
         ↓
         Y 可能和期望完全不同但也算对 (语义等价)
         Y 可能看起来对但实际错 (流利的幻觉)
         Y 每次运行都不同 (temperature > 0)
```

**核心难题**：**正确性没有 ground truth**。

这导致 LLM eval 必须做三件传统测试不做的事：

1. **多层评估**（硬规则 + 模型评分 + 人工反馈）
2. **持续监控**（线下通过不等于线上通过）
3. **评估器本身需要评估**（Judge 模型可能漂移）

> [!IMPORTANT]
> **Anthropic 2026 年初的事故复盘告诉我们**：线下 eval 通过后线上仍然劣化了——"你的 eval 会骗你"已经是共识。Eval 不是一次性动作，是**一套持续运转的子系统**。

---

## 1. 三层 Eval 体系

```
┌─────────────────────────────────────────┐
│ L3 · A/B 测试 & 用户反馈                │  ← 真理 (慢)
│    thumbs up/down、留存、编辑距离       │
├─────────────────────────────────────────┤
│ L2 · Judge 模型评分                     │  ← 近似 (可扩展)
│    LLM-as-judge，相对人工评分对齐       │
├─────────────────────────────────────────┤
│ L1 · Assertion / 硬规则                 │  ← 快 (死板)
│    格式、长度、必要字段、黑名单         │
└─────────────────────────────────────────┘
```

**设计原则**：每一层各自解决一类问题，**互相不可替代**。

### L1 · Assertion（硬规则）

**做什么**：基于规则的快速过滤

**具体检查项**：
- 输出格式（是不是 valid JSON？）
- 必要字段（有没有 `title`、`summary`？）
- 字段类型（number 字段不是 string？）
- 长度约束（summary ≤ 200 字？）
- 黑名单（有没有违禁词、PII、竞品名）
- 白名单（必须包含某些关键词）
- 结构验证（markdown 表格格式对不对？）

**实现**：Python / Regex / JSON Schema / Pydantic 模型

**优势**：
- 毫秒级执行
- 100% 可解释
- 通过/失败二分

**劣势**：
- 死板（语义对但规则错就 false negative）
- 覆盖不到"质量"

**部署位置**：**每次请求都跑**，作为准入门槛

### L2 · Judge 模型评分

**做什么**：用 LLM 给 LLM 打分

**具体评估维度**：
- **相关性**（是不是在回答这个问题）
- **忠实度**（RAG 里，回答是否忠实于检索内容）
- **完整性**（回答够不够）
- **简洁度**（有没有废话）
- **准确性**（事实对不对，能核验的话）

**实现**：
```python
judge_prompt = f"""
你是一个严格的评委。给以下回答打分（0-10）：

问题：{question}
回答：{answer}
参考文档：{reference}

评分维度：
- 相关性（0-10）
- 忠实度（0-10）
- 完整性（0-10）

以 JSON 格式输出：{{"relevance": int, "faithfulness": int, "completeness": int, "reasoning": str}}
"""
```

**优势**：
- 能评价语义
- 可扩展（跑在抽样的线上流量上）

**劣势**：
- 判官自己可能错
- 有偏见（偏好长文、偏好自己语言风格）
- 有成本

**部署位置**：抽样线上流量（比如 1-5%）持续跑

### L3 · A/B 测试 + 用户反馈

**做什么**：让用户当裁判

**信号来源**：
- 显式：thumbs up/down、评分、反馈按钮
- 隐式：编辑距离（用户改了多少）、留存、复用率、任务完成率
- 对比：A/B 分流，新旧版本对比

**优势**：
- 最接近真理
- 业务相关

**劣势**：
- 慢（需要统计显著性）
- 样本有偏（爱抱怨的人发声多）
- 维护成本高

**部署位置**：重大版本切流前必做

---

## 2. Judge 模型的对齐度追踪

> [!WARNING]
> **Judge 模型自己也会错**。如果你盲信 L2 分数，只是把信任转移给了另一个 LLM。

### 对齐度度量

定期抽样（每周 50-100 条）让**人工评委**和 **Judge 模型**都打分，算一致率：

- **简单指标**：**agreement rate**（打分 ±1 算一致）
- **严格指标**：**Cohen's κ**（修正偶然一致）
- **相关性**：**Pearson / Spearman**

**目标**：Cohen's κ ≥ 0.6（适度一致）；理想 ≥ 0.75

### 当对齐度下降时

可能原因：
1. **Judge 模型本身升级了**（升级往往改变打分分布）
2. **被评估模型改变，Judge 遇到新样本类型**
3. **Rubric 不再适用**（业务目标变了）
4. **数据漂移**（线上 workload 发生偏移）

**处理流程**：
- 暂停 L2 自动决策（比如用 L2 分数筛模型）
- 人工审查最近 50 条差异样本
- 更新 rubric 或换 Judge 模型
- 再测一次 κ，通过再恢复自动决策

### Judge 模型选型

一个实用的经验：**用比被评模型弱一档的 Judge**。

- 被评：GPT-5.4
- Judge：Sonnet 4.6 / Haiku 4.5（用不同厂家避免自家偏见）

或者 **两家 Judge 投票**，分歧时送人工。

---

## 3. Offline vs Online Eval

|  | Offline Eval | Online Eval |
|---|---|---|
| **何时跑** | 部署前、版本切换前 | 生产流量运行中 |
| **数据** | 固定测试集（黄金集） | 抽样生产 trace |
| **目标** | Gate：没达标不放 | 漂移检测 + 持续质量 |
| **预算** | 每次跑几百-几千样本 | 持续跑，占真实成本 1-5% |
| **决策权** | 阻止发布 | 触发回滚 / 降级 |

### Offline Gold Set 维护

- **规模**：200-1000 条
- **多样性**：覆盖核心场景 + 长尾 + 历史故障案例
- **冻结版本化**：`v1.0`、`v1.1`...
- **定期扩充**：从线上新问题补充（防止过拟合旧集）
- **不要训练时用**：训练集和 eval 集严格分离，避免数据污染

### Online Continuous Eval

```
生产流量 → 抽样 1-5% → L1 assertion → L2 judge → 异常报警
                           ↓                      ↓
                      失败样本入库           趋势图到仪表盘
```

> [!IMPORTANT]
> **Online eval 不是可选的**。只靠 offline 会漏：
> - 模型 API 侧静默升级
> - 数据漂移（用户问的问题变了）
> - 运行环境变化（prompt cache hit 率变低）

---

## 4. Eval 自身的 SLO

Eval pipeline 挂了 = 你**瞎了**。所以 Eval 自己必须有 SLO。

### 关键 SLI

| SLI | 定义 | 目标 |
|---|---|---|
| **覆盖率** | 生产流量被 eval 的比例 | ≥ 1%（抽样比例） |
| **评估延迟** | 请求到 eval 结果的时间 | p95 < 5 分钟 |
| **Judge 对齐度** | Cohen's κ with human | ≥ 0.6 |
| **Pipeline uptime** | Eval 服务可用性 | ≥ 99.5% |
| **Eval 失败率** | judge 调用失败 / schema 错 | < 1% |
| **数据新鲜度** | 最老的未处理 trace 年龄 | < 10 分钟 |

### Error Budget

**Eval pipeline 挂掉 > 1 小时** = budget 扣 10%（比如每月 budget 20 分钟挂机）。

超预算怎么办？
- **不是回滚 eval**（我们在测试，不是在做功能）
- 而是**暂停所有自动质量决策**（比如自动 rollback 新模型版本），转人工 review，直到 eval 恢复

---

## 5. Data Flywheel：Eval → 改进 → 再 Eval 的循环

Eval pipeline 的**最终价值**不是"看看怎么样"，是**持续改进的动力源**。

```
       ┌───────────────────────────────────────┐
       ↓                                       │
  [生产 trace]                                 │
       │                                       │
       ↓                                       │
  [抽样 + L1/L2 eval]                          │
       │                                       │
       ↓                                       │
  [失败样本 + 低分样本 → 标注队列]             │
       │                                       │
       ↓                                       │
  [人工标注 / 修正]                             │
       │                                       │
       ↓                                       │
  [扩充 gold set + 发现新 failure mode]        │
       │                                       │
       ↓                                       │
  [调 prompt / 换模型 / 加 verifier]           │
       │                                       │
       ↓                                       │
  [offline eval on new gold set]               │
       │                                       │
       ↓                                       │
  [灰度发布 → 回 top]                          │
       │                                       │
       └───────────────────────────────────────┘
```

这是 **SRE 架构师该拥有的基础设施**，而不是推给"ML 团队"。它是可靠性反馈回路。

---

## 6. 工具选型

参考 [深入 03 · §4.4](03-模型与工具场景化最佳实践.md#44-eval--observability-工具)。简版推荐：

| 场景 | 首选 | 备选 |
|---|---|---|
| OSS / 自托管 | **Langfuse** | Phoenix (Arize) / Helicone |
| LangChain 生态 | **LangSmith** | - |
| Eval 优先 + SaaS | **Braintrust** | - |
| 极简代理 | **Helicone** | - |

### 选型考虑

- **OTel 兼容**：未来能和其他 observability 栈整合
- **自托管能力**：数据敏感时必须
- **Evaluator 可插拔**：不被单一 judge 模型绑死
- **数据导出**：便于做 data flywheel 的标注循环
- **定价模型**：按 trace / 按 eval / 按 team

---

## 7. 常见陷阱

- ❌ **事后才写 eval**：线上出问题了再补 eval，已经晚了
- ❌ **只用 offline eval**：线下通过 ≠ 线上好
- ❌ **Judge 模型不校准**：相信 judge 分数而不测它准不准
- ❌ **Gold set 不更新**：线上数据漂移了 gold set 还在测 2024 年的问题
- ❌ **Gold set 训练中泄露**：训练数据污染，eval 分虚高
- ❌ **失败样本不回收**：错过最大的改进机会
- ❌ **Eval 挂了没人知道**：没给 eval 自己设 SLO
- ❌ **所有 eval 用同一个 judge**：本家 judge 偏见 + 单点故障
- ❌ **L1 assertion 过严**：把语义正确但格式偏差的都判死
- ❌ **L2 评分追求小数点**：2.3 vs 2.7 没意义，用大档次（高/中/低）

---

## 8. Worked Example：RAG 系统的 Eval Pipeline

### 系统
- 用 Sonnet 4.6 + 5k 公司文档做内部问答

### L1 Assertion（每请求）
```python
def l1_check(answer: dict) -> bool:
    if not answer.get("answer"): return False
    if not answer.get("citations"): return False  # 必须引用
    if len(answer["answer"]) > 2000: return False  # 过长
    if any(kw in answer["answer"] for kw in BLACKLIST): return False
    return True
```

### L2 Judge（每天抽样 5%）
- 维度：相关性 / 忠实度（引用的文档真的支持这个回答？）/ 完整性
- Judge：GPT-5.4-mini
- 校准：每周 50 条样本 vs 人工，目标 κ ≥ 0.65

### L3 A/B（版本切换时）
- 分流 10% 到新 prompt / 新模型
- 主指标：thumbs-up 率
- 副指标：后续提问率（用户追问多 = 回答不完整）
- 统计显著后决定全量

### Data Flywheel
- L2 低分 + L3 thumbs-down 样本 → 每周人工标注 30 条
- 每月补充 Gold Set 50 条
- 每季度重新跑历史 Gold 对新版本（防回归）

### Eval SLO
- 覆盖率 ≥ 5%
- Judge κ ≥ 0.65
- Pipeline uptime ≥ 99.5%
- 失败率 < 1%

### 触发人工 review 的信号
- L2 平均分周环比下降 > 10%
- L3 thumbs-up 率下降 > 5%
- Judge κ 跌破 0.55
- 用户申诉 rate 2× 基线

---

## 9. 给 SRE 的一句话总结

> [!IMPORTANT]
> **Eval Pipeline = LLM 时代的监控 + 测试 + 回归套件的合体**。
>
> 它不是"ML 团队"的东西——它是**可靠性基础设施**。
>
> 如果 eval 自己没 SLO、Judge 不校准、失败样本不入 flywheel，你就是在开无仪表的飞机。

---

## 10. 参考资料

- Hamel Husain · 《Your AI Product Needs Evals》— https://hamel.dev/blog/posts/evals/
- Eugene Yan · LLM evaluation 系列 — https://eugeneyan.com/
- Anthropic · Postmortem of three recent issues（"你的 eval 会骗你"的原始来源）
- OpenAI · Evals repo — https://github.com/openai/evals
- Langfuse docs · Evaluators and datasets — https://langfuse.com/docs
- Phoenix (Arize) docs · LLM evals — https://docs.arize.com/phoenix
- Braintrust · Eval-first workflow blog — https://www.braintrust.dev/blog

---

← [深入 05 · LLM 推理服务的容量规划](05-LLM推理服务的容量规划.md)  ·  [📖 目录](../README.md)  ·  [深入 07 · Agent Prompt Injection 红队实战 →](07-Agent-Prompt-Injection红队实战.md)
