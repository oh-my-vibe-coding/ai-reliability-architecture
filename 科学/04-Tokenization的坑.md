---
title: 科学 04 · Tokenization 的坑
updated: 2026-07-02
tags: [science, tokenization, cost, multilingual]
---

# 科学 04 · Tokenization 的坑

> [← 返回目录](../README.md)  ·  前置：[引章 · 大模型速览](../01-引章-大模型速览.md)  ·  相关：[深入 02 · Prompt Caching](../深入/02-Prompt-Caching原理.md)  ·  [深入 04 · 为什么"你好"消耗数万 token](../深入/04-为什么简单你好也消耗数万token.md)

> [!NOTE]
> **核心问题**：为什么 GPT 数不清 "strawberry" 里有几个 r？为什么中英文的 token 经济学差这么多？为什么 Opus 4.7 换了 tokenizer 账单就不一样？这些都不是模型"笨"，是 **tokenization** 的固有局限。

---

## 0. 一句话本质

> **模型不看字符，看 token**。Tokenizer 是字符和 token 之间的翻译器——**翻译不是无损的，而且翻译规则决定了很多"怪现象"**。

---

## 1. BPE（Byte Pair Encoding）如何工作

当前主流模型（GPT、Claude、Llama、Qwen）几乎都用 BPE 或其变体。

### 1.1 训练阶段

1. 从字符开始（每个 Unicode 字符是一个初始 token）
2. 在训练语料里统计**最频繁的字符对**
3. 把最频繁的对合并成一个新 token
4. 重复直到词表达到目标大小（常见 50k-200k）

### 1.2 推理阶段

对输入文本：
1. 拆成字符
2. 按训练阶段合并规则**尽量合并**成大 token
3. 输出 token 序列

### 1.3 直观例子

训练数据里 "the" 出现极多：
- 合并 `t + h` → `th`
- 合并 `th + e` → `the`
- **"the" 最终是 1 个 token**

训练数据里 "qwzxy" 从没出现：
- 无法合并
- **"qwzxy" 是 5 个 token**（每字一个）

---

## 2. 为什么中英文 token 经济学差这么大

### 2.1 训练数据构成

大部分 LLM 的训练数据（尤其是西方厂商）：
- 英文：50-70%
- 代码：10-20%
- 其他语言：剩下的被中文、西班牙、法语、日语等分摊

**后果**：英文字符对被合并的次数远多于中文。

### 2.2 具体数字（2026 年前后主流模型）

| 单位 | GPT-4o tokenizer | Claude tokenizer | Qwen tokenizer | Llama 3 |
|---|---|---|---|---|
| **英文每词平均 token** | ~1.35 | ~1.33 | ~1.25 | ~1.25 |
| **中文每字平均 token** | 1.5-2.0 | 1.3-1.8 | **0.6-1.0** | 1.0-1.5 |

**结论**：
- 英文：1 词 ≈ 1.3 token（即 1 token ≈ 0.75 个英文词，各家 tokenizer 差异不大）
- 中文：**Qwen 中文最省**（专门训了中文），OpenAI 中文**比英文贵约 3 倍**

### 2.3 成本影响（真实账单）

假设同一段信息：
- 英文 1000 词
- 中文 2500 字（等价信息量）

用 GPT-4o：
- 英文：1000 × 1.35 = **1350 token**
- 中文：2500 × 1.8 = **4500 token**（贵约 3.3 倍）

用 Qwen：
- 英文：1000 × 1.25 = **1250 token**
- 中文：2500 × 0.8 = **2000 token**（比英文只贵 1.6 倍）

> [!IMPORTANT]
> **SRE 含义**：如果你做中文业务，**模型选型要把 tokenization 纳入成本账**。Qwen / DeepSeek / Kimi 等国产模型在中文 token 效率上有显著优势，这不是"国产情怀"，是**纯粹的工程优势**。

---

## 3. 数字为什么坑

### 3.1 "数 r 问题"的根因

问 GPT "strawberry 里有几个 r"，它常答错（2 个）。

**真相**：模型看到的不是 `s-t-r-a-w-b-e-r-r-y`，而是 `["straw", "berry"]`（2 个 token）。

字符级的统计在 token 层面**看不到**。模型要"数 r"必须先**拆 token**，这是额外推理步。

### 3.2 数字 tokenization 的不稳定性

**关键数字"17234"**可能被切成：
- `["17", "234"]`（如果 17 和 234 都在词表）
- `["1", "7", "2", "3", "4"]`（每字一个）
- `["172", "34"]`（别的组合）

