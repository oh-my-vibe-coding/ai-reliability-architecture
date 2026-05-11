---
title: 代码 01 · Claude Prompt Caching · 教学指南
updated: 2026-05-05
tags: [code, guide, prompt-caching]
---

# 代码 01 · Claude Prompt Caching · 教学指南

> [← 代码索引](README.md)  ·  主代码：[01-claude-caching.py](01-claude-caching.py)  ·  关联章节：[深入 02](../深入/02-Prompt-Caching原理.md)、[深入 04](../深入/04-为什么简单你好也消耗数万token.md)

> [!WARNING]
> 本文包含**价格、模型名、厂商能力**等快变信息。内容**快照日期为 2026-05-05**；实际选型或上线前，请以厂商官方 pricing 和当前生产验证为准。
>
> 官方 pricing 入口：
> - Anthropic: https://www.anthropic.com/pricing
> - OpenAI: https://openai.com/api/pricing
>
> 本文档的定价用来理解**相对比例**和**数量级**，不是精确账单。

---

## 1. 运行前提

### 环境

- Python 3.10+
- Anthropic API key（可以 claude.com/apps 申请试用）
- 网络能访问 api.anthropic.com

### 安装

```bash
python -m venv venv
source venv/bin/activate
pip install 'anthropic>=0.40'
export ANTHROPIC_API_KEY=sk-ant-...
```

### 一次性成本预估

- 跑两次 demo ≈ 消耗 20k 输入 token + 1k 输出 token
- Sonnet 4.6 定价下约 **$0.08**
- 第二次**缓存命中**大部分，成本 < $0.01

---

## 2. 预期输出

第一次运行（缓存写入）：

```
=== 第一次调用（写入缓存）===
Input tokens (未缓存): 15
Cache creation tokens (写入): 12483
Cache read tokens (命中): 0
Output tokens: 287
Cache hit rate: 0.0%
```

第二次运行（命中缓存）：

```
=== 第二次调用（应该命中缓存）===
Input tokens (未缓存): 23
Cache creation tokens (写入): 0
Cache read tokens (命中): 12483
Output tokens: 254
Cache hit rate: 99.8%
```

**关键观察**：
- 第一次 `cache_creation` 大，`cache_read=0`
- 第二次 `cache_creation=0`，`cache_read` 大
- `input_tokens`（未缓存部分）只是当次用户消息的几个 token
- Cache hit rate 从 0 跳到 99%+

