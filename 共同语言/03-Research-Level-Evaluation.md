---
title: 共同语言 03 · Research-level Evaluation
updated: 2026-05-24
tags: [shared-language, evaluation, benchmark, research]
---

# 共同语言 03 · Research-level Evaluation

> [← 返回目录](../README.md)  ·  对比：[深入 06 · Eval Pipeline 设计](../深入/06-Eval-Pipeline设计.md)（生产侧）

> [!NOTE]
> [深入 06](../深入/06-Eval-Pipeline设计.md) 讲的是**生产 eval**——给你的 AI 产品做质量保证。
>
> 这一章讲 **research eval**——ML 团队和 paper / technical report 里用的**学术级评估**。两套系统互补，不互换。

---

## 0. 为什么要单独讲 research eval

你会在这些地方遇到：

- 新模型发布 model card 时："MMLU 82%, GPQA 45%, HumanEval 88% pass@1"
- ML 团队讨论 ablation 时："这版本在 GSM8K 涨了但 MATH 没动"
- 客户或老板问："这个模型比 GPT-5 好吗"

**如果你听不懂这些指标的含义，就只能坐在会议室里点头**。

---

## 1. Research Eval vs Production Eval

| 维度 | Research Eval | Production Eval（[深入 06](../深入/06-Eval-Pipeline设计.md)）|
|---|---|---|
| **目标** | "模型能力如何" | "我的产品好不好用" |
| **数据** | 公开 benchmark | 你的真实业务样本 |
| **周期** | 训练后一次跑 | 生产中持续跑 |
| **指标** | Accuracy, pass@k, Elo | 业务 KPI, judge 分数, 用户反馈 |
| **污染风险** | **极高**（public 就在训练数据里）| 零（你自己的数据）|
| **业务相关性** | 低到中 | 高 |
| **比较对象** | 其他模型 | 自己历史版本 |

**两种都重要，但不能替代**。

---

## 2. 必须知道的主流 Benchmark

### 2.1 通用知识与理解

**MMLU (Massive Multitask Language Understanding)**
- 57 个学科的多选题（数学、历史、法律、医学……）
- 15k 题
- 主要测**广度知识 + 理解**
- 当前 frontier 模型 85-90%；人类专家 90%
- **已几乎饱和**，区分度下降

**MMLU-Pro**
- MMLU 的升级版（更难，多选项）
- 更有区分度
- 2024 后主流

**HellaSwag / ARC / WinoGrande**
- 常识推理 / 科学 / 代词指代
- 较老的 benchmark，新模型几乎满分
- 主要用作 regression 测试

### 2.2 数学能力

**GSM8K (Grade School Math 8K)**
- 8k 小学应用题
- 饱和了（97%+）

**MATH**
- 竞赛级数学（AIME、AMC 难度）
- 仍有区分度（frontier ~85%）
- **常被用作 reasoning 能力指标**

**AIME**
- 美国数学邀请赛真题
- o1/o3/R1 推理模型主打战场
- Frontier 60-90%

**MATH-500 / GPQA Diamond**
- 更干净的子集，污染少
- 当前首选测数学 / 推理硬核度

### 2.3 代码能力

**HumanEval**
- OpenAI 早期 164 道代码题
- 饱和（~90%）
- **仍常被引用但区分度低**

**MBPP**
- Google 的入门级代码题
- 同样饱和

**BigCodeBench**
- 1140 个更真实编码任务
- 2024 新标准

**LiveCodeBench**
- 持续更新（新题每月进）
- **对抗 contamination 的选择**

**SWE-bench Verified**
- 真实 GitHub issue
- **Agent 级编码能力的黄金标准**
- Frontier 75-80%（见 [深入 03](../深入/03-模型与工具场景化最佳实践.md)）

### 2.4 推理与逻辑

**GPQA (Graduate-level Physics, Chemistry, Biology)**
- 博士级 STEM 问题
- Frontier ~55%（人类博士 65%）
- **污染较少，仍有区分度**

**BIG-Bench Hard (BBH)**
- Google 挑出 23 个困难子任务
- 综合推理能力

**ARC Challenge**
- 小学科学题，但推理难
- 已近饱和

### 2.5 Agent 与 Tool Use

**GAIA**
- 通用助理基准（需要多工具、多步）
- 人类 92% vs frontier ~50%

**SWE-bench Verified**
- 见 2.3
- Agent 必考

**τ-bench**
- Tool use + 多轮对话
- 航空、零售场景

**OSWorld**
- 真桌面 computer use
- Frontier 仅 **12%**（人类 72%）—— 见 [深入 03 · §1.4](../深入/03-模型与工具场景化最佳实践.md)

**Vending-Bench**
- 长时程决策（Anthropic）

### 2.6 主观对比

