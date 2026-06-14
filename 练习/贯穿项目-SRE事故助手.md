---
title: 第 19 章 · 贯穿项目：SRE 事故助手
updated: 2026-06-07
tags: [part-4, practice, capstone-project, rag, agent, sre-incident-assistant]
---

# 第 19 章 · 贯穿项目：SRE 事故助手

> [← 返回目录](../README.md)  ·  [← 周循环总览](周循环总览.md)  ·  [→ Capstone · 架构评审包](Capstone-AI生产架构评审包.md)

> [!IMPORTANT]
> 本项目是**陪跑你 19 周学习**的真实工程项目。每个 Unit 都在它上面加一层能力，Capstone 直接以它为评审对象。
>
> 它的价值不在"跑起来"，在于让你**把 Unit 0-5 学的每一样东西落到一个真实系统上**——这正是 SRE 转 AI SRE 的核心训练路径。

---

## 为什么要有贯穿项目

- **只读书和写练习文档还不够**。读懂 ≠ 做过；做过一次 ≠ 做成过一个系统。
- **贯穿项目把 Unit 0-5 串成真实工程经验**：每个 Unit 的练习不是孤立的"作业"，而是**系统的一次增量**。
- **对 SRE 转 AI SRE，RAG + Tool-use Agent 比"调参小模型"更接近主战场**：你日常会运维别人训的模型、做架构决策、管 token 成本、设计权限边界，几乎不会自己去预训练一个新模型。
- **调参 / LoRA 微调是支线，不是主线**——见[支线](#可选支线--日志分类小模型--lora-微调)。

---

## 项目目标

构建一个面向 SRE 场景的 AI 助手——**SRE 事故助手**。

### 它能做什么
- 接收**事故描述 / 日志片段 / metrics 摘要**作为输入
- 检索 **runbook / postmortem / 内部 SRE 知识库**
- 生成**结构化的排查建议**（带来源引用）
- 调用**只读工具**（查日志、查 metrics、查服务依赖、查历史事故）
- 记录**trace**（每次交互可追溯）
- 跑**eval**（三层）
- 监控 **TTFT / tokens/s / cache hit rate / 成本**
- 做**权限边界、prompt injection 防御、灰度回滚、事故模式映射**

### 它不做什么
- **不自动执行生产变更**（只读，人类拍板）
- **不替代 on-call**（只做建议）
- **不是聊天机器人**（回答结构化、可审计）

---

## 最小技术形态

**建议但不强绑定技术栈**，读者按自己熟悉的工具选：

| 组件 | 推荐（任选一个）| 替代 |
|---|---|---|
| 应用框架 | Python + FastAPI | CLI / Flask / Starlette |
| LLM API | Anthropic / OpenAI | 本地 vLLM / Ollama（路线 C 用）|
| 向量库 | SQLite + sqlite-vec | Chroma / LanceDB / pgvector |
| Embedding | OpenAI text-embedding-3-small | bge-m3（本地）/ Cohere Embed |
| Trace 存储 | 自建 JSONL | Langfuse / Phoenix / LangSmith |
| Metrics | Prometheus | 简单 metrics 文件（起步够用） |
| 权限配置 | YAML / JSON 文件 | OPA（成熟后）|

> [!TIP]
> **不要在选型上纠结**。起步选**最小组合**（FastAPI + SQLite + Anthropic），跑起来再考虑替换。选型本身不是学习目标。

---

## 项目演化地图

| Unit | 周 | 新增能力 | 交付物（累积）|
|---|---|---|---|
| **Unit 0** | W1-W2 | 最小 API + RAG + tool use | 能跑的 CLI；20+ 文档 ingested |
| **Unit 1** | W1-W4 | 权限、致命三角、红队 | 工具白名单；injection 测试报告 |
| **Unit 2** | W1-W4 | Trace-Eval 一体化、三层 eval | trace schema；eval pipeline；失败回流 |
| **Unit 3** | W1-W4 | SLO、容量、缓存、成本、灰度 | SLI 面板；决策树；灰度配置 |
| **Unit 4** | W1-W3 | Step 预算、verifier | step 图；端到端正确率对比 |
| **Unit 5** | W1-W2 | 数值级 runbook（+ 可选本地/量化） | 数值 runbook；本地部署验证（可选） |
| **Capstone** | +1w | 架构评审包 | 14 节完整评审文档 |

**核心设计**：每个 Unit 的**Week B2 产出**尽量落到项目里——不是"写一份独立 markdown"，而是**在项目里新增代码 / 文档 / 配置**。

---

## 每个 Unit 的项目产出

### Unit 0 · 启动最小系统（~2 周）

**新增**：
- `app/ingest.py` — 读取 runbook/postmortem 文件，切 chunk，写入向量库
- `app/retrieve.py` — 查询向量库的 top-k 片段
- `app/agent.py` — 含 tool use 循环的最小 agent
- `app/tools.py` — 最初 1-2 个只读工具（grep_logs、read_runbook）
- `data/runbooks/` — **≥20 条**你熟悉的 runbook / postmortem（可脱敏）
- `data/eval/smoke.jsonl` — 5 个事故问题 + 预期答案要点
- `README.md` — 如何 ingest、如何 query、如何测 eval 的基本命令

**验收**：
- [ ] 能回答 **5 个事故问题**（来源：data/eval/smoke.jsonl），答对 ≥ 3 条
- [ ] 每个回答附**来源引用**（哪个 runbook 的哪段）
- [ ] CLI 可以一键 ingest + query

### Unit 1 · 权限与安全（~4 周）

**新增**：
- `app/permissions.yaml` — 工具权限矩阵（tool × 用户类型 × auto/confirm/forbid）
- `docs/threat-model.md` — Lethal Trifecta 分析文档
- `tests/injection/` — **≥3 个** prompt injection payload 测试样本
- `app/tools.py` 扩展：**严格白名单**（只读命令 + path 限制）

**验收**：
- [ ] 工具白名单：未授权命令返回 `ERROR: not allowed`
- [ ] Trifecta 分析覆盖**全部输入面**（prompt / 日志内容 / 工具返回）
- [ ] 3 个 payload 里**至少 1 个**被基础设施层挡住（不是靠 LLM）
- [ ] 写一份红队报告：每个 payload 的攻击路径 + 当前防御 + 缺口

### Unit 2 · Trace + Eval + Flywheel（~4 周）

**新增**：
- `app/trace.py` — Trace schema（请求、prompt、response、tool calls、usage、判决）
- `traces/` — trace 持久化（JSONL 起步）
- `data/eval/gold.jsonl` — gold set（**≥30 条**，含预期关键点）
- `app/eval.py` — L1 assertion + L2 judge（judge 最好用不同家模型）
- `app/failure_queue.py` — 失败样本入队列供人工 relabel

**验收**：
- [ ] 每次请求都有完整 trace 落盘
- [ ] `eval.py` 能跑 gold set 输出报告
- [ ] Judge 和人工对 10-20 条做过**对齐度计算**（记录 Cohen's κ 或 agreement rate）
- [ ] 失败样本自动入 queue，并有手工 review 流程

### Unit 3 · 可靠性工程（~4 周）

**新增**：
- `docs/slo.md` — SLI 清单 + 目标值 + error budget policy
- `app/gateway.py` — 基础 LLM 网关（带 token 计账、cache hit、rate limit）
- `app/metrics.py` — TTFT / tokens/s / cost / cache hit rate 指标导出
- `docs/rollout-decision-tree.md` — 灰度 / 回滚 / shadow 决策树
- 简单 Prometheus scrape endpoint 或 metrics JSON 文件

**验收**：
- [ ] SLO 文档里每个 SLI 有**目标值 + 测量点**
- [ ] Gateway 能跑，能看到 cache hit rate
- [ ] 决策树每个分支有**阈值**（不是"看情况"）
- [ ] 跑一次成本对比（开 vs 关 caching）

### Unit 4 · 复合可靠性数学（~3 周）

**新增**：
- `docs/step-budget.md` — Agent 的 step 图 + 每步 p_i 估算 + 端到端正确率
- `app/agent.py` 改造：加入 **verifier / gate**（至少 2 处）
- `data/eval/gold.jsonl` 扩展：加一组测试"加 gate 前后的对比"
- `docs/failure-amplification.md` — 2 种级联失效场景分析

**验收**：
- [ ] Step 图 + p_i 表格有**具体数字**（不是全 0.95）
- [ ] 端到端正确率**前后对比**：加 verifier 提升多少、代价多少
- [ ] Verifier 的 false positive rate 测过（别把对的误杀）

### Unit 5 · 数值底座 + 本地部署（可选）（~2 周）

**新增**：
- `docs/runbook-numeric.md` — 数值级故障排查 runbook
- 可选（路线 A/B）：`app/agent.py` 支持切换到 **本地小模型**（Qwen3-1.5B / Phi-3-mini），对比质量 / 成本
- 可选（路线 C）：toy softmax + bf16/fp32 对比实验，写进 runbook 的"可复现实验"节

**验收**：
- [ ] Runbook 有**触发条件 + 分层诊断 + 具体命令**
- [ ] 至少做过 1 次实验（toy 或 frontier 规模）
- [ ] 如果做了本地部署，记录**和云 API 的质量差距**

### Capstone · 架构评审包（~1 周）

**不再新增代码**——直接把现有项目**沉淀为[架构评审文档](Capstone-AI生产架构评审包.md)**：

- 14 节评审包的所有内容**都已经在项目里**（docs/ + 代码 + 测试）
- Capstone 的工作是"**写成一份可评审的 markdown**"
- 团队 review → 吸收 action items → 进入**维护期**

**至此你有**：
- 一个跑得动的系统
- 完整的架构评审文档
- 一套可复用的 runbook / SLO / 事故模式

这是**真正的"AI SRE 实战经验"**，不是"读过这本书"。

---

## 项目目录建议

**不强制照抄**。这是一个起点，**按需调整**。

```
sre-incident-agent/
├── README.md                 # 如何运行、当前状态
├── pyproject.toml            # 依赖
├── .env.example              # 环境变量样例
├── data/
│   ├── runbooks/             # 你的 runbook / postmortem
│   ├── postmortems/
│   └── eval/
│       ├── smoke.jsonl       # Unit 0 · 5 条冒烟
│       └── gold.jsonl        # Unit 2+ · gold set
├── app/
│   ├── ingest.py             # Unit 0
│   ├── retrieve.py           # Unit 0
│   ├── agent.py              # Unit 0 / 1 / 4
│   ├── tools.py              # Unit 0 / 1
│   ├── permissions.yaml      # Unit 1
│   ├── trace.py              # Unit 2
│   ├── eval.py               # Unit 2
│   ├── failure_queue.py      # Unit 2
│   ├── gateway.py            # Unit 3
│   └── metrics.py            # Unit 3
├── traces/                   # Unit 2+ · 可被 eval 回放
├── tests/
│   └── injection/            # Unit 1 · 红队 payload
└── docs/
    ├── architecture-review.md    # Capstone
    ├── slo.md                    # Unit 3
    ├── threat-model.md           # Unit 1
    ├── runbook-numeric.md        # Unit 5
    ├── step-budget.md            # Unit 4
    ├── rollout-decision-tree.md  # Unit 3
    └── failure-amplification.md  # Unit 4
```

> [!TIP]
> 每个 Unit 结束时，`README.md` 应该有一个**"当前状态"** 节：跑到哪个 Unit、目前能做什么、已知缺什么。这会成为 Capstone 的天然雏形。

### 5 分钟起步命令清单

复制粘贴即可，零摩擦启动：

```bash
mkdir sre-incident-agent && cd sre-incident-agent
python -m venv .venv && source .venv/bin/activate
pip install anthropic openai sqlite-vec pydantic
echo "ANTHROPIC_API_KEY=..." > .env  # 填上你的 key
git init && echo ".venv/\n.env\n__pycache__/" > .gitignore
mkdir -p app data/runbooks data/eval traces tests/injection docs
cp ../AI时代SRE架构师之路/代码/02-minimal-agent.py app/agent.py  # 起步
```

> 然后打开 [Unit 0 · Week 1](Unit0-AI大模型上手/Week1-API与工具调用.md) 开干。第一次能跑通的目标：让 `app/agent.py` 回答"这台机器磁盘满了吗"。

---

## Mastery Gate

贯穿项目的**最终达标标准**（和 [Capstone Mastery Gate](Capstone-AI生产架构评审包.md#mastery-gate) 互补）：

- [ ] **能跑**：一条命令能 ingest，一条命令能 query
- [ ] **有 trace**：每次交互都能被事后回放
- [ ] **有 eval**：gold set ≥30 条，能跑出 L1/L2 分数
- [ ] **有权限边界**：工具白名单，至少 1 个 Forbidden 操作
- [ ] **有 SLO**：≥3 个 SLI，每个有目标值
- [ ] **有成本和 latency 记录**：能答出"单次请求平均多少钱、TTFT 多少"
- [ ] **有 prompt injection 测试**：≥3 个 payload，至少 1 个靠基础设施挡
- [ ] **有 step 预算和 verifier**：端到端正确率**有数字**
- [ ] **有 runbook**：数值级 + 事故模式库映射
- [ ] **能进入 Capstone**：docs/ 已经有 14 节的素材

**达标后**：你已经是一个**有 AI SRE 实战经验的工程师**。

---

## 可选支线 · 日志分类小模型 / LoRA 微调

> [!NOTE]
> 这是**支线**，不是主线。**默认不做**。做之前必须先回答："为什么这里该微调，而不是继续用 RAG + prompt？"

### 什么时候考虑支线
- 主线已经跑起来，**进入稳态**（Unit 3+ 后）
- 发现有**高频、窄任务**（日志分类、事故类型分类、routing）用 LLM 成本不合算
- 有**足够标注数据**（≥1000 条）
- 已跑过 eval 证明**当前 LLM 方案确实不够**

### 可做的任务（SRE 场景）
- **日志异常分类**：INFO / WARN / ERROR / CRITICAL 之外的细分
- **事故类型分类**：network / disk / cpu / memory / app-bug / upstream-dep
- **Routing classifier**：把事故 route 到不同 runbook / team
- **投诉分类**：哪类用户投诉最可能是模型质量问题（vs 平台问题）

### 做之前必须有
- **一份决策文档**：为什么这里该微调
  - 当前 LLM 方案的准确率 / 成本
  - 微调预期的提升
  - 训练 + 维护的代价
  - 失败 / 漂移时的 fallback（能不能退回 LLM？）
- **标注数据管道**（清洗、对齐、版本化）
- **Eval set**（训练前就有，不是训完再补）

### 和主线的关系
- **不替代主线**：主线依然是 RAG + Tool-use Agent
- **作为 subsystem**：分类结果喂给主线 Agent 做决策
- **可以作为 Unit 5 的可选扩展**（路线 A 的进阶）或**个人独立项目**

### 什么时候不该做
- 任务边界模糊（多意图混合）→ 回 LLM
- 数据少于 1000 条 → 先积累
- 没有人长期维护（上线后没人管 drift）→ 别做
- 为了简历想有"微调经验"→ 这是 reward hacking，不要

参考 [深入 09 · 何时不该用 AI](../深入/09-何时不该用AI.md) 的判断框架，**反向应用**：大多数情况下"该用 RAG + prompt"的场景，也是"不该微调"的场景。

---

## 关于真实数据

用**你自己公司的 runbook / postmortem**价值最大（真实场景、真实词汇），但涉及敏感信息要**脱敏**：

- 脱掉内部服务名（`payment-service` → `service-A`）
- 脱掉具体 IP / 用户 ID / 订单号
- 保留**结构和模式**（告警格式、事故流程、沟通模板）

**如果暂时拿不到真实数据**，可用公开替代：
- Google SRE Book 的案例
- 公开的 postmortem 集合（各家 engineering blog）
- AWS / GCP / Azure 官方 runbook

---

## 贯穿项目和本书其他部分的映射

| 本书组件 | 在项目里的作用 |
|---|---|
| [Unit 0-5 周任务](周循环总览.md) | **每周 B2 产出优先落到项目**（代码 / 文档 / 配置） |
| [复习系统](../复习/README.md) | 过概念时**对照项目当前状态**，快速识别盲点 |
| [附录 E · 模板库](../附录/E-模板库.md) | 项目 `docs/` 目录**直接复用这些模板** |
| [深入 01-10 专题](../深入/) | 项目实际碰到问题时**按需查**，不求通读 |
| [代码参考](../代码/README.md) | **起步直接 copy 改**，尤其 01 caching / 02 agent / 04 eval |
| [Capstone](Capstone-AI生产架构评审包.md) | 项目的**最终产出**就是 Capstone 的内容 |

---

## 常见问题

### Q1：我的工作不直接碰 AI，做这个项目有意义吗？
**有**。SRE 未来运维的系统里**一定会有 LLM**。这个项目给你的是**带着 SRE 视角理解 AI 系统**的肌肉记忆——即使两年内你不碰 AI 线，当业务方要上 AI 时，你就是团队里**最有话语权的那个人**。

### Q2：我的公司不让我用 Claude / GPT，能做吗？
**能**。全书的设计就是 vendor-neutral（见[深入 03](../深入/03-模型与工具场景化最佳实践.md)）。用**本地 vLLM + 开源模型**（Llama / Qwen）完全够用，只是 Unit 0 的 tool use 部分需要选**tool use 支持好的模型**（Qwen3-7B-Instruct 或更大）。

### Q3：我时间少，能裁剪吗？
**能**。最小可行路线：
- Unit 0 全做（~2 周）
- Unit 1 做工具白名单 + Trifecta（跳过红队）
- Unit 2 做 trace + L1 eval（跳过 L2 judge 校准）
- Unit 3 做 SLO 文档（不实现 metrics）
- Unit 4 做 step 预算（不加 verifier）
- Unit 5 读不做

耗时 **~6 周**。适合求职前冲刺用。但**深度远不如完整 19 周**。

### Q4：项目做完了可以开源吗？
可以，**但注意数据脱敏**。开源后可以作为面试 portfolio。**别把公司 runbook 直接 push 上去**。

---

## 给 SRE 的一句话总结

> [!IMPORTANT]
> 读这本书**不做贯穿项目**，像健身只看教练视频不下场。
>
> 做贯穿项目**不读这本书**，像闷头蛮练容易伤。
>
> **两者结合 = 4.5 个月把你从"SRE"转化为"有 AI SRE 实战的 SRE"**。
>
> 别只写文档。**代码要能跑、trace 要能追、eval 要跑过、runbook 要能用**。

---

[← 周循环总览](周循环总览.md)  ·  [→ Capstone](Capstone-AI生产架构评审包.md)  ·  [📖 目录](../README.md)
