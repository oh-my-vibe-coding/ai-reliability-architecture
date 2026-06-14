---
title: 共同语言 02 · Data 是 ML 的真正核心
updated: 2026-05-05
tags: [shared-language, data, pipeline, contamination]
---

# 共同语言 02 · Data 是 ML 的真正核心

> [← 返回目录](../README.md)  ·  前置：[共同语言 01 · 训练生命周期](01-训练生命周期与Recipe.md)

> [!NOTE]
> **核心洞察**：ML 团队 80% 的时间花在**数据**上，不是模型上。懂了数据，才能懂 ML 团队在操心什么。

---

## 0. SRE 常见误解：以为 ML 团队整天在"调模型"

真实的 ML 工程师工位：

- 20%：看 loss curve 纠结参数
- 80%：看**数据质量报告**、**重训 data pipeline**、**debug 数据 schema 错误**

**数据之于 ML，就如同代码之于传统软件**。模型架构在 2-3 家开源方案里选，算法在几个主流里选——**数据的选择和处理，才是真正决定产品走向的变量**。

---

## 1. Pre-training Data Pipeline 的 7 步

```
┌──────────────┐
│ 1. Crawl     │  爬取互联网（CommonCrawl、自家爬虫）
└──────┬───────┘
       ↓
┌──────────────┐
│ 2. Clean     │  去 HTML、boilerplate、样板文字
└──────┬───────┘
       ↓
┌──────────────┐
│ 3. Filter    │  质量过滤（语法、连贯性、毒性）
└──────┬───────┘
       ↓
┌──────────────┐
│ 4. Dedup     │  去重（近重复、哈希、minhash）
└──────┬───────┘
       ↓
┌──────────────┐
│ 5. Decontam. │  去除 eval 集泄露
└──────┬───────┘
       ↓
┌──────────────┐
│ 6. Mix       │  配比（web / code / math / books / 多语言）
└──────┬───────┘
       ↓
┌──────────────┐
│ 7. Tokenize  │  切 token、存成训练友好格式
└──────────────┘
        ↓
     训练用数据
```

**每一步都有大量工程 + 科学**。SRE 能参与的基础设施层在每个阶段都有。

---

## 2. 主流 Pre-training 数据集

SRE 要能听懂这些名字：

| 名字 | 规模 | 性质 | 备注 |
|---|---|---|---|
| **Common Crawl** | 250B+ pages | 公共爬虫 dumps | 原始，需要大量清洗 |
| **C4 (Colossal Clean Crawled Corpus)** | ~750GB | Google 清洗的 CC | T5/Llama 用过 |
| **The Pile** | 800GB | EleutherAI 整理的多源语料 | 开源经典 |
| **RedPajama** | 1.2T token | 复刻 Llama 用的数据 | 开源 |
| **Dolma** | 3T token | AI2 开源高质量语料 | 新一代 |
| **FineWeb** | 15T token | HuggingFace 清洗 CC | 2024 当前最大开源 |
| **FineWeb-Edu** | 1.3T token | FineWeb 中教育内容子集 | 质量高 |
| **The Stack** | 3TB code | BigCode 的代码语料 | 编码模型必用 |
| **Proof Pile 2** | 55B token | 数学论文 | 数学增强 |

**训练一个 frontier 模型大约要 10-15T token**，以上几个混合用。

---

## 3. 数据清洗与过滤（Clean + Filter）

### 3.1 Cleaning 的典型步骤

- 去 HTML tag
- 去 JavaScript / CSS 样板
- 去 URL / 邮箱（可选）
- 去极短文本（< 100 字符）
- 去极长行（> 1000 字符，通常是 log 或代码压缩）
- Unicode normalization

### 3.2 Quality Filter

- **语言识别**（只保留目标语言）
- **困惑度过滤**（用小模型打分，太高 = 乱码）
- **关键词过滤**（去黑话、成人内容）
- **基于 classifier 的过滤**（训一个"高质量分类器"筛）
- **基于 embedding 的筛选**（和 Wikipedia / 书籍相似的保留）

### 3.3 FineWeb-Edu 的方法

HuggingFace 用 LLM 给每页**教育价值**打 0-5 分，只保留 3+。结果：**1/10 的数据，效果接近全量**。

> [!TIP]
> **"数据质量比数量重要"是 2024-2026 的显学**（Phi-3 推到极致）。小模型 + 高质量数据可以在某些任务上打败大模型 + 混乱数据。

---

## 4. Dedup（去重）