**LMSYS Chatbot Arena (LM Arena)**
- 用户盲测，Elo 评分
- **最"真实"但最主观**
- 详见 [深入 03 · §1](../深入/03-模型与工具场景化最佳实践.md)

---

## 3. Pass@k 是什么

ML 团队讨论编码能力时常说 "pass@1 88%, pass@10 95%"。

**pass@k**：让模型对同一题生成 k 次，**至少有一次通过测试**的概率。

- **pass@1**：跑一次通过率（严格）
- **pass@10**：跑 10 次至少一次对（宽松）
- **pass@100**：跑 100 次……（极宽松，研究用）

**数学公式**（简化）：
```
pass@k ≈ 1 - (1 - p)^k
```
其中 p 是单次通过率。

**含义**：
- 如果 pass@1 是 50%，pass@10 可以高到 ~99.9%
- **pass@1 才代表"单次可用"**，高 pass@k 只说明"有可能对"
- 生产里重要的是 pass@1（或很小的 k）

**SRE 警惕**：有些 paper / 营销用 pass@100 刷分，**别被迷惑**。

---

## 4. Elo 评分（LM Arena）

### 4.1 机制

源自国际象棋。两个选手对弈：

```
新分 = 旧分 + K × (结果 - 期望)
```

- K：调整幅度常数
- 期望：基于双方分差算出的理论胜率

LM Arena 让用户盲测两个模型回答相同问题，选更好的。每个投票更新 Elo。

### 4.2 关键特性

- **相对分数**（某个锚点 = 1000 或 1500）
- **对弈要多**（需要成千上万场对弈才收敛）
- **难被单点刷**（需要众多真实用户参与）
- **反映主观偏好**，不等同于能力

### 4.3 读 LM Arena 排名的姿势

- 看**分差**而不是绝对数字（差 20 分 = 显著，差 5 分 = 噪声）
- **子榜**（Coding / Hard Prompts / Long Context）比总榜重要
- **投票数**要足够（< 10k 投票的新模型分数不稳）

---

## 5. Benchmark Contamination

