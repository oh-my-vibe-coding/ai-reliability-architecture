---
title: 附录 C · 术语表
updated: 2026-05-10
tags: [appendix]
---

# 附录 C · 术语表

> [← 返回目录](../README.md)

## 大模型基础

| 术语 | 含义 |
|---|---|
| Token | 模型的最小处理单位，中文 1-2 字/token，英文约 0.75 词/token |
| Context Window | 一次对话能容纳的最大 token 数 |
| System Prompt | 贯穿整个对话的指令 / 规则 |
| Temperature / top-p | 控制输出随机性的采样参数 |
| Tool Use / Function Calling | LLM 返回结构化"工具调用"请求，由宿主代码执行并回灌结果 |
| Streaming | Token 逐个返回的输出模式 |
| Claude Opus / Sonnet / Haiku | Anthropic Claude 系列的常见分层：Opus 偏最强，Sonnet 偏平衡主力，Haiku 偏轻量快速 |
| GPT flagship / mini / nano / reasoning | OpenAI GPT 系列的常见分层：旗舰做复杂任务，mini/nano 做低成本高频任务，reasoning 档用于复杂推理 |
| Gemini Pro / Flash / Flash-Lite | Google Gemini 系列的常见分层：Pro 偏复杂和长上下文，Flash 偏速度成本平衡，Flash-Lite 偏轻量高吞吐 |
| Reasoning / Thinking Budget | 推理时让模型"多想一会"的预算控制，通常会增加延迟和 token 成本 |

## 检索与记忆

| 术语 | 含义 |
|---|---|
| Embedding | 把文本映射为向量，用向量距离衡量语义相似度 |
| RAG | Retrieval-Augmented Generation，检索后生成 |
| Context Engineering | 将上下文窗口当作有限资源进行设计的学科 |

## 可靠性与可观测性

| 术语 | 含义 |
|---|---|
| TTFT | Time To First Token，推理服务延迟的关键 SLI |
| Silent Degradation | 指标全绿但系统已经数学错误的静默故障 |
| Judge Model | 用模型评估另一个模型输出质量的评估方法 |
| Data Flywheel | 生产 trace → 标注 → eval → 改进 → rollout 的反馈回路 |
| Assertion Battery | 任务专属的硬规则校验集（替代"全局幻觉率"这类不可操作指标） |

## 自治与安全

| 术语 | 含义 |
|---|---|
| Lethal Trifecta | 不受信输入 + 工具访问 + 外泄通道三者共存的危险组合 |
| Capability-scoped Credentials | 权限按操作范围细分、最小化的凭证 |
| Blast Radius | 一个操作失败时可能影响的范围 |
| Reversibility | 操作可回滚的程度，自治分级的核心判据 |

## 架构

| 术语 | 含义 |
|---|---|
| Compound AI System | 由多步推理、工具调用、检索组成的复合系统 |
| Step Budget | 一条 Agent 链路允许的最大推理步数 |
| Verifier / Gate | 在链路中插入的校验节点，用于截断错误累积 |