**取决于 tokenizer 训练时看到过什么数字**。

**后果**：
- 模型对数字的"理解"不是位值式的（ones/tens/hundreds）
- 数学运算是"基于 token 模式"的，**不是真正的计算**
- 超过训练见过的数字就不可靠

### 3.3 为什么"写代码比算术好"

代码里 "17" 这个数字固定是 `"17"` token。
算术里 "173 + 289" 里 "173" 和 "289" 被切可能完全不同。

**这就是为什么 LLM 普遍不擅长精确计算**——不是"不聪明"，是 tokenization 没给它足够一致的表示。

### 3.4 SRE 含义

- **涉及精确数字的业务，用 tool use 让模型调用计算器**
- **监控模型输出里"不合理的数字"**（日期错位、金额算错）
- **结构化抽取时数字字段加 schema validator 硬校验**

---

## 4. 其他常见的 tokenization 坑

### 4.1 URL 的坑

URL 里的特殊字符、参数会被切得稀碎：

```
https://example.com/api/v2?user_id=123&session=abc
→ ["https", "://", "example", ".com", "/", "api", "/", "v2", "?", "user", "_id", "=", "123", "&", "session", "=", "abc"]
```

- **token 数极高**
- **模型理解 URL 结构能力弱**
- 解决：用 tool use 处理 URL，别让模型自己拼

### 4.2 代码里的空格和缩进

Python 的缩进敏感。不同 tokenizer 对 `"    "`（4 空格）处理不同：
- GPT-4：常被合并成 1 token
- 某些模型：4 个 token（每空格一个）

**后果**：
- 输出 Python 代码有时缩进错
- 某些 tokenizer 对缩进式代码成本额外高

### 4.3 Emoji 和 Unicode 的代价

一个 emoji 在 UTF-8 里可能是 4 字节。tokenizer 对 emoji 的处理参差不齐：
- 主流 BPE：1 emoji ≈ 2-4 tokens
- 冷门 emoji：每字节一个 token

**后果**：重 emoji 业务成本偏高。

### 4.4 少数民族语言 / 古文

蒙古文、藏文、彝文、甲骨文……这些训练数据极少：
- 每字符可能 3-8 个 token
- 模型输出能力也弱

**SRE 对策**：对这些语言的业务，考虑用**专门训练的模型**（如面向东南亚的 SEA-LION、藏文专用模型等）。

---

## 5. Opus 4.7 的 tokenizer 事件（2026-06 快照 🕒）

2026 年 Anthropic 给 Claude Opus 4.7 换了 tokenizer（4.8 沿用同一套）：

- Sonnet 4.6：每 1M token ≈ **750k 英文词**
- Opus 4.7+（含 4.8）：每 1M token ≈ **555k 英文词**

同样一段内容，词数固定，Opus 把它切成的 token 更多——多多少？算的是 `750k / 555k ≈ 1.35`，即 **Opus 4.7+ 的 token 体积比 Sonnet 4.6 大约 1.35×，多约 35%**。

> [!CAUTION]
> 这里很容易把方向算反。"555 比 750 少 26%"说的是 Sonnet 比 Opus 省，分母是 750；而我们要的是"Opus 比 Sonnet 多多少"，分母得是 555——`750/555-1 ≈ 35%`。账单跟着 token 数走，所以**对成本有意义的方向是 35%（1.35×），不是 26%**。

**意味着**：
- **同样一段内容，Opus 4.7+ 的 token 数比 Sonnet 4.6 多约 35%**
- 即使单价一样，Opus 4.7+ 的实际成本高约 35%
- 迁移时**账单会"莫名其妙涨"**

**为什么 Anthropic 要换**：
- 更细的 tokenization 可能对 reasoning 质量有利
- Tokenizer 决定了模型的"语感"

**SRE 含义**：
- 跨模型 / 跨版本迁移时，**按"token 数"比价是错的**；要按"完成同样任务消耗的 token"比价
- 成本预估要跑自己的数据实测，不信官方定价表的"表面数字"

---

## 6. Tokenization 对 Prompt Caching 的影响

回忆 [深入 02](../深入/02-Prompt-Caching原理.md)：**Prompt Caching 按 token 粒度做 prefix 匹配**。

**问题**：
- 同样的文字，**不同 tokenizer 切出不同 token 序列**
- 你从 Claude 切到 GPT：prompt 内容一样，**token 序列完全不同**
- 你不能"跨厂商"共享缓存
- 甚至同厂商**换 tokenizer 版本**也让缓存全失效

