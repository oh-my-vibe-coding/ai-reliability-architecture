---
title: 共同语言 01 · 训练生命周期与 Recipe（SRE 视角）
updated: 2026-05-05
tags: [shared-language, training, recipe, lifecycle]
---

# 共同语言 01 · 训练生命周期与 Recipe（SRE 视角）

> [← 返回目录](../README.md)

> [!NOTE]
> **目标**：让 SRE 能进入 ML 团队的会议室听懂"这次 mid-training 的 recipe 改了 data mixing，ablation 显示 MATH 涨 3 个点"。不推公式，不讲 PyTorch 代码，只讲**概念 + 词汇 + SRE 能做什么**。

---

## 0. 为什么 SRE 要懂训练

你说："我不跑训练，为什么要学？"

因为你会遇到这些场景：
- ML 团队说要给 training run **申请 64 张 H100 两周** — 你得能问"为啥是这配置"
- 训练中 **loss spike**，ML 问你"checkpoint 能从哪里恢复" — 你得听懂这是啥
- 新模型版本上线前 ML 给你一份 **model card** — 你要会读
- 生产模型出问题怀疑是 training 阶段的 **data contamination** — 你要听懂病灶

> [!IMPORTANT]
> **SRE 不需要会训练，但必须能参与训练的架构决策和 incident**。

---

## 1. 训练生命周期全景

```
┌────────────────────────────────────────────────────────┐
│ Pre-training                                           │
│ ─ 数据：万亿级 token（网页+书+代码）                   │
│ ─ 目标：下一 token 预测                                │
│ ─ 时长：数周到数月，几百~几万张 GPU                   │
│ ─ 产出：base model（没对齐，只会续写）                 │
└─────────────────────┬──────────────────────────────────┘
                      ↓
┌────────────────────────────────────────────────────────┐
│ Mid-training / Annealing / Continued Pre-training      │
│ ─ 数据：更精选（数学、代码、指令跟随）                 │
│ ─ 目标：提升特定能力                                   │
│ ─ 时长：数天到数周                                     │
│ ─ 2024-2026 新阶段，以前没有                           │
└─────────────────────┬──────────────────────────────────┘
                      ↓
┌────────────────────────────────────────────────────────┐
│ Post-training                                          │
│ ├─ SFT (Supervised Fine-tuning)                        │
│ │   对齐到"按指令回答"格式                             │
│ ├─ RLHF (Reinforcement Learning from Human Feedback)   │
│ │   或 DPO (Direct Preference Optimization)            │
│ │   让回答质量符合人类偏好                             │
│ └─ Safety tuning                                       │
│     拒绝有害请求、礼貌度、refusal 校准                 │
└────────────────────────────────────────────────────────┘
                      ↓
                 可部署的 Chat Model
```

---

## 2. 每个阶段详解

### 2.1 Pre-training（预训练）

**做什么**：在海量文本上让模型学"下一个 token"。

- 数据：10-15 T token（**万亿级**，不是十亿）
- 目标函数：简单到反人类——`cross-entropy loss`（预测下一 token 概率分布）
- 时长：GPT-4 级模型约 3 个月、上千张 A100/H100
- 产出：**base model**——只会续写，不会对话

**关键词**：
- **Token**：已经熟悉（见 [科学 04](../科学/04-Tokenization的坑.md)）
- **Context length**：训练时的最大序列长度（通常 2k-8k）
- **Batch size**：一次 gradient update 看多少样本
- **Steps**：训练步数（常用 100k-500k）
- **Loss curve**：随 steps 下降的 loss 曲线——ML 团队盯着看的图
- **Perplexity (PPL)**：loss 的指数形式，越低越好

**SRE 能参与**：
- Training cluster 运维（见 [共同语言 05](05-分布式训练基础设施.md)）
- Checkpoint 存储容量规划（一个大模型 checkpoint 可达 TB 级）
- Monitoring（loss 曲线异常报警）

### 2.2 Mid-training / Annealing（2024-2026 新阶段）

**做什么**：在 pre-train 末期或之后，用**质量更高、主题更聚焦的数据**继续训练。

ML 团队常说：
- *"这批 recipe 在 annealing 阶段加了 15% 数学数据"*
- *"mid-training 专门补了 code 能力"*

**为什么重要**：
- Pre-training 数据质量参差；高质量数据放最后阶段**影响最大**（近因效应）
- 是当前"性能跃迁"的重要手段（如 Llama 3、Qwen 3、DeepSeek V3 都重度依赖）

### 2.3 Post-training：SFT（监督微调）