已在 [共同语言 02 · §5](02-Data是ML的真正核心.md#5-decontamination去污染) 讲过。这里从 eval 角度再讲：

### 5.1 怎么判断一个模型"刷榜"

- Benchmark 分飙高但 Arena 没变
- 一个子类型异常强（比如 HumanEval 95% 但 LiveCodeBench 60%）
- 和其他强模型差距"太不合理"

### 5.2 为什么 frontier 实验室用 Private Eval

- 公开 benchmark 已被训练数据污染
- 内部 held-out eval 才反映真实能力
- **但 paper 里不能报告 private eval**（不可比）

### 5.3 Fresh Benchmarks（新鲜评估）

**LiveBench / LiveCodeBench**：每月加新题，保证没在训练集。**2025-2026 最被推崇的抗污染方案**。

---

## 6. Ablation 的评估逻辑

ML 团队做 ablation，需要的 eval 是：

- **快**（不想每次等 6 小时）
- **敏感**（能看出微小改动）
- **多维**（MATH / CODE / MMLU / ARENA 综合）

典型 ablation 表：

| Recipe | MMLU | MATH | HumanEval | MT-Bench | 结论 |
|---|---|---|---|---|---|
| Base | 68.2 | 42.1 | 71.3 | 7.8 | — |
| + Math data | 68.8 | **47.9** | 70.8 | 7.7 | 数学强，代码轻退 |
| + Code anneal | 67.9 | 42.3 | **75.6** | 7.9 | 代码强 |
| Both | **69.5** | **48.1** | **75.9** | 8.0 | **最终版** |

**SRE 要知道**：每一行都是**一个完整 run**，跑一次可能几天 + 上千卡。**Ablation 的成本极高**——ML 团队必须精算哪些组合值得跑。

---

## 7. 评估的常见陷阱

### 7.1 Zero-shot vs Few-shot

**Zero-shot**：直接问题，不给例子。
**Few-shot (n-shot)**：给 n 个例子再问（如 5-shot MMLU 是给 5 个示例）。

**不同 paper 用不同设置**，比较时要**注意前提**。Few-shot 常涨几个点。

### 7.2 Chain-of-Thought（CoT）

让模型"先想再答"。
- Zero-shot CoT：加 "Let's think step by step"
- Thinking 模型：原生 CoT
- **CoT 分和非 CoT 分不能直接比**

### 7.3 格式敏感性

同样问题不同格式（选择题顺序、是否用 `A/B/C/D`）分差可能 5-10%。

**ML 团队常做的**：同一 benchmark 跑多种格式取平均。

### 7.4 Judge 模型打分

用 LLM 给 LLM 打分。**评委偏见**（同家模型对自家输出评分偏高）。**AlpacaEval / MT-Bench** 用这方法，要读的时候打折。

### 7.5 Cherry-picking

Paper 里报告"我们赢的 10 个 benchmark"，没提"我们输的 5 个"。
**读 tech report 时**：看完整的表格，而不是只看文字摘要。

---

## 8. SRE 视角：哪些 eval 信号要上生产监控

### 8.1 Research eval 不是生产 eval

生产监控不需要跑 MMLU。**生产上该盯的**见 [深入 06](../深入/06-Eval-Pipeline设计.md)。

但有这些**关联**：

### 8.2 新模型上线前的 SRE 动作

- 看 model card 的 **benchmark 结果对比**老版本
- **关注回退（regression）**：如果 MMLU 涨但 HumanEval 跌，你的 code-heavy 业务要小心
- 跑**自己业务的 eval set**，不要信 public benchmark
- 用**Shadow 流量**对比新旧版本

### 8.3 当 ML 团队说 "Public benchmark 涨了" 时

你要追问：
- **Private eval 动了吗**？
- **LM Arena 动了吗**？
- **有没有 contamination check**？
- **Ablation 表有没有**？

**避免被 benchmark 刷分迷惑，导致上线事故**。

---

## 9. 会议室对话实例

> **ML**：新版本 MMLU 85、GPQA 48、pass@1 HumanEval 92，比上版全面涨。准备上线。
> **老 SRE**：嗯……好。
> **懂了的 SRE**：等等：
> - MMLU 到 85 已经接近饱和，意义不大，LiveBench 或 MMLU-Pro 呢？
> - HumanEval 92 是 pass@1 还是 pass@10？我们生产场景等同 pass@1 吗？
> - LM Arena 你们跑了吗？分差多少？
> - Private eval（你们自己 held-out 的）动了多少？
> - Regression check 做了吗？万一 code 好了但 reasoning 退了？

这些问题**每一个都值得追问**，因为每一个都可能引发线上事故。

---

## 10. 关键词汇速查

| 词 | 意思 |
|---|---|
| **MMLU** | 57 学科选择题，通用知识 |
| **MMLU-Pro** | MMLU 升级版，更难 |
| **GPQA** | 博士级 STEM 问题 |
| **GSM8K / MATH / AIME** | 数学 benchmark 三档（饱和/中/难）|
| **HumanEval / MBPP / BigCodeBench / LiveCodeBench** | Code benchmark |
| **SWE-bench Verified** | 真实 GitHub issue 修复 |
| **GAIA / OSWorld / τ-bench / Vending-Bench** | Agent benchmark |
| **pass@k** | k 次里至少一次对的概率 |
| **Elo / Arena** | 盲测对弈评分 |
| **Contamination** | Benchmark 被训练数据污染 |
| **Private eval / Held-out** | 实验室内部的 eval set |
| **Zero-shot / n-shot** | 给多少例子 |
| **Chain-of-Thought (CoT)** | 先想再答 |
| **LLM-as-judge** | 用 LLM 给回答打分 |
| **Regression** | 新版某项指标掉了 |
| **Ablation** | 改 1 变量的对比实验 |

---

## 11. 给 SRE 的一句话总结

> [!IMPORTANT]
> Research eval 的语言不是"炫技"——是 SRE 在**模型上线决策**里参与讨论的门票。
>
> 读 model card / technical report 不需要你推导 attention 公式，但**必须**能区分 MMLU / GPQA / SWE-bench、理解 pass@k、警觉 contamination、分辨 Elo 分差。
>
> **懂了这些，新版本上线前的风险评审，SRE 就能提出让 ML 团队服气的问题**——而不是当个 GPU 计量员。

---

## 12. 参考资料

- Hendrycks et al · 《MMLU》— https://arxiv.org/abs/2009.03300
- Rein et al · 《GPQA》— https://arxiv.org/abs/2311.12022
- Chen et al · 《HumanEval》— https://arxiv.org/abs/2107.03374
- Jimenez et al · 《SWE-bench》— https://arxiv.org/abs/2310.06770
- Chiang et al · 《Chatbot Arena》— https://arxiv.org/abs/2403.04132
- Huang et al · 《LiveCodeBench》— https://arxiv.org/abs/2403.07974
- LMSYS · LM Arena leaderboard — https://arena.ai/leaderboard
- Hugging Face · Open LLM Leaderboard — https://huggingface.co/spaces/open-llm-leaderboard/open_llm_leaderboard

🔄 复习：[核心概念卡](../复习/核心概念卡.md) · [Active Recall 题库](../复习/Active-Recall题库.md)

---

← [共同语言 02 · Data 是 ML 的真正核心](02-Data是ML的真正核心.md)  ·  [📖 目录](../README.md)  ·  [共同语言 04 · Alignment 的词汇 →](04-Alignment的词汇.md)
