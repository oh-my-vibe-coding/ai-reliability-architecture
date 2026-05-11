---
title: Unit 0 · Week 1 · API 调用与工具使用
updated: 2026-05-05
tags: [part-3, practice, unit0, week]
---

# Unit 0 · Week 1 · API 调用与工具使用

> [← Unit 0 总览](总览.md)  ·  [← 返回目录](../../README.md)

## 本周目标
用 API 搭出一个最小 CLI：能流式回答、能调用 2-3 个本地函数。

> [!TIP]
> **如果你走 [贯穿项目](../贯穿项目-SRE事故助手.md) 路线**：本周的交付物**直接变成 `sre-incident-agent/app/agent.py` + `app/tools.py` 的雏形**。工具选只读 SRE 场景的（见下方任务清单）。本周不需要完美，Week 2 会加 RAG。

## 任务清单

### 准备（30 分钟）
- [ ] 申请 API key（Anthropic 或 OpenAI 任一）
- [ ] 准备 Python 环境，装 SDK（`pip install anthropic` 或 `pip install openai`）
- [ ] 设置环境变量，确认能调通一次最简单的请求

### 核心编码（2-3 小时，可拆到两个晚上）
- [ ] 写一个 CLI 程序：读用户输入 → 调用 API → **流式打印**回答
- [ ] 加 system prompt（一句话"你是一个 SRE 助手"）
- [ ] 调整 temperature（试 0 / 0.3 / 1.0），观察输出差异
- [ ] 实现 tool use：
  - `run_shell(cmd)` —— 白名单 2-3 个命令（`uptime`, `df -h`, `ls`），禁止其他
  - `read_file(path)` —— 只读，限制在某目录
- [ ] 让模型能自主决定何时调用工具，回灌结果后继续生成

### 验证（15 分钟）
- [ ] 问它："当前主机磁盘用得满吗？"——观察它是否调用 `df -h`
- [ ] 问它："读一下 /etc/hosts 告诉我有什么异常"——观察它是否调用 `read_file`
- [ ] 观察它对你"没给工具权限"的请求的行为

## 阅读 · B3 · 45 分钟（无 AI）
**Anthropic API 文档 · Tool use 章节**（anthropic.com/docs → Tool use）

不开 AI、不要让 AI 帮你读。自己一字一句过一遍，特别注意：
- `tool_use` 和 `tool_result` 两种消息类型的结构
- 模型"请求调用工具"和"收到结果后继续"是**两次独立的 API 调用**
- `tool_choice` 参数的三种模式（auto / any / tool）

## 产出 · B2 · 30 分钟
不用 AI，写下你对两个问题的回答：
1. Tool use 流程里，**谁决定调不调用工具？谁决定用什么参数？谁决定执行？**
2. 如果 AI 被诱导调用了错误参数（比如 `run_shell("rm -rf /")`），责任链条在哪一步断的？

写完贴给 AI 说："挑我这份分析的漏洞。"自己改。

## 预测 · B1 · 每日 5 分钟
本周每次触发 tool use 之前，先猜：
- **会不会调用工具？**
- **调哪个？**
- **参数是什么？**

猜对/猜错都记一笔。周末统计：猜错率 > 50% 说明你对这个模型的"直觉"还没建立——正常，继续练。

## 周末自检（5 分钟）
- [ ] CLI 能跑，能流式输出
- [ ] 至少 2 个工具接入，模型能自主选择调用
- [ ] 读完了 tool use 官方文档并能自己画出两次 API 调用的流程
- [ ] 预测记录本周"没想到"次数：____ 次

**贯穿项目路线额外自检**：
- [ ] 代码落到 `sre-incident-agent/app/` 目录下
- [ ] `README.md` 里有"当前状态"节，写清楚"Unit 0 W1：有 tool use 但还没 RAG"
- [ ] 至少 2 个工具是 SRE 场景相关的（不是通用 demo 工具）

---

下一步 → [Unit 0 · Week 2 · 本地 RAG](Week2-本地RAG.md)
