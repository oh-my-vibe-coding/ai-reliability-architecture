---
title: 深入 02 · Prompt Caching 原理：缓存是如何创建和命中的
updated: 2026-05-05
tags: [deep-dive]
---

# 深入 02 · Prompt Caching 原理：缓存是如何创建和命中的

> [← 返回目录](../README.md)  ·  对应知识章节：[第 5 章 · AI 推理服务的可靠性工程](../知识/05-AI推理服务的可靠性工程.md)  ·  前置：[深入 01 · 首包延迟与吞吐](01-首包延迟与吞吐的影响因素.md)

给 SRE 架构师用的工程级解析。**强烈建议先读[深入 01](01-首包延迟与吞吐的影响因素.md)** 再回来，否则很多机制讲不清楚。

---

## 0. 先理清：缓存的是什么？

很多人以为"prompt caching 缓存的是回答"——**错了**。Prompt caching 缓存的是 **KV cache**，也就是 Transformer 内部的中间状态。

为什么是 KV cache 而不是最终回答？因为——

> **LLM 的 prefill 阶段最大的成本不是计算，而是把同样的 prefix 反复算 K/V 张量。**

回忆一下 prefill（见[深入 01](01-首包延迟与吞吐的影响因素.md#0)）：输入 N 个 token，模型要对每层每头算出 K 张量和 V 张量，存起来供后续 decode 用。这些 K/V 张量对于**同样的输入 prefix 是完全确定的**——确定的输入 token 序列 → 确定的 K/V 张量。

所以只要**同一个 prefix 出现过一次**，把它的 K/V 张量存下来，下次再遇到相同 prefix 就跳过重算。这就是 prompt caching 的全部本质。

**关键特征**：

- 缓存的数据类型：per-layer、per-head 的 K 和 V 张量（位于 GPU HBM 或 host memory）
- 缓存的粒度：按 **token** 粒度，不是字符/字节
- 缓存的形式：和普通的 KV cache 一样的数据结构，只是生命周期被延长

---

## 1. 缓存命中的判定：Token 级前缀匹配

这里是最多人搞错的地方。**缓存命中不是字符串相等，而是 token 序列的前缀匹配**。

### 机制

1. 请求到达推理服务
2. 对 prompt 做 tokenization，得到 token 序列 `[t1, t2, t3, ... tN]`
3. 服务查找内部 cache 表，找到**最长匹配前缀**——从 `t1` 开始，看连续有多少 token 已经缓存过
4. 假设匹配到前 K 个 token，那么：
   - 前 K 个 token 跳过 prefill（直接用缓存的 K/V）
   - 从第 K+1 到第 N 个 token 做 prefill
   - 计算成本降低 ~K/N

### 几个关键点

**1. 必须是精确的 token-by-token 前缀**

- 在中间插入一个 token → 从那个位置往后全部缓存失效
- 修改 prefix 中的一个字符（如果改变了 tokenization）→ 整个缓存失效
- 因此：**不要在 prompt 的前面放会变化的内容**（比如时间戳、用户 ID、随机 session 信息）

**2. 后缀变化不影响前缀缓存**

- `[系统提示][文档 A][用户问题 1]` 和 `[系统提示][文档 A][用户问题 2]` 共享前两段缓存
- 这是 RAG 场景能大幅受益的原因：**固定文档放前面，变化查询放后面**

**3. Tokenization 的微妙影响**

- 有的模型 "hello world" 和 "hello world " （多空格）分词结果不同
- 中文和英文混排时分词可能不稳定
- 实际工程中：**一定要测**，不要假设"看起来一样"就是 token 序列一样

---

## 2. 缓存是如何创建的：工程流程

以 Anthropic Claude 的 prompt caching 为例（OpenAI / Google 机制类似但细节不同）：

### 2.1 显式标记（Anthropic 模式）

客户端发请求时用 `cache_control` 标记要缓存的段：

```json
{
  "model": "claude-opus-4-7",
  "system": [
    {
      "type": "text",
      "text": "你是一个 SRE 助手...（长系统提示）",
      "cache_control": {"type": "ephemeral"}
    }
  ],
  "messages": [
    {
      "role": "user",
      "content": [
        {
          "type": "text",
          "text": "参考文档：...（几万 token 的文档）",
          "cache_control": {"type": "ephemeral"}
        },
        {
          "type": "text",
          "text": "问题：这份文档里的 X 是什么意思？"
        }
      ]
    }
  ]
}
```

两个 `cache_control` 标记了两个 cache breakpoint。推理服务会：
1. 计算到第一个 breakpoint 的 KV cache → 写入缓存
2. 计算到第二个 breakpoint 的 KV cache → 写入缓存（追加，不覆盖）
3. 最后对 "问题：..." 做 prefill
4. Decode 生成回答

下次请求如果前两段完全一样，就直接命中这两段缓存，跳过前面的 prefill。

### 2.2 自动模式（OpenAI 模式）

OpenAI 的 Prompt Caching 不需要显式标记，**自动对长 prompt 做缓存**：

- 当 prompt ≥ 1024 token 时自动启用
- 按 128 token 粒度做前缀匹配
- 组织级共享缓存（同一 org 的不同请求可以共用）
- 无额外 API 调用开销

**权衡**：省事但不可控。不知道什么命中了，不知道什么失效了。

### 2.3 显式创建 + 按时间付费（Google Gemini 模式）

Gemini 的 Context Caching 更像"创建一个资源"：

- 客户端调用 API 显式创建 cached content，得到一个 ID
- 后续请求引用这个 ID
- 缓存按存储时间付费（不是按命中次数）
- 适合单次创建、大量引用的场景（如一本大书的 Q&A）

---

## 3. 三家 API 的缓存对比

| 维度 | Anthropic | OpenAI | Google Gemini |
|---|---|---|---|
| 触发方式 | 显式 `cache_control` | 自动（≥1024 token） | 显式创建 cached content |
| 最小缓存粒度 | 1024 token（Opus/Sonnet）/ 2048（Haiku） | 1024 token | 取决于模型，通常较大 |
| 写入成本 | ~1.25x 常规价格 | 无额外成本 | 按缓存大小 × 时长 |
| 读取成本 | ~0.1x 常规价格（折扣 90%） | ~0.5x（折扣 50%） | ~0.25x + 存储费 |
| TTL | 5 分钟（可延长到 1 小时 beta） | 5-10 分钟（off-peak 可达 1 小时） | 用户指定 |
| 共享范围 | 本 API key | 组织级 | 本项目 |
| 最大 breakpoint 数 | 4 | N/A（自动） | N/A |

### 成本回本点

Anthropic 的缓存**读取便宜但写入贵**：
- 写入：1.25x 常规（多付 25%）
- 读取：0.1x 常规（省 90%）

所以**重用 2 次就回本**。重用越多越划算。对高频复用场景（RAG 系统同一文档被反复查询），可以节省 80-90% 成本。

OpenAI 无写入成本但折扣小，适合"有多少用多少"的场景。

---

## 4. 缓存何时失效（Invalidation）

这是 SRE 最关心的部分——失效 = 成本/延迟突然翻倍。

### 4.1 TTL 过期

每个缓存有固定 TTL（通常 5 分钟）。**每次命中会刷新 TTL**（Anthropic 是这样；具体厂商查文档）。

**工程含义**：低频调用场景（每 10 分钟一次），**永远命中不了**，缓存成了纯浪费。
**对抗**：心跳请求维持缓存活性（但要算成本账）。

### 4.2 服务端路由变化

推理服务是分布式的，缓存**通常**只存在于具体某个 GPU 实例上（host memory 或 HBM）。如果请求被路由到**另一个实例**，即便 prompt 一样也会 miss。

这叫**缓存路由亲和**（sticky routing / session affinity）。

**工程含义**：
- 云 API 后端通常会尽量路由到同一实例，但不保证
- Traffic 突增或实例扩容时，缓存命中率会下降
- 自建推理服务时必须设计路由策略（按 session ID / 按 prompt hash）

### 4.3 Prefix 变更

前面已讲：前面插入/修改任何 token 都会让后续缓存失效。

**常见踩坑**：
- 系统提示里加了当前时间 → 每次都失效
- 系统提示里加了 `user_id` → 每个用户独享缓存（不是 bug，但要算成本）
- 版本号、A/B 标签放在系统提示开头 → 每次变更都失效

**工程规则**：
> **越靠前的内容变得越少，越靠后的内容可以随意变**。

### 4.4 实例重启 / OOM

推理服务重启（部署新版本、crash 恢复）会丢失所有缓存。扩缩容中新起的实例 cache 是空的，会有"预热期"。

### 4.5 模型版本切换

缓存是**模型绑定**的。切换到不同模型版本（或量化版本）后，所有缓存作废。灰度发布期间缓存命中率会下降。

---

## 5. 对 SRE 的工程含义

### 5.1 必须监控的指标

| 指标 | 说明 | 警戒 |
|---|---|---|
| Cache hit rate | 总命中率 | 低于预期值 20% 就该报警 |
| Cache hit prefix length | 平均命中多少 token | 突然变短 = 前缀设计可能坏了 |
| Cache write rate | 每秒写入缓存次数 | 突增可能是 prefix 在变 |
| Per-session cache hit rate | 单用户 / 单会话级别 | 某些 session 命中率异常低 → 有人加了变化 prefix |
| Cost savings | 按 token 折合的成本节省 | 业务层追踪 |

### 5.2 路由设计

自建推理服务时：
- **按 session 路由**：同会话请求到同实例，缓存最优
- **按 prompt prefix hash 路由**：共享前缀的请求到同实例
- 代价：负载均衡变差，可能导致热点

### 5.3 容量规划的影响

缓存**占显存**。一个 70B 模型的完整 KV cache（128k context）约 40GB。

> **缓存命中率和可服务并发数是此消彼长的**。

给缓存多留显存 → 命中率上升、成本下降，但并发容量下降。这是容量规划的新维度。

### 5.4 失效的静默性

缓存失效往往**无明显报警**：
- 请求还在正常成功
- 延迟变长（但不是 timeout）
- 成本变高（但财务数据有滞后）

所以必须**主动监控 cache hit rate**，不能等事故后才发现。

---

## 6. 实战：哪些场景最受益

### 高受益场景
- **RAG**：固定文档 + 变化查询，文档放前面
- **长系统提示的对话产品**：Few-shot 示例、人设定义这些放前面
- **代码助手**：仓库上下文放前面
- **多轮对话**：前几轮对话可以被缓存（每次缓存断点推进）

### 不太受益的场景
- 一次性短 prompt
- 每次前面都在变的场景（时间、随机值）
- 调用频率很低（< TTL 一次）的场景

---

## 7. 常见陷阱（Checklist）

- [ ] 不要在 prompt 最前面放时间戳 / UUID / 随机值
- [ ] 不要每次改版本号放在系统提示开头
- [ ] 用户 ID / session ID 如果没必要就不要放前面
- [ ] 要监控实际命中率，不要假设设了 `cache_control` 就一定命中
- [ ] 模型灰度发布时预期到缓存失效的成本冲击
- [ ] 自建服务时设计路由亲和，否则缓存机制失效
- [ ] 不要以为缓存的是回答 —— 温度 > 0 时同 prompt 回答不同，缓存的是 KV 张量
- [ ] 不要忘了写入比读取贵 —— 冷门 prompt 不要标记缓存

---

## 8. 参考资料

- Anthropic · Prompt Caching 官方文档（含 cache_control 语义、定价、TTL 规则）
- OpenAI · Prompt Caching 文档（自动缓存机制）
- Google · Context Caching with Gemini 文档
- vLLM · Prefix Caching 设计文档（开源推理服务的实现参考）
- SGLang · RadixAttention 论文 / 文档（最早实现基于 radix tree 的 prefix cache）
- 《Efficient Memory Management for Large Language Model Serving with PagedAttention》（vLLM 论文）

---

上一篇 → [深入 01 · 首包延迟与吞吐的影响因素](01-首包延迟与吞吐的影响因素.md)