**为什么重要**：
- 重复数据让模型**过拟合这些段落**
- 浪费 compute
- 危险情况下会**逐字背诵**隐私数据

### 4.1 技术

- **Exact dedup**：MD5/SHA hash
- **MinHash / LSH**：近重复检测（可以发现"改了几个词的同一篇文章"）
- **Suffix array**：发现长重复子串
- **SimHash**：Google 搜索用的快速近重复

### 4.2 规模挑战

- 10T token 的数据里跑 MinHash：**要数千 CPU 小时 + 几 TB 内存**
- 这是 SRE 能贡献的地方——**数据 pipeline 的分布式工程**

---

## 5. Decontamination（去污染）

**最重要的 SRE 要懂的概念之一**。

### 5.1 什么是 Contamination

训练数据里**混进了 eval 集**。例子：
- MMLU 题目 + 答案出现在 Wikipedia 讨论页
- SWE-bench 题目对应的 GitHub PR 被爬到
- HumanEval 的解答在博客里

**后果**：
- 模型在 benchmark 上分数虚高
- 生产表现和 benchmark 脱节
- 对比其他模型不公平

### 5.2 如何检测

- **精确 N-gram 匹配**：训练数据里搜 eval 题目的 13-gram
- **Canary strings**：在 eval set 里埋特殊字符串，训练完后查模型是否"记得"
- **Dynamic benchmarks**：用模型没见过的新题（但维护难）

### 5.3 ML 团队常说的

- *"这版本的 MMLU 涨了但 pass rate 没涨，怀疑是 contamination"*
- *"我们用了 13-gram decontamination，数据掉 2%"*
- *"要切到 private eval 重测一次"*

SRE 能帮上什么：
- 给 decontamination pipeline 提供大规模字符串匹配的基础设施
- 管理 eval set 的 **canary tokens**
- 保护 private eval 的访问控制

---

## 6. Data Mixing（配比）

**这是 ML 团队 2024-2026 的"黑魔法"所在**。

### 6.1 典型 Mix

一个 frontier 模型的训练数据构成（估算）：

| 类别 | 比例 |
|---|---|
| Web text | 50-60% |
| Code | 15-25% |
| Math / science | 5-15% |
| Books | 5-10% |
| Academic papers | 2-5% |
| Multilingual (非英文) | 10-20% |
| Dialogue / Forums | 2-5% |
| Synthetic | 0-20%（上升中）|

### 6.2 Annealing Mix

**训练末期**（最后 10-20% steps）用**更高质量、更聚焦**的混合：
- 代码比例提到 30%
- 数学比例提到 20%
- 教育内容比例拉高

**为什么**：近因效应——模型最后学的东西影响最大。

### 6.3 ML 团队常说的

- *"这次 annealing mix 里数学开到 25% 了"*
- *"数据 mixing 的 sensitivity 比我们想的大"*
- *"跑了 5 个 ablation 找到最优 ratio"*

---

## 7. Synthetic Data（合成数据）

### 7.1 为什么 2024-2026 火

- 高质量人类数据**见顶**（能爬的都爬了）
- 强模型可以生成**比低质量网页更好的**训练数据
- 可以针对特定能力定向生成（数学推理、代码、对话）

### 7.2 方法

#### 7.2.1 蒸馏（Distillation）——让大模型当老师，小模型当学生

**一句话**：蒸馏就是让一个又贵又强的"老师模型"做题，把解题过程记下来，拿去训练一个又便宜又快的"学生模型"。学生不需要自己从零探索——它直接模仿老师的"思考路径"，用十分之一的成本做出接近的效果。

**一个比喻**：

> 你请了一位日薪 5 万的资深架构师做系统设计。你做的不只是看他的**最终方案**——你把他草稿纸上画过的每一个架构图、否掉的每一种方案、每一次"这里不能这样做因为……"的判断，全部拍下来。然后你拿这些草稿去训练一个初中级工程师——他不一定能达到架构师的水平，但面对同类问题时，他的思考路径**不再是空白的**。

这就是蒸馏和普通 SFT 的区别：

- **普通 SFT**：只给学生看"标准答案"（输入→输出）
- **蒸馏**：给学生看**老师的完整思考过程**（输入→一步步推理→输出），学生学的是"怎么想"，不是"答案是啥"

这也是为什么 DeepSeek-R1 的蒸馏小模型（7B/14B/32B）在推理任务上能做到大模型的 70-80%——因为它们蒸的是 R1 的 **reasoning trace**（一步步的思考链），而不仅仅是 R1 的最终回答。