**做什么**：用人类写的高质量"指令-回答"对子继续训练，教模型"对话"。

- 数据：10k-1M 条精选对话（**几个量级小于 pre-train**）
- 目标：让模型学会"被问就答"，不是续写
- 时长：数小时到数天
- 产出：**Instruction-tuned Model**

**关键词**：
- **Instruction tuning**：SFT 的别名
- **Turn**：一问一答算一 turn
- **Multi-turn**：多轮对话训练

### 2.4 Post-training：RLHF / DPO / GRPO

**做什么**：让模型的回答**更符合人类偏好**（帮助性、诚实性、无害性）。

详细见 [共同语言 04 · Alignment 的词汇](04-Alignment的词汇.md)。一句话：

- **RLHF**：用人类偏好训一个 reward model，然后用 RL 让模型迎合 reward model
- **DPO**：不训 reward model，直接用偏好对比做优化（简化版，主流选择）
- **GRPO**：DeepSeek-R1 用的变体，不用 value function

**产出**：**Chat Model / Aligned Model**

### 2.5 Safety Tuning

**做什么**：专门训练 refusal / 拒绝有害请求的能力。

- 与 RLHF 可合并可独立
- 坑：过度拒绝（over-refusal）让模型变"怕事"

---

## 3. 如何读 Model Card / Technical Report

ML 团队发布新模型时，会有一份 **model card**（或 technical report）。SRE 至少要能读懂这些区段：

### 3.1 Training Data

- **数据量**（"10T tokens"）
- **Cutoff date**（训练数据截止日——决定模型"知识最晚到哪天"）
- **Mixing ratio**（代码、数学、多语言各占多少）
- **Data filtering**（怎么清洗、去重）

### 3.2 Architecture

- 参数量（70B、400B、激活参数等）
- Layer 数、Hidden dim
- MoE 与否（几个 expert，激活几个）
- Attention 机制（GQA group size、sliding window）
- **Context length（训练 vs 推理可能不同）**

### 3.3 Training Recipe

- Compute（"trained for N FLOPs"）
- Batch size / learning rate / scheduler
- Hardware（H100? TPU? 多少张）
- **Loss spikes**（有就会提）

### 3.4 Post-training

- SFT dataset size
- RLHF / DPO / GRPO 用了哪个
- Safety training 流程

### 3.5 Evaluations

- Benchmarks（见 [共同语言 03](03-Research-Level-Evaluation.md)）
- **Ablations**（对比实验：去掉某组件看影响）

### 3.6 Limitations / Safety

- 已知失败模式
- Red team 结果

---

## 4. Recipe 与 Ablation

**Recipe**：完整的训练配方。包含：数据、架构、超参、训练流程。

**一次 run**：按某个 recipe 从头跑完的训练。

**Ablation**：改动 recipe 的一个变量，跑一次 run，对比结果。**ML 团队时间的 50% 花在这**。

例子（model card 里可能看到）：

| Recipe | MMLU | MATH | HumanEval |
|---|---|---|---|
| Baseline | 68.2 | 42.1 | 71.3 |
| + Math-heavy mix (10%→25%) | 68.8 | **47.9** | 70.8 |
| + Code annealing | 67.9 | 42.3 | **75.6** |
| + DPO over PPO | **69.5** | 43.0 | 72.1 |

**解读**：
- 加数学数据让 MATH 涨但其他基本持平
- 加代码 annealing 让 HumanEval 涨，MMLU 略降
- DPO 比 PPO 整体好

ML 团队据此**选组合**做最终版。

---

## 5. 训练常见事故的 SRE 词汇

### 5.1 Loss Spike

**现象**：loss 曲线突然飙高。
**原因**：
- 数据里有 outlier（比如一段垃圾文本）
- 优化器 numerical 问题
- Gradient 爆炸

**ML 处理流程**：
- Skip 这批数据，从最近 checkpoint 恢复
- 或降低 learning rate 继续
- 或直接中止重跑

**SRE 要知道**：
- **Checkpoint 必须频繁保存**（每 1-5k steps）
- 单个 checkpoint 可达 1-5 TB，存储设计要跟上
- 从 checkpoint 恢复的流程必须演练过

### 5.2 Divergence

Loss 不再下降甚至上升。通常 recipe 有问题（超参选错、数据质量问题）。

### 5.3 Grokking

训练很久后模型突然"开窍"，验证集准确率从接近 0 跳到接近 100%。2021 年 OpenAI 观察到的现象。生产训练里不常遇到。

### 5.4 Catastrophic Forgetting

