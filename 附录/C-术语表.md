---
title: 附录 C · 术语表
updated: 2026-07-04
tags: [appendix]
---

# 附录 C · 术语表

> [← 返回目录](../README.md)

> [!IMPORTANT]
> **这张表分两层，用法不同。**
>
> - **第一性术语（下面 5 个分区，建议背下来）**：跨工具、跨厂商、跨年份长寿的概念——致命三角、Blast Radius、Reversibility、Step Budget 这类是基石，工具换代它们也不变，值得真正记进脑子。
> - **当前产品 / 参数名词（文末单列，查用即可）**：具体模型名、档位、默认参数行为——随厂商版本月度漂移，**不要背**，用到时查、并以厂商官方文档为准。这一层带 🕒 快照标记，标注的数字只是当期量级。

## 大模型基础

| 术语 | 含义 |
|---|---|
| Token | 模型的最小处理单位。英文约 0.75 词/token；中文通常每字 1-2 个 token——tokenizer 差异大，中文友好的 tokenizer 可低至 1 token/字以下，分厂商数字见 [科学 04](../科学/04-Tokenization的坑.md) |
| Tokenizer 代际差异 | 同一厂商不同代模型可能换 tokenizer，相同字符的 token 数会变，按 token 计账时要对每代单独估。例（2026-06 快照 🕒，详见 [科学 04 · §5](../科学/04-Tokenization的坑.md)）：Claude Opus 4.7 起换了新 tokenizer，1M context 对应 ~555k 词，而同 1M context 的 Sonnet 4.6 对应 ~750k 词——意味着 Opus 4.7+（含 4.8）的 token 体积比 Sonnet 4.6 大约 1.35× |
| Context Window | 一次对话能容纳的最大 token 数 |
| System Prompt | 贯穿整个对话的指令 / 规则 |
| Temperature / top-p | 控制输出随机性的采样参数 |
| Tool Use / Function Calling | LLM 返回结构化"工具调用"请求，由宿主代码执行并回灌结果 |
| Streaming | Token 逐个返回的输出模式 |
| Reasoning / Thinking Budget | 推理时让模型"多想一会"的预算控制，通常会增加延迟和 token 成本 |
| 精度（精度位数 / Precision） | 每个模型参数占多少字节，直接决定显存占用和带宽需求：**fp32 = 4 / bf16 = 2 / fp16 = 2 / int8 = 1 / int4 = 0.5** 字节。例：70B bf16 ≈ 140GB；70B int4 ≈ 35GB |

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
| Silent Degradation | 指标全绿但系统已经数学出错的静默故障 |
| Judge Model | 用模型评估另一个模型输出质量的评估方法 |
| Data Flywheel | 生产 trace → 标注 → eval → 改进 → rollout 的反馈回路 |
| Assertion Battery | 任务专属的硬规则校验集（替代"全局幻觉率"这类不可操作指标） |

## 自治与安全

| 术语 | 含义 |
|---|---|
| Lethal Trifecta | 私有数据访问 + 不受信输入 + 外泄通道三者共存的危险组合（Simon Willison 原版三条腿）。工具访问不是独立的一条腿，而是放大器——同时加宽不受信输入的入口和外泄通道的出口。详见 [第 6 章](../知识/06-AI自治与上下文架构约束.md) |
| Capability-scoped Credentials | 权限按操作范围细分、最小化的凭证 |
| Blast Radius | 一个操作失败时可能影响的范围 |
| Reversibility | 操作可回滚的程度，自治分级的核心判据 |
| Harness（宿主运行时） | 包在模型外面、把工具调用意图变成受控系统动作的那层：负责工具注册、权限执行、沙箱/egress、上下文管理、审计与预算/中断。模型负责"提出下一步"，harness 负责"决定下一步是否被允许"。Agent 的真实安全边界在这里，不在 prompt 里 |
| Canonical Schema（内部规范协议） | 多上游网关自定义的统一请求/响应结构。各厂商协议先经 provider adapter 翻译成它，再对外暴露。原则是字段取"所有上游的并集，不是交集" |

## 架构

