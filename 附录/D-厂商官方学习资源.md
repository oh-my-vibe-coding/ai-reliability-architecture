---
title: 附录 D · 厂商官方学习资源（📊 每季度校对）
updated: 2026-05-24
tags: [appendix, training, vendor-official, 📊]
---

# 附录 D · 厂商官方学习资源

> [← 返回目录](../README.md)

> [!WARNING]
> 本节包含**厂商课程名、URL、课程数量、平台入口**等快变信息。内容**快照日期为 2026-05-05**；URL 和课程名每季度可能变。实际使用前请**访问厂商官方主站**确认当前状态。**脚本自动扫链**不替代人工访问。

> [!NOTE]
> **本附录定位**：列出厂商官方的**结构化培训资源**，对照本书章节给出学习路径。**不是"必须学"**——本书自身是独立完整的手册；这些是**补充和实操场地**。
>
> **漂移度**：📊（快变）。URL 和课程名每季度变，**维护者按 [月度更新清单](../维护/月度更新清单.md) 校对**。

---

## 1. Anthropic（Claude 系列）

### Anthropic Academy（结构化平台，含证书）
- **URL**：https://anthropic.skilljar.com/
- **入口**：https://www.anthropic.com/learn
- **主要 Track**：
  - **Build with Claude** —— API 开发
  - **Claude for Work** —— 团队 / 组织部署
  - **Claude for Personal use** —— 个人使用
- **典型课程**：AI Fluency、API Development、MCP、Claude Code 专项
- **带完成证书**

### GitHub · anthropics/courses （代码教学）
- **URL**：https://github.com/anthropics/courses
- **5 个课程**（Jupyter Notebook，建议按序）：

| # | 课程 | 教什么 |
|---|---|---|
| 1 | **Anthropic API Fundamentals** | API key、模型参数、多模态 prompt、流式 |
| 2 | **Prompt Engineering Interactive Tutorial** | 提示词工程系统教学（也有 AWS Workshop 版）|
| 3 | **Real World Prompting** | 真实复杂 prompt 的编写（也有 Google Vertex 版）|
| 4 | **Prompt Evaluations** | 生产级 prompt eval |
| 5 | **Tool Use** | Tool use / function calling 全指南 |

### Anthropic Cookbook（代码样例）
- **URL**：https://github.com/anthropics/anthropic-cookbook
- 大量任务化代码：结构化输出、PDF 处理、vision、embedding、retrieval 等

### Claude Code 官方文档
- **URL**：https://code.claude.com/docs/en/overview
- 已在 [深入 03](../深入/03-模型与工具场景化最佳实践.md) 详细讨论
- 必看：Quickstart、Memory（CLAUDE.md）、Skills、Hooks、Sub-agents、Agent SDK

### Claude 模型与 API 官方文档
- **URL**：https://platform.claude.com/docs/
- 必读：Models、Prompt engineering、Extended thinking、Tool use、Prompt caching
- 对应本书：[深入 12 · Claude / GPT / Gemini 三大模型系列使用指南](../深入/12-Claude-GPT-Gemini三大模型系列使用指南.md)

---

## 2. OpenAI

### OpenAI Cookbook
- **URL**：https://github.com/openai/openai-cookbook
- Python / Node 实操示例：embedding、fine-tuning、function calling、prompt caching、Responses API 等

### OpenAI Platform 官方文档
- **URL**：https://platform.openai.com/docs
- 含 Quickstart、Models、Guides、API Reference
- 必读：Models、Responses API、Function calling、Structured outputs、Reasoning、Prompt caching
- 对应本书：[深入 12 · Claude / GPT / Gemini 三大模型系列使用指南](../深入/12-Claude-GPT-Gemini三大模型系列使用指南.md)

### DeepLearning.AI 合作课程
- **URL**：https://www.deeplearning.ai/short-courses/
- 与 OpenAI 共同出品，Andrew Ng 参与：
  - ChatGPT Prompt Engineering for Developers
  - Building Systems with the ChatGPT API
  - LangChain for LLM Application Development
  - 其他多门短课（每门 1-2 小时）