继续训练让模型忘了原本会的技能。**SFT / fine-tune 后特别常见**。应对：混合部分原始数据。

### 5.5 Data Contamination

训练数据里混进了评估集（MMLU 题目等）。导致 benchmark 分数虚高、生产表现不符。

**SRE 要关心**：
- 数据 pipeline 的 contamination check
- Benchmark scores 异常高（"太好了"）要警惕

---

## 6. 训练的经济学（SRE 要记的数字）

### 6.1 Pre-training 成本（2026 估算）

| 模型规模 | GPU × 天数 | 大致成本 |
|---|---|---|
| 70B-class | 1000 × H100 × 30 天 | **$2M** |
| 400B-class MoE | 4000 × H100 × 60 天 | **$15M** |
| Frontier 1T+ | 10000+ × H100 × 90+ 天 | **$100M+** |

### 6.2 Post-training 成本

通常比 pre-training **便宜 100×** 以上：
- SFT：千元到十万美元级
- RLHF：万到百万美元级

### 6.3 Inference vs Training

**推理**是持续成本，训练是一次投入。
一个被广泛使用的模型，推理累计成本**很快超过训练成本**（几周到几个月）。

---

## 7. SRE 在训练流程里的角色

### 你可能不负责
- 设计 recipe
- 写 training code
- 调超参

### 但你一定要负责
- **Training cluster 的可用性**（节点失败、网络抖动）
- **Checkpoint 存储**（容量、冗余、跨区复制）
- **训练 run 的监控**（loss 曲线、GPU 利用率、通信效率）
- **Incident**（loss spike、OOM、node crash 的处理流程）
- **Data pipeline 的 uptime**（见 [共同语言 02](02-Data是ML的真正核心.md)）
- **安全与合规**（训练数据不能泄露、不能污染）

---

## 8. SRE 和 ML 对话的真实例子

> **ML**：我们要跑 Llama 3.3 的 mid-training，data mixing 加 20% 数学数据，用 constant LR 2e-4。
> **以前的 SRE**：嗯……需要多少 GPU？
> **现在的 SRE**：Mid-training 用了什么 base model？你们预期 MATH 涨多少？别的指标的 regression 监控做了吗？Checkpoint 节奏是？

看到差别没有？**"共同语言"就是能追问到有意义的深度**。

---

## 9. 关键词汇速查表（务必记住）

| 词 | 意思 |
|---|---|
| **Pre-training** | 第一阶段大规模训练，学"世界知识" |
| **Mid-training / Annealing** | 中间阶段，用精选数据提升特定能力 |
| **Post-training** | 对齐阶段（SFT + RLHF/DPO + Safety）|
| **SFT** | Supervised Fine-tuning，监督微调 |
| **RLHF** | RL from Human Feedback，用人类偏好优化 |
| **DPO** | Direct Preference Optimization，简化版 RLHF |
| **Recipe** | 完整训练配方（数据+架构+超参+流程）|
| **Ablation** | 对比实验（改 1 个变量看效果）|
| **Checkpoint** | 训练中保存的模型快照 |
| **Loss spike** | Loss 突飞，training 事故 |
| **Contamination** | 训练数据污染（混进 eval set） |
| **Step** | 训练的迭代单位（非 epoch） |
| **Cutoff date** | 训练数据截止日 |
| **Base model** | Pre-training 后的模型（未对齐）|
| **Instruction-tuned** | 经过 SFT 的模型 |
| **Model card** | 模型发布文档 |

---

## 10. 给 SRE 的一句话总结

> [!IMPORTANT]
> 训练不是"ML 团队的黑盒"。SRE 至少要懂 **生命周期三段（pre/mid/post）+ Recipe + Checkpoint + Loss spike**，才能在会议室不失语、在 incident 里发挥作用。
>
> **这是 "和 ML 工程师做同事" 的入场券，不是选修课**。

---

## 11. 参考资料

- Llama 3 Herd of Models paper（最易读的 frontier recipe）— https://arxiv.org/abs/2407.21783
- DeepSeek V3 Technical Report — https://github.com/deepseek-ai/DeepSeek-V3
- Qwen 2.5 / 3 Technical Report — https://github.com/QwenLM/Qwen
- Anthropic · Constitutional AI paper — https://arxiv.org/abs/2212.08073
- Chinchilla paper（Scaling laws）— https://arxiv.org/abs/2203.15556
- Kaplan et al · Scaling Laws for Neural Language Models — https://arxiv.org/abs/2001.08361

---

[📖 目录](../README.md)  ·  [共同语言 02 · Data 是 ML 的真正核心 →](02-Data是ML的真正核心.md)
