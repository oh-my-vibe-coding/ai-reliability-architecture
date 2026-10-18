---
title: 附录 B · 一手材料与参考文献
updated: 2026-10-17
tags: [appendix]
---

# 附录 B · 一手材料与参考文献

> [← 返回目录](../README.md)

本附录只列**一手材料和公认经典**。列在这里的东西，要么是某个训练 Unit 会读的，要么是值得反复回看的。

---

## AI 大模型与 Agent 开发（Unit 0）
- [Anthropic API 官方文档](https://docs.claude.com/en/api/messages) · messages / tool use / streaming 三章
- Anthropic · [《Building effective agents》](https://www.anthropic.com/research/building-effective-agents)（2024）
- Simon Willison · [《Embeddings: What they are and why they matter》](https://simonwillison.net/2023/Oct/23/embeddings/)

## Agent 架构与安全（Unit 1）
- Simon Willison · [《The lethal trifecta for AI agents》](https://simonwillison.net/2025/Jun/16/the-lethal-trifecta/) 及 [prompt-injection tag 系列](https://simonwillison.net/tags/prompt-injection/)
- Simon Willison · [《Designing Agentic Loops》](https://simonwillison.net/2025/Sep/30/designing-agentic-loops/)（2025）
- Anthropic · [Agent 架构相关官方文章](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)
- OpenAI · [Function calling safety best practices](https://platform.openai.com/docs/guides/safety-best-practices)

## 质量可观测性与 Evals（Unit 2）
- Hamel Husain · [《Your AI Product Needs Evals》](https://hamel.dev/blog/posts/evals/)
- Eugene Yan · [LLM evaluation 系列](https://eugeneyan.com/writing/llm-evaluators/)
- [Langfuse 官方架构文档](https://langfuse.com/docs/evaluation/overview)
- [LangSmith 官方架构文档](https://docs.langchain.com/langsmith)
- Honeycomb · [LLM observability 相关博客](https://www.honeycomb.io/blog)

## AI 系统可靠性与事故复盘（Unit 3）
- Anthropic · [Postmortem of three recent issues](https://www.anthropic.com/engineering/a-postmortem-of-three-recent-issues)（**重要，至少读三次**）
- Anthropic · [Effective Context Engineering for AI Agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)
- [vLLM 官方文档](https://docs.vllm.ai/)
- [TGI 架构文档](https://huggingface.co/docs/text-generation-inference/) / [SGLang 架构文档](https://docs.sglang.ai/)（任一）

## AI SRE 现实图谱与风险治理（深入 11）
- BAIR · [《The Shift from Models to Compound AI Systems》](https://bair.berkeley.edu/blog/2024/02/18/compound-ai-systems/)
- Anthropic · [《A postmortem of three recent issues》](https://www.anthropic.com/engineering/a-postmortem-of-three-recent-issues)
- Anthropic · [《An update on recent Claude Code quality reports》](https://www.anthropic.com/engineering/april-23-postmortem)
- OWASP · [《Top 10 for LLM Applications 2025》](https://owasp.org/www-project-top-10-for-large-language-model-applications/)
- NIST · [《AI 600-1: Artificial Intelligence Risk Management Framework: Generative Artificial Intelligence Profile》](https://www.nist.gov/itl/ai-risk-management-framework)
- [Google SRE Book](https://sre.google/sre-book/table-of-contents/) · SLO、Postmortem、Cascading Failures 相关章节

## 三大主流模型系列（深入 12）
- [Anthropic / Claude Docs](https://docs.claude.com/en/docs/about-claude/models/overview) · Models、Prompt engineering、Extended thinking、Tool use、Prompt caching
- [OpenAI Platform Docs](https://platform.openai.com/docs) · Models、Responses API、Function calling、Structured outputs、Reasoning、Prompt caching
- [Google Gemini API Docs](https://ai.google.dev/gemini-api/docs/models) · Models、Text generation、Long context、Thinking、Function calling、Live API

## LLM API 协议与网关（深入 17）
- [Anthropic API Docs](https://docs.claude.com/en/api/messages) · Messages API、Tool use（how tool use works）、Streaming、MCP connector
- [OpenAI Platform Docs](https://platform.openai.com/docs/api-reference/responses) · Responses API reference、Migrate to the Responses API、Streaming responses、Function calling、Remote MCP、Chat Completions reference
- Model Context Protocol（MCP）· [官方规范](https://modelcontextprotocol.io/)

## 复合 AI 系统（Unit 4）
- Chip Huyen · [《Agents》](https://huyenchip.com/2025/01/07/agents.html)（2025）
- BAIR · [《The Shift from Models to Compound AI Systems》](https://bair.berkeley.edu/blog/2024/02/18/compound-ai-systems/)
- [DSPy 官方文档](https://dspy.ai/) · [DSPy 论文](https://arxiv.org/abs/2310.03714)

## 工程底座与数值级调试（Unit 5）
- PyTorch · [Numerical reproducibility docs](https://pytorch.org/docs/stable/notes/randomness.html)
- NVIDIA · [CUDA determinism / floating-point guide](https://docs.nvidia.com/cuda/floating-point/index.html)
- [Google SRE Book](https://sre.google/sre-book/table-of-contents/)（Chapter 4 SLO / Chapter 22 addressing cascading failures）

---

## 阅读原则（重要）

1. **一手优于二手**：能读官方文档 / 作者本人博客，不读别人的解读。
2. **保留独立尝试**：这些材料可用于 B3。允许术语、翻译和调试辅助，再对关键关系独立解释并核实，见[第 18 章](../练习/10-三个核心训练动作.md)。
3. **反复读**：同一篇重要文献（如 Anthropic 事故复盘）在不同单元会用不同视角读。每次读完和上次笔记对比。
4. **做笔记并检验**：记录自己的判断和证据。可以用 AI 辅助整理，但不能把它的总结或认可当成原文与理解的证明。


---

## 工作范式、学习与长任务验证（本轮补充）

以下材料于 2026-10-17 核对，研究或工程结果只支持各自范围，不表示已在本项目复现实验。

- Anthropic · [Effective harnesses for long-running agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents) · 跨会话进度与交接案例。
- Anthropic · [Harness design for long-running application development](https://www.anthropic.com/engineering/harness-design-long-running-apps) · 编排组件与评价器的任务化验证。
- Anthropic · [Scaling Managed Agents](https://www.anthropic.com/engineering/managed-agents) · 会话日志、harness 与执行环境的职责分离。
- Anthropic · [How AI assistance impacts the formation of coding skills](https://www.anthropic.com/research/AI-assistance-coding-skills) · Trio 入门任务的即时理解测验，不能外推为长期能力结论。
- METR · [Time-horizon 方法说明](https://metr.org/time-horizons/) · 人类任务难度与 AI 成功概率；该页已注明不再持续更新。
- METR · [Early-2026 AI usage survey](https://metr.org/blog/2026-05-11-ai-usage-survey/) · 自报告生产率的口径与限制，不能当成控制实验。
- Lù 等 · [AgentHorizon](https://arxiv.org/abs/2610.11050) · 2026-10-08 预印本，本轮只核对摘要；长轨迹 judge 的成对正反例设计。

---

[← 维护记录](../维护/2026-10-17-三层维护记录.md)  ·  [📖 目录](../README.md)