### OpenAI Evals（开源）
- **URL**：https://github.com/openai/evals
- 生产级 evals 框架 + 大量示例 eval

---

## 3. Google（Gemini）

### Gemini API Cookbook
- **URL**：https://github.com/google-gemini/cookbook
- Jupyter notebook 格式的样例集

### Google AI Studio 教程
- **URL**：https://ai.google.dev/
- Quickstart + 各任务指南
- 必读：Models、Text generation、Long context、Thinking、Function calling、Live API
- 对应本书：[深入 12 · Claude / GPT / Gemini 三大模型系列使用指南](../深入/12-Claude-GPT-Gemini三大模型系列使用指南.md)

### Google Cloud · Vertex AI Learning
- **URL**：https://cloud.google.com/vertex-ai/docs/generative-ai/learn/overview
- 企业侧部署 / 整合内容

---

## 4. Hugging Face（开源生态入口）

### HuggingFace Learn
- **URL**：https://huggingface.co/learn
- 免费系统课程：
  - **NLP Course**
  - **Deep RL Course**
  - **Diffusion Models Course**
  - **LLM Course**（2024 新）
- 特别有价值：**Alignment** 和 **AI Agents** 的专门课程

### HF Cookbook（实操样例）
- **URL**：https://huggingface.co/learn/cookbook

---

## 5. 其他厂商

### DeepSeek
- **URL**：https://api-docs.deepseek.com/
- 相对简洁的官方文档。**中文支持好**

### Mistral
- **URL**：https://docs.mistral.ai/
- Quickstart + Guides

### Alibaba Qwen
- **URL**：https://huggingface.co/Qwen （HF 上的 model cards + 技术报告）
- 官方博客：https://qwenlm.github.io/

### xAI Grok
- **URL**：https://docs.x.ai/docs/models

---

## 6. 按本书章节的学习路径映射

建议**边学本书边挑对应厂商课程做实操**。Table 按 Track 组织：

### 能力面

| 本书章节 | 推荐对应官方课程 | 为什么 |
|---|---|---|
| [引章 · 大模型速览](../01-引章-大模型速览.md) | Anthropic Course 1（API Fundamentals）| 最短路径体感 |
| [Unit 0 · API 上手](../练习/Unit0-AI大模型上手/总览.md) | Anthropic Course 1 + Course 5（Tool Use）| 直接组合成你的 CLI Agent |
| [Unit 1 · Agent 自治](../练习/Unit1-Agent自治与致命三角/总览.md) | Anthropic Claude Code docs · Skills/Hooks/Sub-agents 篇 | 官方 Agent 架构示例 |
| [Unit 2 · Trace-Eval](../练习/Unit2-TraceEval统一可观测性/总览.md) | Anthropic Course 4 + OpenAI Evals repo | Eval 的两种风格 |
| [深入 02 · Prompt Caching](../深入/02-Prompt-Caching原理.md) | Anthropic · Prompt Caching docs 专章 | 官方细节最全 |
| [深入 03 · 选型](../深入/03-模型与工具场景化最佳实践.md) | 三大厂 cookbook 各选一个任务动手 | 比 benchmark 更真实的感知 |
| [深入 06 · Eval Pipeline](../深入/06-Eval-Pipeline设计.md) | Anthropic Course 4 · Prompt Evals | 系统 eval 设计 |

### 学习方法（不适用——厂商没有"学习方法"培训）

### 协作面

| 本书章节 | 推荐对应官方课程 | 为什么 |
|---|---|---|
| [共同语言 01 · 训练生命周期](../共同语言/01-训练生命周期与Recipe.md) | HuggingFace LLM Course | 开源视角 + 动手 |
| [共同语言 02 · Data](../共同语言/02-Data是ML的真正核心.md) | HuggingFace Datasets 课程 | Dataset 工程化 |
| [共同语言 04 · Alignment](../共同语言/04-Alignment的词汇.md) | HuggingFace DRL + Alignment 课程 | 相对中立的学术视角 |