**LLM 时代蒸馏的三种形态**：

| 形态 | 老师输出什么 | 学生学到什么 | 例子 |
|---|---|---|---|
| **Response-only** | 最终答案 | 回答风格 | Alpaca / Vicuna（用 GPT-4 回答训 LLaMA）|
| **Trace-level** | 完整思考链 | 推理能力 | DeepSeek-R1 distilled → Qwen/Llama 小模型 |
| **Reward-model** | "这个回答打 8 分" | 判断力 | RLHF 里的 reward model 本质上也是一种蒸馏 |

**三种形态的"人话"对照**：

> - Response-only：学生抄了老师的标准答案——格式像、风格像，但遇到没见过的题就不会。
> - Trace-level：学生看了老师的解题草稿——知道怎么一步步推，换道类似的题也能自己推。
> - Reward-model：学生没看老师做题，而是看了老师给全班作业打的分数——学会了"什么样的是好回答"的判断力。

**对 SRE 意味着什么**：

- **蒸馏小模型是成本优化的第三条路**：不是"选更便宜的模型"，也不是"做 prompt caching"，而是**用自家最强模型蒸出一个专属小模型**——虽然蒸馏本身要花一笔生成成本（见 §7.3），但上线后每次推理成本可能是原来的 1/10。
- **蒸馏改变了自托管的门槛**：一个 7B 的蒸馏模型可以在单卡上跑，这意味着你不需要为 70B 旗舰模型规划 GPU 集群——一个 M 系列 MacBook 就能部署推理服务。
- **蒸馏模型的 eval 要重做**：学生模型在老师见过的题上分很高，但在老师没见过的题上可能断崖式下降——这不是模型坏了，是蒸馏的本质局限。**上线前必须用老师模型没见过的样本单独跑一轮 eval**。

**学术源头与实战范例**：

- 学术源头：Hinton et al · *Distilling the Knowledge in a Neural Network* (2015) — https://arxiv.org/abs/1503.02531
- LLM 时代必读（含中文）：DeepSeek-AI · *DeepSeek-R1* (2025) — 把 R1 的 reasoning trace 蒸到 Qwen / Llama 小模型并开源权重。英文 arXiv https://arxiv.org/abs/2501.12948 ；中文版 PDF 见官方仓库 https://github.com/deepseek-ai/DeepSeek-R1/blob/main/DeepSeek_R1.pdf

#### 7.2.2 角色扮演生成（Persona-based Generation）

- 让强模型扮演不同角色生成对话（"现在你是一个暴躁的用户……"）
- 多样性比"一个身份一直说"更好

#### 7.2.3 先验证再训练（Verify-then-train）

- 数学题：模型解 → 用 solver / 测试用例校验 → 只保留对的
- Code：模型写 → 跑测试 → 只保留 pass 的
- **本质**：机器自动做 quality control，不靠人工一条条审

#### 7.2.4 Microsoft Phi 的极端路线

- 几乎全合成数据
- 3.8B 小模型在某些 benchmark 打败 70B
- **证明了一件事**：数据质量比模型大小重要，尤其在训练预算固定的情况下

### 7.3 SRE 要知道的

- **合成数据的成本**：生成 1B token 的 Claude/GPT 数据可能 **$500K-$5M**
- **合成数据的 quality control**：也是 eval pipeline 问题
- **合法性**：用 OpenAI 输出训 LLM **违反 OpenAI 条款**（很多公司还是做了）

---

## 8. Post-training Data

与 pre-training 不同：
- **小得多**（几万到百万条）
- **手工 + 合成结合**
- **标注质量**远高于 pre-training 数据

### 8.1 SFT 数据

**每条是**：
```json
{
  "system": "你是一个乐于助人的助手",
  "user": "写一个 Python 函数排序列表",
  "assistant": "```python\ndef sort_list(lst): return sorted(lst)\n```"
}
```

**来源**：
- 手工标注（贵）
- 从 ChatGPT / Claude 蒸馏（问题：条款 + 质量漂移）
- 自己模型早期版本生成 + 筛选

### 8.2 RLHF / DPO 数据

**每条是**：
```json
{
  "prompt": "...",
  "chosen": "较好的回答",
  "rejected": "较差的回答"
}
```

人类 annotator 对比两个回答选一个更好的。**10k-100k 对**就能显著改变模型行为。

---

## 9. 数据工程的 SRE 机会

### 9.1 你能做的基础设施

