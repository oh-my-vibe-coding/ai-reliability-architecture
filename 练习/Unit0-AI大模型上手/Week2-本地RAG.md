---
title: Unit 0 · Week 2 · 本地 RAG
updated: 2026-07-02
tags: [part-4, practice, unit0, week]
---

# Unit 0 · Week 2 · 本地 RAG

> [← Unit 0 总览](总览.md)  ·  [← 返回目录](../../README.md)

## 本周目标
给上周的 CLI 加上检索能力：基于一批本地文档回答问题，**输出必须附来源**。

> [!TIP]
> **如果你走 [贯穿项目](../贯穿项目-SRE事故助手.md) 路线**：本周的交付物变成 `sre-incident-agent/app/ingest.py` + `app/retrieve.py` + `data/runbooks/`。**文档内容请用真实的 SRE 材料**（你自己的 runbook / postmortem 脱敏版，或 Google SRE Book 的案例），至少 20 条。Week 结束时应该能跑通 `data/eval/smoke.jsonl` 里的 5 个事故问题。

## 任务清单

### 准备（30 分钟）
- [ ] 选 5-10 份你熟悉的文档：runbook、技术笔记、内部文档都行
  - 不要用 markdown 之外的格式（pdf 会拖累第一次上手）
  - 文档总量 < 1 MB 即可
- [ ] 选向量库：**SQLite + sqlite-vec** 或 **FAISS**（二选一，本地跑）
  - **不要上 Pinecone / Weaviate / Milvus** —— 独立部署的服务是第一次上手的陷阱，多一个服务多一层黑盒；嵌入式方案（sqlite-vec / FAISS）才能看清楚每一步

### 核心编码（3-4 小时，可拆到两个晚上）
- [ ] 写切分逻辑：按段落或固定 token 数切（500-800 token/片较合理）
- [ ] 调 embedding API（OpenAI / Voyage / 本地 bge 都行），把每片转成向量存库
  - 注意 Anthropic 不提供 embedding API，官方推荐的是 Voyage——别去 Anthropic 文档里找 embedding 端点
- [ ] 写检索函数：查询 → embedding → 向量库 top-K 相似度搜索 → 返回片段 + 来源路径
- [ ] 改造上周的 CLI：
  - 用户提问先调检索工具（作为 tool use 的一个工具）
  - 把检索结果塞进 prompt
  - 要求模型回答时**必须附出处**（哪个文件的哪一段）

### 验证（20 分钟）
- [ ] 问一个"文档里明确写了的"问题——看它有没有引用正确来源
- [ ] 问一个"文档里没有的"问题——看它会不会编（大概率会，这是下一步要治的）
- [ ] 故意在某份文档里埋一个错误事实，看它会不会被误导

## 阅读 · B3 · 45 分钟（无 AI）
**Simon Willison · 《Embeddings: What they are and why they matter》**（simonwillison.net/2023/Oct/23/embeddings/）

读的时候拿笔记下三件事：
- 向量空间里"相似"到底是什么数学概念
- embedding 模型和对话模型是**不同的模型**，为什么
- 他提到的"chunking 很难"的具体例子

## 产出 · B2 · 45 分钟
不用 AI，为你的小 Agent 写一页**架构图 + 200 字失败模式分析**：

必须包含：
- Agent 的整体数据流（用户 → 检索 → 拼 prompt → 生成 → 回答）
- 至少列出 **3 种失败模式**（例：检索不到、检索错片段、模型忽略检索结果、模型在结果里编造……）
- 每种失败模式的可能对抗方式

写完贴给 AI："这份分析你觉得我漏掉了什么？挑出来，不要重写。"自己改。

## 预测 · B1 · 每日 5 分钟
每次查询之前先猜：
- **它会从哪份文档里检出来？**
- **前 3 个片段会不会包含答案？**
- **模型最终回答会不会忠实于检索结果？**

周末统计预测准确度。

## 周末自检
- [ ] CLI 能基于本地文档回答，并附来源
- [ ] 知道一次 query 走了几次 API 调用、花了多少 token
- [ ] 产出的架构图 + 失败模式分析完成
- [ ] 对"RAG 为什么解决幻觉但不能完全消除"有自己的直觉解释

**贯穿项目路线额外自检**：
- [ ] `data/runbooks/` 有 ≥20 条真实 SRE 文档（脱敏 OK）
- [ ] `data/eval/smoke.jsonl` 有 5 条事故问题 + 期望答案要点
- [ ] 跑 smoke eval 能**答对 ≥3 条**（带来源引用）
- [ ] `README.md` 更新到"Unit 0 完成：能查 runbook + 调 tool"

> **怎么"跑 smoke eval"**：Unit 0 阶段还没有 `app/eval.py`（那是 Unit 2 W1 才会建）。这里**手工跑**就够了：CLI 里逐条问 5 个问题，对照 `smoke.jsonl` 里的"期望答案要点"打 pass/fail（命中要点 + 引用正确 = pass）。把结果记在 commit message 或 `data/eval/smoke-results-W2.md` 里。Unit 2 W1 会把它自动化。

---

## 范例参考

> 关于"架构图 + 失败模式分析"的**填好范例**：

### Agent 数据流

```
用户: "数据库连接池满了怎么办"
  → CLI 收到查询
  → 调 embedding API 把查询转成向量
  → FAISS 向量库 top-3 相似搜索
  → 返回: [runbook-db-pool.md:§3, postmortem-2025-03.md:§7, runbook-connection.md:§2]
  → 拼进 prompt: system + 检索结果 + 用户问题
  → Claude 生成回答（附来源引用）
  → 返回给用户
```

### 至少 3 种失败模式

| 失败模式 | 示例 | 对抗方式 |
|---------|------|---------|
| **检索不到** | 用户问"K8s HPA 抖动"，但 runbook 里只写了"自动扩缩容"，词不匹配 | 加同义词映射；embedding 模型选领域匹配的（中文用 bge-m3） |
| **检索错片段** | 用户问"OOM 怎么办"，返回了"磁盘满怎么办"的 runbook（都提到了"内存"） | Rerank 环节；Top-K 不能太大（K ≤ 5 控制中间塌陷） |
| **模型忽略检索结果** | 检索返回了正确 runbook，但模型说"我无法确定，建议重启试试" | Prompt 强制要求引用来源；输出无引用时触发重试 |
| **模型在结果里编造** | 检索结果说"max_connections=100"，模型回答"建议设为 200" | System prompt: "只基于检索结果回答，不要添加检索结果中没有的建议" |

---

完成 Unit 0 后 → [Unit 1 · Agent 自治与致命三角](../Unit1-Agent自治与致命三角/总览.md)

上一步 → [Unit 0 · Week 1](Week1-API与工具调用.md)