**SRE 含义**：
- 模型版本升级 = 缓存失效 = 成本冲击
- 灰度发布预算要留出 **"缓存 cold period"**（5-10 分钟内成本可能翻倍）

---

## 7. 实用工具和经验规则

### 7.1 预估 token 数

**Python 工具**：

```python
# Anthropic
import anthropic
client = anthropic.Anthropic()
count = client.messages.count_tokens(
    model="claude-opus-4-7",
    messages=[{"role": "user", "content": "你好"}]
)

# OpenAI
import tiktoken
enc = tiktoken.encoding_for_model("gpt-5")
tokens = enc.encode("你好")

# Qwen
from transformers import AutoTokenizer
tok = AutoTokenizer.from_pretrained("Qwen/Qwen3-32B")
tokens = tok.encode("你好")
```

### 7.2 经验比例（粗估）

| 内容类型 | 英文 | 中文 | 代码 | JSON |
|---|---|---|---|---|
| token / 字符（GPT tokenizer）| 0.25 | 1.5 | 0.3 | 0.4 |
| token / 字符（Qwen tokenizer）| 0.25 | 0.8 | 0.3 | 0.4 |

粗估：**中文字数 × 1.5 ≈ GPT token 数**；**中文字数 × 0.8 ≈ Qwen token 数**。

### 7.3 成本优化规则

1. **跨语言业务**：中文重的场景用 Qwen / DeepSeek / Kimi 等中文友好模型
2. **URL / 结构化文本**：用 tool 处理，避免让模型"看到" URL 原文
3. **大量数字 / 表格**：做前置抽取成结构化再喂模型
4. **模型升级验证**：换 tokenizer 前**重新估成本**
5. **缓存失效预算**：灰度发布期的成本预留

---

## 8. 常见误区

- ❌ **"字符数等于 token 数"** — 差很多，尤其中文
- ❌ **"token 单价一样就成本一样"** — tokenizer 不同差 20%+
- ❌ **"模型能数字符"** — 在 token 层看不见字符
- ❌ **"LLM 会做数学"** — 它会模仿算术，不是真算
- ❌ **"prompt 里加空格不影响"** — 可能破坏 tokenization 进而破坏缓存
- ❌ **"版本升级只要效果好就行"** — tokenizer 一变成本大改、缓存归零

---

## 9. SRE 实操清单

- [ ] 每个主要模型都装对应 tokenizer，**预估成本用真实 token 数**
- [ ] 按**业务语言**选模型，不只是按"能力榜单"
- [ ] 数字敏感业务上 tool calling（计算器 / 数据库）
- [ ] 监控 **per-language 和 per-task 的 token 消耗**分布
- [ ] 模型版本升级前跑 **token 数对比**的 dry run
- [ ] 缓存策略里标注"所依赖的 tokenizer 版本"
- [ ] 输出里的数字 / 日期 / 金额**必做 schema 校验**

---

## 10. 给 SRE 的一句话总结

> [!IMPORTANT]
> Tokenizer 不是"看不见的底层细节"——它直接决定**成本、缓存命中、数学能力、多语言表现**。
>
> SRE 必须把 tokenizer 当成**一等的容量规划变量**，像对待 GPU 显存一样对待它。
>
> **换模型 = 换 tokenizer = 成本结构改变**。没做 dry run 就上线的灰度都是赌博。

---

## 11. 参考资料

- Sennrich et al · 《Neural Machine Translation of Rare Words with Subword Units》(BPE) (2015) — https://arxiv.org/abs/1508.07909
- Kudo & Richardson · 《SentencePiece》(2018) — https://arxiv.org/abs/1808.06226
- Karpathy · 《Let's build the GPT Tokenizer》视频讲解 — https://www.youtube.com/watch?v=zduSFxRajkE
- OpenAI · tiktoken 库 — https://github.com/openai/tiktoken
- Anthropic · Tokenizer docs — https://docs.claude.com/en/docs/about-claude/tokenization
- Qwen · Tokenizer details on HuggingFace — https://huggingface.co/Qwen
- Simon Willison · 《GPT-4 can't count letters》— https://simonwillison.net/2023/Sep/29/llms-count-characters/

🔄 复习：[核心概念卡](../复习/核心概念卡.md) · [Active Recall 题库](../复习/Active-Recall题库.md)

---

← [科学 03 · Quantization 为什么有时坏](03-Quantization为什么有时坏.md)  ·  [📖 目录](../README.md)
