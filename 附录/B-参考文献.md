---
title: 附录 B · 一手材料与参考文献
updated: 2026-05-10
tags: [appendix]
---

# 附录 B · 一手材料与参考文献

> [← 返回目录](../README.md)

本附录只列**一手材料和公认经典**。列在这里的东西，要么是你 Track A 某个单元会读的，要么是值得反复回看的。

---

## AI 大模型与 Agent 开发（Unit 0）
- Anthropic API 官方文档 · messages / tool use / streaming 三章
- Anthropic · 《Building effective agents》（2024）
- Simon Willison · 《Embeddings: What they are and why they matter》

## Agent 架构与安全（Unit 1）
- Simon Willison · 《The lethal trifecta for AI agents》及 prompt-injection tag 系列
- Simon Willison · 《Designing Agentic Loops》（2025）
- Anthropic · Agent 架构相关官方文章
- OpenAI · Function calling safety best practices

## 质量可观测性与 Evals（Unit 2）
- Hamel Husain · 《Your AI Product Needs Evals》（hamel.dev/blog/posts/evals/）
- Eugene Yan · LLM evaluation 系列（eugeneyan.com）
- Langfuse 官方架构文档
- LangSmith 官方架构文档
- Honeycomb · LLM observability 相关博客

## AI 系统可靠性与事故复盘（Unit 3）
- Anthropic · Postmortem of three recent issues（**重要，至少读三次**）
- Anthropic · Effective Context Engineering for AI Agents
- vLLM 官方文档
- TGI / SGLang 架构文档（任一）

## AI SRE 现实图谱与风险治理（深入 11）
- BAIR · 《The Shift from Models to Compound AI Systems》
- Anthropic · 《A postmortem of three recent issues》
- Anthropic · 《An update on recent Claude Code quality reports》
- OWASP · 《Top 10 for LLM Applications 2025》
- NIST · 《AI 600-1: Artificial Intelligence Risk Management Framework: Generative Artificial Intelligence Profile》
- Google SRE Book · SLO、Postmortem、Cascading Failures 相关章节

## 三大主流模型系列（深入 12）
- Anthropic / Claude Docs · Models、Prompt engineering、Extended thinking、Tool use、Prompt caching
- OpenAI Platform Docs · Models、Responses API、Function calling、Structured outputs、Reasoning、Prompt caching
- Google Gemini API Docs · Models、Text generation、Long context、Thinking、Function calling、Live API

## 复合 AI 系统（Unit 4）
- Chip Huyen · 《Agents》（huyenchip.com, 2025）
- BAIR · 《The Shift from Models to Compound AI Systems》（bair.berkeley.edu）
- DSPy 论文与官方文档

## 工程底座与数值级调试（Unit 5）
- PyTorch · Numerical reproducibility docs
- NVIDIA · CUDA determinism guide
- Google SRE Book（Chapter 4 SLO / Chapter 22 addressing cascading failures）

---

## 阅读原则（重要）

1. **一手优于二手**：能读官方文档 / 作者本人博客，不读别人的解读。
2. **无 AI 阅读**：这些材料是 B3 阅读块的主要对象。
3. **反复读**：同一篇重要文献（如 Anthropic 事故复盘）在不同单元会用不同视角读。每次读完和上次笔记对比。
4. **做笔记**：手写或纯文本，**不要让 AI 帮你总结**——总结是你自己的事。