**如果你看到的不是这样**：
- 第二次仍然 `cache_creation` 高 → 看[常见报错 B](#b--缓存未命中)

---

## 3. 常见报错

### A · 401 Authentication Error

```
anthropic.AuthenticationError: Error code: 401
```

- ✅ 确认 `ANTHROPIC_API_KEY` 环境变量设了：`echo $ANTHROPIC_API_KEY`
- ✅ Key 是否有效（去 console.anthropic.com 查）
- ✅ 账号是否有余额（试用额度耗尽也会 401）

### B · 缓存未命中

**症状**：第二次调用 `cache_read_input_tokens=0`，`cache_creation` 仍高。

**排查**：
1. **两次间隔 > 5 分钟**？Anthropic cache TTL 默认 5 分钟
   - 解决：缩短间隔，或开启 1h extended cache（beta）
2. **SYSTEM_PROMPT 或 LARGE_CONTEXT 变了**？改任何字符都会失效
   - 解决：确认完全相同（可以 `hash(text)` 对比）
3. **内容 < 1024 token**？Sonnet/Opus 的最小 cache size
   - 解决：加长系统提示到 ≥ 1024 token
4. **路由到了不同后端实例**？
   - Anthropic 云端通常会路由亲和，但不保证

### C · `TypeError: Argument of type 'NoneType' is not iterable`

一般是 response 解析时假设了结构。检查：

```python
response.content[0].text  # 可能 content 是空列表
```

加防御：

```python
if response.content and response.content[0].type == "text":
    return response.content[0].text
return ""
```

### D · RateLimitError

```
anthropic.RateLimitError: Error code: 429
```

试用 API key 有较低速率限制。解决：
- 加指数退避重试
- 用付费 API key
- 改用 Bedrock / Vertex（额度独立）

---

## 4. 改造任务（递进难度）

### 任务 1 · 多个缓存断点（简单）

当前代码只有 2 个 `cache_control`。扩展到 4 个（Anthropic 最大支持）：

```python
messages=[{
    "role": "user",
    "content": [
        {"type": "text", "text": FIXED_DOC_1, "cache_control": {"type": "ephemeral"}},
        {"type": "text", "text": FIXED_DOC_2, "cache_control": {"type": "ephemeral"}},
        {"type": "text", "text": RECENT_HISTORY, "cache_control": {"type": "ephemeral"}},
        {"type": "text", "text": question},
    ],
}]
```

**思考**：多个断点的顺序 matter 吗？为什么？

### 任务 2 · 跟踪成本 ROI（中等）

给代码加上实时成本计算：

- 用 [深入 02 · §3 的定价表](../深入/02-Prompt-Caching原理.md)
- 每次调用后打印：**"本次节省 $X"** vs 如果没用 caching

### 任务 3 · Cache-miss 监控（中等）

设计一个监控：

- Cache hit rate 连续 10 次 < 30% → 打印警告
- 什么情况会触发？（灰度切版本、prompt 模板变化等）

### 任务 4 · 跨 session 共享 Cache（较难）

Anthropic cache 以 API key 为界。写一个多用户场景，比较：
- 每个用户独立 session（cache 不共享）
- 共享 prefix（cache 共享）

从 token 账单上计算规模化差异。

### 任务 5 · 迁移到 1h TTL（较难）

当前默认 5 min TTL。Anthropic 有 beta 的 1h extended cache：

- 查文档：https://platform.claude.com/docs/en/docs/build-with-claude/prompt-caching
- 加 `cache_control: {"type": "ephemeral", "ttl": "1h"}`
- 对比 5 min vs 1h 的**成本 / TTL trade-off**

---

## 5. 读者作业（自检答案见下）

### 作业 1
Claude 的 prompt caching **写入成本 vs 读取成本** 的比例是多少？什么时候**划算**开 caching？

<details><summary>参考答案</summary>

- 写入：~1.25x 常规价格（多付 25%）
- 读取：~0.1x（省 90%）
- **重用 2 次就回本**。第 3 次以后每次省 90%。

所以只要该 prefix **会被复用 ≥ 2 次**，就该开 caching。

</details>

### 作业 2
你的 system prompt 里加了当前时间（`"当前时间：2026-05-05 14:30:00"`），会发生什么？

<details><summary>参考答案</summary>

时间戳每分钟变，导致 token 序列变，**缓存每次都 miss**。你实际在**付写入成本而没有读取收益**——比不用 caching 更贵 25%。

修复：把时间戳放 prompt **末尾**或移除；或让 LLM 通过 tool call 查时间。

</details>

### 作业 3
Cache hit rate 从 95% 掉到 30%，你会怎么排查？列出至少 4 步。

<details><summary>参考答案</summary>

1. **是否有部署**？最近 prompt template、system prompt、工具定义有没有变
2. **Cache TTL 是否到期**？低频调用（< 5 min 一次）永远 miss
3. **服务端路由**？可能被路由到新实例（常见于自动扩容时）
4. **模型版本切换**？缓存绑定模型版本
5. **Tokenizer 变化**？Anthropic 近期换过 tokenizer（见科学 04）

</details>

### 作业 4
你要为一个 **RAG 系统**（固定 50k token 文档 + 变化用户 query）设计缓存。怎么组织 prompt 最大化命中？

<details><summary>参考答案</summary>

顺序：`[system] [文档 1..N 固定段] [CACHE BREAKPOINT] [用户 query]`

- 文档放前面，query 放后面
- `cache_control` 放在文档的最后一段
- 用户 query 每次变，但只占几十 token，其他部分命中

假设 100 个用户都在查这些文档，只第一人付写入成本，后续全部 0.1x。

</details>

---

## 6. 生产化清单

这份代码是**学习起点**。上生产前要加：

- [ ] 错误处理（try/except 所有 API 调用）
- [ ] 速率限制 + 指数退避
- [ ] Structured logging（trace_id / user_id / cache_stats）
- [ ] Metrics 导出到 Prometheus（cache_hit_rate / cost_per_request）
- [ ] 密钥管理（Vault / AWS Secrets Manager，不要 env）
- [ ] 监控告警（cache hit rate < 阈值）
- [ ] 成本预算上限（单用户 / 单 org / 单天）

这些都是 [深入 10 · Pattern 2 Cache Miss Storm](../深入/10-AI系统事故模式库.md#pattern-2--cache-miss-storm) 的预防。

---

## 7. 多厂商对照

- **OpenAI 版本**（自动 caching，无需显式标记）：[01-openai-caching.py](01-openai-caching.py)
- **本地 vLLM 版本**（Automatic Prefix Caching）：[01-local-vllm-caching.py](01-local-vllm-caching.py)

三种机制的对比见 [深入 02 · §3](../深入/02-Prompt-Caching原理.md)。

---

[← 代码索引](README.md)  ·  [📖 目录](../README.md)
