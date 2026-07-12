---
title: 深入 17 · LLM 网关的 SRE 视角
updated: 2026-07-12
tags: [deep-dive, gateway, sre, multi-provider, observability]
---

# 深入 17 · LLM 网关的 SRE 视角

> [← 返回目录](../README.md)  ·  对应知识章节：[第 5 章 · AI 推理服务的可靠性工程](../知识/05-AI推理服务的可靠性工程.md)、[第 7 章 · 质量可观测性 ＋ Data Flywheel](../知识/07-质量可观测性与DataFlywheel.md)

> 把"模型/Agent 内部 SRE"和"网关/中间层 SRE"分开看。这一篇专讲后者——很多团队容易忽视它，但**真实生产中 80% 的"AI 系统"其实就是这一层**。

---

## 0. 谁需要读这一篇

- 你的团队**不直接运营推理服务**，而是把多个上游（OpenAI / Anthropic / Gemini / 自建）聚合在一个统一 endpoint 后面，对调用方提供统一接口
- 或者你直接运营推理服务，但**有专门的 API 网关**做鉴权、限流、计费、路由
- 或者你只是用单个上游模型，但已经在考虑"未来要不要支持第二家"——这一篇能让你提前避免几个一旦上线就改不回来的设计错误

如果你完全不在这个位置，可以跳过本章。但**第 5 节"网关 = AI SRE 第一现场"**值得每个 AI SRE 看一眼，是组织边界判断。

---

## 1. 网关位的特征：看不到模型，但能看到所有调用

普通推理服务 SRE 看到的是"模型实例的内部状态"——KV cache、batch 队列、GPU 利用率。
网关 SRE 看到的是另一组东西：

| 维度 | 推理服务视角 | 网关视角 |
|---|---|---|
| 模型内部 | ✅ 可观测 | ❌ 黑盒，只能看 API 行为 |
| 所有上游差异 | ❌ 不关心 | ✅ 必须每天抹平 |
| 调用方代码 | ❌ 看不到 | ❌ 看不到 |
| 调用方流量画像 | 部分 | ✅ 全部（全租户视图） |
| 跨租户的横向对比 | 不可能 | ✅ 唯一能做的位置 |
| 计费 | 通常不管 | ✅ 是核心责任 |

**两个推论**：

- 网关位是**唯一**能把"哪一家上游今天表现更差"做横向对比的位置。这件事不是某个模型 SRE 的本职，但对整个组织的可靠性是关键。
- 网关位的所有 SLI 都必须**按 (调用方租户 × 上游通道 × 模型)** 三维度切——任意一维度合并都会导致归因失败。

---

## 2. 不能控制调用方时的可观测性模式

传统可观测的标准做法是"应用代码 → trace SDK → 后端"，这一假设的前提是你能改业务代码。

**网关位这个假设不成立**——调用方可能是几十个团队、几百个脚本、若干第三方 SDK，你改不动他们。所以你必须用一套不一样的可观测模式：

### 2.1 在网关侧自发 trace，回写 header

- 网关收到请求时，如果 header 里**没有** `traceparent` / `x-request-id` / 自定义 trace id，就**自己生成一个**
- root span 起在网关入口，子 span 覆盖：鉴权、路由选通道、上游 RTT、首字节、流式持续期、计费
- 在 response header 里**回写** `x-trace-id` 和 `x-request-id`——这是给调用方做关联的唯一手段

### 2.2 把 trace 拆成三段，分别上报给不同对象

| 段 | 谁会看 | 含什么 | 保留时长 |
|---|---|---|---|
| 元数据段 | 平台运营 | 租户、模型、通道、token 计数、状态码、四段 TTFT | 长（90 天+） |
| 请求体段 | 调用方自己 + 出问题时排查 | 完整 prompt、完整响应 | 短（7 天-30 天，且需脱敏） |
| 计费段 | 财务 + 调用方 | usage 字段、缓存 token 计数、单价、币种 | 长（按账期） |

**为什么要拆**：合在一起会有两个问题——一是请求体里的 PII 上到长保留的看板上违规；二是元数据段查询频次远高于请求体段，混在一张表上无法做分级存储。

