---
title: 参考代码 · README
updated: 2026-07-02
tags: [code, reference, templates]
---

# 参考代码 · README

> [← 返回目录](../README.md)

> [!NOTE]
> 所有代码是**最小可运行参考实现**，优化了可读性而非性能。**Copy 过去改造用**，不是即插即用的库。

---

## 包含的文件

### 核心参考实现 + 教学指南

| 文件 | 作用 | 教学指南 | 多厂商对照 |
|---|---|---|---|
| [01-claude-caching.py](01-claude-caching.py) | Claude Prompt Caching | [📖 GUIDE](01-claude-caching-GUIDE.md) | [OpenAI](01-openai-caching.py) · [本地 vLLM](01-local-vllm-caching.py) |
| [02-minimal-agent.py](02-minimal-agent.py) | Tool use Agent（Claude）| [📖 GUIDE](02-minimal-agent-GUIDE.md) | [OpenAI](02-openai-agent.py) · [本地 Ollama/vLLM](02-local-agent.py) |
| [04-eval-skeleton.py](04-eval-skeleton.py) | Eval Pipeline 骨架 | [📖 GUIDE](04-eval-skeleton-GUIDE.md) | Vendor-neutral |

### 其他参考实现

| 文件 | 作用 |
|---|---|
| [03-local-rag.py](03-local-rag.py) | 本地 RAG（SQLite + sqlite-vec） |
| [05-llm-gateway.py](05-llm-gateway.py) | LLM Gateway（计账 + 限流） |
| [06-dedup-minhash.py](06-dedup-minhash.py) | MinHash 训练数据去重 |
| [07-canary-check.py](07-canary-check.py) | Canary 污染检测 |

---

## 使用原则

### ⚠️ 生产使用前必做

1. **加错误处理** — 这里为了简洁省略了大部分 try/except
2. **加速率限制** — 防止意外烧钱
3. **加日志** — structured logging + observability
4. **加 secret 管理** — 不要把 API key 写在代码里
5. **加 eval 覆盖** — 本书 [深入 06](../深入/06-Eval-Pipeline设计.md) 的东西

### ✅ 直接拿来用的部分

- Prompt caching 的 `cache_control` 用法
- Tool use 循环的结构
- SQLite + sqlite-vec 的 embedding 存储
- Eval 的三层结构

---

## 运行环境

```bash
# Python 3.10+
python -m venv venv
source venv/bin/activate

# 核心依赖
pip install anthropic openai sqlite-vec pydantic fastapi datasketch

# 设置 API key
export ANTHROPIC_API_KEY=your_key
export OPENAI_API_KEY=your_key  # 如果用 OpenAI embedding
```

---

## 代码 ↔ Unit / Week 对应

跟着练习走时，按"我现在在哪一周"找该 copy 哪个文件：

| Unit / Week | 推荐 copy 起步的代码 | 备注 |
|---|---|---|
| Unit 0 W1（API + tool use）| [`02-minimal-agent.py`](02-minimal-agent.py) | 含 tool result 净化层示例 |
| Unit 0 W2（本地 RAG）| [`03-local-rag.py`](03-local-rag.py) | SQLite + sqlite-vec |
| Unit 1（致命三角 / 红队）| [`02-minimal-agent.py`](02-minimal-agent.py) 改造 | 见 GUIDE 任务 4 |
| Unit 2 W1-W2（Trace-Eval）| [`04-eval-skeleton.py`](04-eval-skeleton.py) | 三层 eval 骨架 |
| Unit 3 W1-W4（推理 SLO / 网关）| [`05-llm-gateway.py`](05-llm-gateway.py) + [`01-claude-caching.py`](01-claude-caching.py) | 计账 + 限流 + caching |
| Unit 4（复合可靠性 / verifier）| [`04-eval-skeleton.py`](04-eval-skeleton.py) 扩展 | Verifier ≈ 实时 eval |
| Unit 5（数值底座）| 主要靠 [科学 03/04](../科学/) + Anthropic postmortem，代码侧 [`07-canary-check.py`](07-canary-check.py) 可参考 | — |

---

## 学习路径建议

按顺序做，每个理解后进下一个：

1. **01 · Caching** — 先理解 prompt caching 的 token 账
2. **02 · Minimal Agent** — 理解 tool use 的 API 循环
3. **03 · RAG** — 组合 embedding + 检索 + generation
4. **04 · Eval** — 给你的系统加质量保障
5. **05 · Gateway** — 当多产品共享一个 LLM 入口
6. **06 · Dedup** — 训练数据管线的 SRE 贡献点
7. **07 · Canary** — 防止 benchmark 污染

配合 [Unit 0 · API 上手](../练习/Unit0-AI大模型上手/总览.md) 一起用。

---

## 给读者的话

> [!IMPORTANT]
> 这些代码**不是答案**，是**起点**。
>
> 对照 Bloom 分级：代码**读懂 = 理解**，**改了改跑通 = 应用**，**写出自己场景的变体 = 综合**。
>
> 读完不动手的话，你还在"理解"层。

---

[📖 目录](../README.md)