---

## 7. "该不该做这些课程" 判断

> [!TIP]
> **不做比做更重要的判断**。你**没必要做完所有**——本书已经覆盖概念。厂商课程价值在**动手实操**，不在概念传授。

### 值得做的（高 ROI）
- ✅ **Anthropic Course 1 + 5**（API + Tool Use）—— Unit 0 的完美搭配
- ✅ **Anthropic Course 4**（Evals）—— Unit 2 的动手版
- ✅ **OpenAI Cookbook 里和你场景匹配的 recipe** —— 而不是整个 cookbook
- ✅ **Anthropic Claude Code docs** —— 如果你在用 Claude Code，必读

### 可选（中 ROI）
- 🟡 Anthropic Course 2（Prompt Engineering）—— 如果你写很多 prompt
- 🟡 HuggingFace LLM Course —— 如果你要深化 ML 侧理解
- 🟡 DeepLearning.AI 短课 —— 娱乐性学习

### 别全做（低 ROI）
- ❌ "凑整套证书" —— 没人看你证书
- ❌ 过完所有 cookbook —— 信息过载 + 遗忘快
- ❌ 做 marketing 向的课程 —— 少实质

---

## 8. 厂商官方培训的"气味"

选的时候注意：

| 好气味 | 坏气味 |
|---|---|
| Jupyter notebook + 可运行代码 | 只有 slides / 视频 |
| 结尾有 exercises | 一路都在 demo |
| 有 failure modes 讨论 | 只讲 happy path |
| 定期更新（看 commit history）| 2 年没动 |
| 和产品文档互相链接 | 孤立存在 |

Anthropic Courses 和 OpenAI Cookbook **符合好气味**。很多 YouTube "tutorial" **不符合**。

---

## 9. 配合本书的学习节奏

### 建议做法
- 本书章节是**骨架**
- 厂商官方课程是**实操场**
- **每个 Unit 做 1-2 个对应厂商课程**的实操
- **用 B2 方式**（见 [第 17 章](../练习/10-三个核心训练动作.md)）：自己动手，AI 挑错

### 千万别做的
- ❌ 先把厂商课程全做完再来学本书——会迷失
- ❌ 本书学完了再想起做实操——记忆已流失
- ❌ 一边做本书一边做所有 cookbook——认知过载

---

## 10. 链接死活的保险

URL 会变。如果本附录的链接失效：

1. **先搜**：`site:anthropic.com [keyword]` / `site:openai.com [keyword]`
2. **去 GitHub**：厂商 GitHub org 永远是最可靠起点
3. **Wayback Machine**：https://web.archive.org/

**维护提示**：本附录**每季度校对**一次（见 [漂移度表](../维护/漂移度表.md)）。

---

## 11. 给 SRE 的一句话总结

> [!IMPORTANT]
> 厂商官方培训**不是必读**——本书自身已经独立完整。
>
> 厂商课程的真正价值是 **"让你的手指头熟练起来"**——动手写过带 cache_control 的 API 调用，和只在书上读过，完全不是一个状态。
>
> **选 2-3 门最对口的做透**，胜过浏览 10 门。

---

## 12. 参考索引

| 厂商 | 核心入口 | 最值得做的 |
|---|---|---|
| Anthropic | https://anthropic.skilljar.com/ · https://github.com/anthropics/courses | Course 1 + Course 5 |
| OpenAI | https://github.com/openai/openai-cookbook · https://platform.openai.com/docs | Cookbook 对口 recipe + Evals repo |
| Google | https://github.com/google-gemini/cookbook | Cookbook 对口任务 |
| HuggingFace | https://huggingface.co/learn | LLM Course（深化 ML） |
| DeepSeek / Mistral / Qwen / xAI | 各自官方 docs | 有空再看 |

---

← [附录 C · 术语表](C-术语表.md)  ·  [📖 目录](../README.md)