### 2.3 流式请求的 trace 要落到 token 级

普通 HTTP trace 一个 span 一个请求即可。LLM 流式请求**必须**记录：

- 首 token 的时间点（用于 `ttft_model_ms`，参见[深入 01 · TTFT 四段归因](01-首包延迟与吞吐的影响因素.md#310-网关位的-ttft-四段归因gateway-side-attribution)）
- 流期间的 token 增量心跳（每 N 个 token 或每 N 秒一次 span event）
- 流结束原因：正常 stop / 客户端断开 / 上游异常 / 网关主动断（参见 [深入 10 · Pattern 16 · Zombie Stream](10-AI系统事故模式库.md#pattern-16--zombie-stream伪存活流)）

只记请求开始/结束这一对时间戳的 trace，对流式诊断**完全无用**。

---

## 3. 抹平多上游差异的代价

每接入一家新上游都不是"加一个 adapter 就好了"。下面这些坑只在网关位才会显形：

### 3.1 先把协议翻译成 canonical schema

> [!NOTE]
> 本节协议事实以 Anthropic Claude Messages API、OpenAI Responses API / Chat Completions 官方文档为准，快照日期为 2026-06-30。协议会变；网关设计要假设它会继续漂移。

多上游网关最大的错觉，是以为 Claude / OpenAI / Gemini 的差别只是字段名不同。真正的差别在**协议语义**：谁保存状态、工具调用如何回灌、流式事件如何结束、usage 字段代表什么、MCP 工具由谁连接、错误是否是 HTTP 错误。

| 面 | Claude Messages API | OpenAI Responses API | OpenAI Chat Completions |
|---|---|---|---|
| 基本抽象 | `messages` + content blocks；默认由客户端保存完整历史 | `input` / output items；面向 agentic workflow，可用 `previous_response_id` / `store` 做状态延续 | `messages` + `choices[]`；经典 chat 形态，客户端保存历史 |
| 工具调用 | `tool_use` content block；结果作为 `user` 消息里的 `tool_result` block 回灌 | 输出 items 里出现 function / built-in / MCP 相关 item；工具结果再作为 input item 回灌 | `message.tool_calls`；结果用 `role="tool"` + `tool_call_id` 回灌 |
| 结束原因 | `stop_reason`，常见有 `end_turn`、`tool_use`、`max_tokens`、`pause_turn`、`refusal` | response status + output item 类型；流式下看 typed events 与 done/error | `finish_reason`，常见有 `stop`、`length`、`tool_calls`、`content_filter` |
| 流式 | SSE 有 `event:` 名称；如 message / content block / delta / stop 等层级事件 | SSE typed events；增量可能是 text、function arguments、tool progress 等不同事件 | SSE chunk；历史兼容里常见 `data: ...` + `[DONE]` |
| 内置工具 | Web / code / MCP 等能力按 Claude API 版本与 beta 状态暴露 | Responses 是 OpenAI 新项目推荐面，统一内置 tools、function calling、remote MCP | 支持 function/tool calling，但不是新 agentic 能力的主承载面 |
| MCP | Messages API 的 MCP connector 需要声明远端 server 与对应 toolset；鉴权/可用性是协议边界 | Responses API 支持 remote MCP / connectors；会出现 MCP list / approval / call 相关 items | 不应把 Chat Completions 当 MCP 主路径 |

**网关侧的最低工程要求**：不要把任何一家供应商的请求/响应格式直接暴露成公司内部标准。内部应该先定义一套 canonical schema，再由 provider adapter 做双向翻译。

这条要求的价值可以用一个形状说清：M 个调用方直连 N 家上游、各接各的协议，是 **M×N** 份互不复用的胶水；中间插一层 canonical schema，调用方只对内部协议编程、每家上游只被 adapter 对接一次，M×N 就塌成 **M+N**。像 USB-C——一个统一口，两端换任何设备都不用重接线。

同一个 `M×N→M+N` 的形状在别处也出现：**MCP**（Model Context Protocol）之于"应用 × 工具"，就是 canonical schema 之于"调用方 × 模型厂商"——写一次 MCP Server，所有支持 MCP 的客户端都能用；跨 Agent 通信（Agent × Agent）也是同一回事。认得这个形状，接入层很多设计就不必死记。

最小 canonical schema 至少要包含：

```yaml
request:
  tenant_id: string
  task_type: string
  model_policy: string        # 不是裸 model name
  input_messages: []          # 内部统一消息块
  tools: []                   # 内部工具定义，不等同于上游原始 tools
  budget: {tokens, steps, wall_clock_ms}
response:
  output_blocks: []
  action_requests: []         # tool/function/mcp 调用意图
  stop_class: enum            # completed / needs_tool / filtered / length / error / paused
  usage_union: object         # 所有上游 usage 字段的并集
  upstream_raw_ref: string    # 原始请求/响应/错误的留档引用
```

这里的关键词是 **union，不是 intersection**。如果 canonical schema 只保留三家都有的字段，你会把最重要的差异删掉：Claude 的 `cache_read` / `cache_creation`、OpenAI reasoning / cached / tool 相关 usage、不同供应商的安全拒答细分、MCP approval 状态，都会在事故排查时消失。

### 3.2 流式协议的不一致

- OpenAI 风格：`data: {chunk}\n\ndata: [DONE]\n\n`
- Anthropic 风格：`event: <type>\ndata: {...}\n\n`，多种事件类型
- Gemini：JSON streaming，每行一个完整对象，但偶尔有 server-side keepalive 字节
- 自建（vLLM/SGLang）：通常 OpenAI 兼容，但 `[DONE]` 时机和真实生成结束之间有时差

**网关侧的最低工程要求**：每个上游的流解析器**必须是独立模块**，不要试图写一个通用解析器。一旦试图通用化，所有疑难故障都会卡在这一处。

### 3.3 错误语义的不一致

- 同样是"上下文超长"，OpenAI 是 `context_length_exceeded`（400），Anthropic 是 `invalid_request_error`（400 但 message 完全不同），Gemini 是 `INVALID_ARGUMENT`（400，proto 风格）
- 同样是"配额耗尽"，有的家是 429，有的家是 403 + 特定 code
- 同样是"上游过载"，有的家返回 503，有的家返回 200 但内容是 "I'm sorry, please try again"

**网关侧必须做的**：

1. 统一一套**对外错误码**，明确文档化每个上游的错误如何映射
2. **保留原始错误**——在响应里加一个 `x-upstream-error` header 或 trailer，调用方排查时需要原始信息
3. 把"200 + 实际是过载文案"作为一类**伪成功**单独识别——这种事故不靠状态码能发现

### 3.4 计费字段的不一致

参见 [深入 02 · 6.5 多上游网关位的特殊风险](02-Prompt-Caching原理.md#65-多上游网关位的特殊风险)。这里再强调一句：**网关计费日志的字段集是"所有上游字段的并集，不是交集"**——任何一家上游有的字段都要留位置，没有就填 0。否则月底对账就会出现"账面少了 X% 的缓存命中收入"这类事故，且无法追溯。

### 3.5 同名模型不一定是同一个模型

`gpt-4o-2024-08-06` 在 OpenAI 直连和 Azure OpenAI 上**实际行为可能不同**——Azure 有自己的 safety layer 和路由策略。你当前的主力模型 ID（写作时如 `claude-sonnet-4.x`）同时挂 Anthropic 直连和 AWS Bedrock，两条通道**也不同**——延迟特性、错误码、流式行为都有差异。重点不在具体型号，而在同一个模型 ID 走了两条通道。

**网关侧必须做的**：

- 模型 ID 在内部表示里**始终带上 channel 维度**：`(model_name, channel_id)` 才是可观测/可路由的最小单位
- 看板上从不展示孤立的 `model_name`——一定是 `model_name × channel`
- 灰度新通道时把它当成"一个全新的模型上线"对待，不是"加了一个供应商"

---

## 4. 网关层的"静默退化"是个独立的对手

[第 5 章 · 5.5 静默降级](../知识/05-AI推理服务的可靠性工程.md)讲了模型层的静默降级。在网关层有它的"大表哥"——**上游通道整体退化**：

- 同一个模型 ID，今天的回答质量比上周差
- 上游侧从未发任何变更通知
- 调用方的成功率/延迟看着都没变（因为他们看的是网关聚合指标）
- 唯一能感知的是端到端的业务质量，但等到那时已经晚了

**网关侧的检测手段**（关联 [Unit 3 · 推理 SLO 与静默降级](../练习/Unit3-推理SLO与静默降级/总览.md)）：

1. **金标准探针**：每个通道周期性注入若干已知答案的 prompt（5-50 条够），跑一组确定性 metric
   - 输出长度落在 [a, b]
   - 输出格式（JSON / 列表 / 引用格式）通过校验
   - 关键短语命中（embedding 相似度 > 阈值）
   - 语种检测（中文 prompt 不能输出英文回答）
2. **跨通道横向对比**：同一探针在多个通道上同时跑，**通过率出现分叉**就报警
3. **不依赖上游错误码**：上面这些 metric 全部是黑盒探针，与上游有没有报错无关——这是关键

把这套探针看作**网关位的 health check**，是最低标准；上面 4 类 metric 是入门，再往上是用 LLM-as-judge 做更高级的判定（成本高、延迟大，按通道关键性投入）。

---

## 5. 网关 = AI SRE 的第一现场

很多组织把"AI 网关"划归"中间件团队"或"API 平台团队"，把"AI SRE"留给"算法/推理团队"。这种切分在 LLM 时代是错的，理由有三：

1. **用户感知的 SLO 在网关位定型**。上游再稳，网关一行流式解析写错（参见 [Pattern 16 · Zombie Stream](10-AI系统事故模式库.md#pattern-16--zombie-stream伪存活流)）就全线崩。"用户以为是模型问题"的事故，事后追查八成落在网关。
2. **AI 特有的故障模式集中在网关位**。本书前面 16 个事故 Pattern 里至少有 6 个（Cache Miss Storm、Tokenizer Drift、Cost Explosion via Context、KV Preemption、Batching Spike、Zombie Stream）的最佳观察/拦截点都在网关——不是在模型里。
3. **计费、路由、限流是 AI SRE 的责任，而它们都长在网关上**。把网关划走等于把可靠性预算的控制权交出去。

**给读者的判据**：如果你的组织中"网关"和"AI SRE"是两个团队，且每周不开相同的例会、不看同一组指标——那么你要么推动合并，要么清楚地意识到**自己正在用一种反生产模式做事**。

---

## 6. Data Flywheel 在网关位的廉价起点

[第 7 章 · Data Flywheel](../知识/07-质量可观测性与DataFlywheel.md) 讲的飞轮起点是"用户反馈"。这是理想，**绝大多数团队拿不到密集、可靠的用户反馈**。

网关位有一个被低估的起点——**计费日志**。它有几个非常稀缺的属性：

- 几乎是免费的副产品（计费本来就要打日志）
- 100% 覆盖（每一次请求都有一行）
- 包含所有最重要的元数据：用户、租户、模型、通道、prompt token 数、completion token 数、TTFT、流时长

要把它升级为飞轮起点，**只需在现有计费日志里加三列**：

| 字段 | 含义 | 用途 |
|---|---|---|
| `output_hash` | completion 前 256B 的 SHA256 | 去重、识别"模板化输出泛滥" |
| `finish_reason` | 上游返回的结束原因（stop/length/tool_use/safety/error） | 异常分布分析 |
| `quality_tag` | 默认 NULL，留给 Eval 子系统回写 | 离线 Eval 的目标列 |

加完这三列后，最小可运行飞轮长这样：

```
network gateway logs (含上面三列)
    │
    ▼  每天抽样 N 条
[离线 Eval Worker]
  ├─ 规则层（长度 / 格式 / 语种 / finish_reason 异常）
  └─ LLM-as-judge（按 quality_tag 分布抽样）
    │
    ▼  回写 quality_tag
[Grafana 看板]  按 (model × channel × tenant) 的 bad rate 趋势
    │
    ▼
[告警]  某通道 bad rate 漂移 → 触发降级 / 通知供应商
```

**与第 7 章那张"理想飞轮图"的关系**：网关版飞轮**不依赖用户主动反馈**，所以它跑得起来。是飞轮的"启动器"，不是替代品。等它跑起来积累了几个月数据，再叠加用户反馈、再叠加人工标注，就是第 7 章那张图。

---

## 7. 网关位的最小自检清单

如果你正在/即将运营一个 LLM 网关，对照这一份清单：

**可观测**

- [ ] TTFT 按 client/gateway/upstream/model 四段拆分（[深入 01 · 3.10](01-首包延迟与吞吐的影响因素.md#310-网关位的-ttft-四段归因gateway-side-attribution)）
- [ ] 流式请求有 token 级心跳，不是字节级
- [ ] 计费日志同时记录 prompt / cache_read / cache_write / completion 四列
- [ ] 计费日志附 output_hash / finish_reason
- [ ] 每个 (model × channel) 单独看 SLI，从不混合

**协议适配**

- [ ] 内部 API 有 canonical schema，不直接暴露 Claude / OpenAI / Gemini 任一家的原始格式
- [ ] Claude Messages、OpenAI Responses、OpenAI Chat Completions 各有独立 adapter 与 fixture，不共用一个"万能解析器"
- [ ] `stop_reason` / `finish_reason` / response status 映射到统一 `stop_class`，同时保留原始字段
- [ ] 流式事件的 start / delta / tool / error / done 都有逐供应商测试样例
- [ ] MCP / function / tool 调用都先落成内部 `action_request`，再由 harness 决定是否执行
- [ ] 原始上游 request / response / error 有留档引用，事故复盘能还原供应商原文

**可控**

- [ ] 入口 RPM/TPM 限流 + 上游 inflight token budget 限流（[深入 05 · 陷阱 5](05-LLM推理服务的容量规划.md#陷阱-5在网关层仅用-rpm-限流相当于没有实施容量保护)）
- [ ] 流式 N 秒无 token 增量主动断流，不等上层超时
- [ ] 通道级降级路径已演练（不只是文档）

**可演进**

- [ ] 每个上游通道有金标准探针，跨通道横向对比
- [ ] 调用方能从 response header 拿到 trace_id 自助排查
- [ ] 上游错误原文保留可供事后追溯，不被网关吞掉

任何一条做不到，都对应着一类未来的生产事故。

---

## 8. 关联与延伸

- [深入 01 · TTFT 四段归因](01-首包延迟与吞吐的影响因素.md#310-网关位的-ttft-四段归因gateway-side-attribution) —— 网关位最重要的 SLI 拆解
- [深入 02 · 多上游 Caching 风险](02-Prompt-Caching原理.md#65-多上游网关位的特殊风险) —— 缓存语义不一致与计费陷阱
- [深入 05 · inflight token 限流](05-LLM推理服务的容量规划.md#陷阱-5在网关层仅用-rpm-限流相当于没有实施容量保护) —— 容量保护的正确抽象
- [深入 10 · Pattern 16 · Zombie Stream](10-AI系统事故模式库.md#pattern-16--zombie-stream伪存活流) —— 网关位独有的伪存活流事故
- [深入 11 · AI SRE 现实图谱](11-AI-SRE现实图谱.md) —— 真实生产环境的系统/指标/组织边界全景
- [Unit 2 · Trace-Eval 统一可观测性](../练习/Unit2-TraceEval统一可观测性/总览.md) —— 把这一篇里的可观测要求落到具体设计

🔄 复习：[核心概念卡](../复习/核心概念卡.md) · [Active Recall 题库](../复习/Active-Recall题库.md)

---

← [深入 16 · Embedding 服务作为独立运维对象](16-Embedding-服务作为独立运维对象.md)  ·  [📖 目录](../README.md)  ·  [深入 18 · LLM 成本工程 →](18-LLM成本工程.md)