| 术语 | 含义 |
|---|---|
| Compound AI System | 由多步推理、工具调用、检索组成的复合系统 |
| Step Budget | 一条 Agent 链路允许的最大推理步数 |
| Verifier / Gate | 在链路中插入的校验节点，用于截断错误累积 |
| 并行维度（TP / PP / EP / DP） | 把单卡装不下的大模型摊到多卡的四种切法：**TP**（张量并行，切层内权重、降单请求延迟、每 token 多次 all-reduce、只能待 NVLink 域内）、**PP**（流水线并行，按层分段、跨节点装大模型、有流水线气泡）、**EP**（专家并行，MoE 专用、把专家摊到多卡、每 MoE 层 all-to-all）、**DP**（数据并行，整个单元复制、加吞吐但不省显存）。铁律：`总卡数 = TP×PP×DP`；EP 不是再乘的第五维——MoE 的专家在既有 DP×TP 的同一批卡上重新摊开（如 DeepSeek decode 的 144 卡：attention 走 DP144、路由专家走 EP144）。TP 在节点内、PP/DP/EP 跨节点。详见 [深入 20](../深入/20-单卡装不下的大模型分布式推理.md) |
| PD 解耦（Prefill/Decode Disaggregation） | 把 prefill（吃算力、容忍延迟）和 decode（吃带宽、延迟敏感）放到两个独立 GPU 池，各用最合适的硬件与并行度，中间传 KV cache。目标是 **goodput**（同时满足 TTFT 与 TPOT 两个 SLO 前提下的每卡有效请求数），而非裸吞吐。详见 [深入 20 · §4](../深入/20-单卡装不下的大模型分布式推理.md) |
| 互联带宽层级 | 多卡推理的物理地基：**HBM（卡内，TB/s）≫ NVLink/NVSwitch（节点内，百 GB/s 级）≫ InfiniBand/RoCE（跨节点，~50 GB/s/卡）≫ 以太网**。每降一层掉约一个数量级，决定了每种并行"能跨多远"。数字快照见 [深入 20 · §1](../深入/20-单卡装不下的大模型分布式推理.md) |
| Prompt Registry | 管理 prompt 工件生命周期的"包管理器"：**稳定标识符 + 不可变版本 + 可移动指针（label）**——发布 = 移动指针、回滚 = 指针移回。发布单元是"模板 + 模型版本 + 采样参数 + 工具 schema"（四联版本绑定 Prompt/Model/Embedding/Judge 的 prompt 侧）。详见 [深入 21](../深入/21-Prompt作为运维对象.md) |
| 回放评审（Backtest） | 从生产 trace 采样真实请求，用候选 prompt / 模型版本重跑并与当前版本成对比较的发布前评审——"用昨天的真实流量预演明天的行为"。详见 [深入 21 · §4](../深入/21-Prompt作为运维对象.md) |

---

## 当前产品 / 参数名词（2026-06 快照 🕒）

> [!WARNING]
> 这一层是**查用即可、不要背**的快变信息：模型名、档位、默认参数行为随厂商版本月度漂移。下表是 **2026-06 快照**，实际选型 / 调用前以厂商官方文档为准。完整选型口径见 [深入 12 · 三大模型系列使用指南](../深入/12-Claude-GPT-Gemini三大模型系列使用指南.md)。

| 术语 | 含义 |
|---|---|
| Claude Opus / Sonnet / Haiku | Anthropic Claude 系列的常见分层：Opus 偏最强（当前旗舰 Opus 4.8，2026-05-28），Sonnet 偏平衡主力（4.6），Haiku 偏轻量快速（4.5）。**注意**：Opus 4.8 起 `effort` 默认 `high`，调用方不显式 override 会一次性吃掉 3-10× token 预算 |
| Claude Fable / Mythos | 在 Opus/Sonnet/Haiku 主线之外的研究分支：Fable 5（2026-06-09）通用研究形态、Mythos Preview 是 Project Glasswing 防御性安全研究专用（邀请制）。不是日常生产首选 |
| GPT flagship / mini / nano / reasoning | OpenAI GPT 系列的常见分层：旗舰做复杂任务，mini/nano 做低成本高频任务，reasoning 档用于复杂推理 |
| Gemini Pro / Flash / Flash-Lite | Google Gemini 系列的常见分层：Pro 偏复杂和长上下文，Flash 偏速度成本平衡，Flash-Lite 偏轻量高吞吐。当前稳定档为 Gemini 3.5 Flash，旗舰为 Gemini 3.1 Pro Preview（Gemini 3 Pro Preview 已于 2026-03-09 关停）|
| Computer Use Preview | 让 LLM 直接驱动浏览器/桌面操作的能力。当前可用：Anthropic Claude Computer Use、OpenAI Codex/Operator、Google Gemini 2.5 Computer Use Preview。**SRE 警示**：启用即把模型同时拉到 "私有数据 + 不受信内容 + 外部行动" 三条线上，必须按致命三角扩展防御 |
| `effort` 参数（reasoning effort） | Anthropic / OpenAI / Google 推理模型上控制"思考深度"的统一参数，档位通常为 `none/low/medium/high/xhigh`。每升一档延迟与 token 成本可放大数倍。**Claude Opus 4.8 起在 API/Claude Code 上默认 `high`**，是 4.7 → 4.8 升级的最大坑 |
| Messages API / Responses API / Chat Completions | 当前三种主流 LLM 调用协议：Anthropic **Messages API**（block-structured、默认无状态、`tool_use`/`tool_result`、`stop_reason`）；OpenAI **Responses API**（OpenAI 新项目推荐的统一 agentic 面，input/output item、内置工具、remote MCP、可选状态延续）；OpenAI **Chat Completions**（经典兼容层，`messages`/`choices[]`/`finish_reason`/`tool_calls`）。差异不只在字段名，更在状态、工具循环、流式与计费语义，详见 [深入 17](../深入/17-LLM网关的SRE视角.md) |