- **Pipeline orchestration**（Airflow / Dagster / Prefect）
- **分布式计算**（Spark / Ray 做 dedup / clean）
- **存储**：PB 级数据的冷热分层
- **Quality monitoring**：数据 schema drift、volume anomaly
- **Reproducibility**：数据版本化（DVC、lakeFS）

### 9.2 监控指标

- **Pipeline uptime**：任一 stage 挂都会拖慢下游
- **Data volume per day**：突降 = 上游 broken
- **Token count produced**：最终输出指标
- **Dedup ratio**：突增可能是新数据源重复
- **Contamination check results**：canary token 检测
- **Storage usage**：常常爆炸

### 9.3 事故类型

- 爬虫被封（上游断流）
- Schema 改变（下游 parse 失败）
- Dedup OOM（数据暴增）
- Checkpoint 损坏
- 不小心删除数据（SRE 经典错误）
- 数据泄露（PII / 版权）

---

## 10. 合规与版权

**2025-2026 的大事**：NYT vs OpenAI 案、艺术家集体诉讼。

**SRE 需要知道**：
- 训练数据的**版权审计**是合规要求
- PII 数据要么不收，要么清洗
- 内部数据训练的模型**不能污染到公共发布模型**（隔离 pipeline）
- **Data provenance**（来源追溯）会成为标配

---

## 11. ML ↔ SRE 对话的真实例子

> **ML**：我们要重跑一次 pre-training data pipeline，加 FineWeb-Edu 3+ 子集，重做 dedup 和 decontamination。估计数据从 10T 涨到 12T。
> **老 SRE**：好，我给你开个 ticket。
> **懂了的 SRE**：12T 的 MinHash dedup 你们之前是用 Spark 跑的吧，上次 OOM 了，这次我把 executor memory 调到 256G，再把数据 shuffle 优化一下。Decontamination 用 canary token 还是 13-gram？我准备一下 canary 列表。

**这就是共同语言的力量**——不是 SRE 会做 ML 的活，是 SRE 能**精准贡献自己的长处**。

---

## 12. 关键词汇速查

| 词 | 意思 |
|---|---|
| **CommonCrawl / FineWeb / Dolma** | 主流 pre-training 数据集 |
| **Mixing** | 不同类型数据的配比 |
| **Annealing mix** | 训练末期的高质量混合 |
| **Contamination** | 训练数据混入 eval set |
| **Canary token** | 埋在 eval 集里检测污染的特殊字符串 |
| **MinHash / LSH** | 近重复检测算法 |
| **Synthetic data** | 用强模型生成的训练数据 |
| **Distillation** | 用强模型蒸馏训小模型 |
| **Provenance** | 数据来源追溯 |
| **PII** | Personally Identifiable Information |
| **Data pipeline drift** | 数据流变化导致质量变动 |

---

## 13. 给 SRE 的一句话总结

> [!IMPORTANT]
> ML 团队最大的痛点**几乎永远是 "数据"**，不是 "模型"。
>
> 懂了 data pipeline，SRE 就能提供最值钱的工程价值——**大规模 data infra、dedup 性能、contamination 审计、pipeline uptime**。
>
> **数据是 ML 的代码，Data pipeline 是 ML 的生产线**。SRE 是这条生产线的天然 owner。

---

## 14. 参考资料

- Penedo et al · 《The RefinedWeb Dataset》— https://arxiv.org/abs/2306.01116
- HuggingFace · FineWeb 技术博客 — https://huggingface.co/spaces/HuggingFaceFW/blogpost-fineweb-v1
- AI2 · Dolma paper — https://arxiv.org/abs/2402.00159
- Microsoft · Phi-3 Technical Report — https://arxiv.org/abs/2404.14219
- Lee et al · Deduplicating training data makes LMs better — https://arxiv.org/abs/2107.06499
- Hinton et al · Distilling the Knowledge in a Neural Network — https://arxiv.org/abs/1503.02531
- DeepSeek-AI · DeepSeek-R1（含中文 PDF 与开源蒸馏小模型）— https://github.com/deepseek-ai/DeepSeek-R1 · arXiv https://arxiv.org/abs/2501.12948
- OpenAI / Anthropic · 数据 policy & safety 文档

🔄 复习：[核心概念卡](../复习/核心概念卡.md) · [Active Recall 题库](../复习/Active-Recall题库.md)

---

← [共同语言 01 · 训练生命周期](01-训练生命周期与Recipe.md)  ·  [📖 目录](../README.md)  ·  [共同语言 03 · Research-level Evaluation →](03-Research-Level-Evaluation.md)
