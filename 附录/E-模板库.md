---
title: 附录 E · 模板库
updated: 2026-07-04
tags: [appendix, templates, reusable]
---

# 附录 E · 模板库

> [← 返回目录](../README.md)

> [!NOTE]
> **定位**：本书最有复用价值的 9 份模板，集中在一处。**直接 copy 用**，不必翻章节抄。
>
> **配合 [Capstone · AI 可靠性架构评审包](../练习/Capstone-AI生产架构评审包.md) 使用**——Capstone 的 15 节里，有 6 节可以用下列模板起步。
>
> **配合 [🛠️ 贯穿项目 · SRE 事故助手](../练习/贯穿项目-SRE事故助手.md) 使用**——项目的 `docs/` 目录可以**直接填充这些模板**（slo.md / threat-model.md / step-budget.md / runbook-numeric.md 等都对应到下面的模板编号）。

---

## 模板 1 · Trace-Eval 一体化设计

**来源**：[深入 06](../深入/06-Eval-Pipeline设计.md)、[Unit 2](../练习/Unit2-TraceEval统一可观测性/总览.md)

```markdown
## Trace-Eval 一体化设计 · <系统名>

### 统一数据流
生产 trace → 抽样 → L1/L2 eval → 失败样本入库
  ↑                                         ↓
  └── rollout ← prompt 改动 ← eval 集更新 ← 人工标注

### 数据字段（trace = eval sample 的 schema 合一）
| 字段 | 来源 | 用于 trace | 用于 eval |
|---|---|---|---|
| trace_id | 系统生成 | ✓ | ✓ |
| prompt | 业务代码 | ✓ | ✓ |
| response | LLM | ✓ | ✓ |
| tool_calls | LLM | ✓ | ✓ |
| user_feedback | UI | ✓ | ✓ L3 |
| latency_ms | 系统 | ✓ | - |
| tokens | LLM usage | ✓ | - |

### 抽样策略
- 全量流量的 5% 进入 eval pipeline
- 低流量类目强制采样 100%（保覆盖度）
- 用户反馈为负的请求 100% 采样

### Data Flywheel · 每一步 owner
| 步骤 | Owner | 频率 |
|---|---|---|
| Trace 持久化 | SRE | 实时 |
| 抽样 + L1/L2 | SRE + ML Eng | 实时 |
| 失败样本标注 | ML Eng + QA | 每周 |
| Gold set 更新 | ML Eng | 月度 |
| Prompt / 模型改动 | ML Eng | 双周 |
| Rollout + 监控 | SRE | 按需 |

### Eval 自身 SLO
- 覆盖率 ≥ 5%
- 评估延迟 p95 < 5 min
- Judge 对齐度 κ ≥ 0.6
- Pipeline uptime ≥ 99.5%
- 失败率 < 1%

### Fallback 流程（Eval 挂了怎么办）
- 告警 SRE + ML 双方
- 暂停所有**自动**基于 eval 的决策
- 转人工 review 模式
- 超 1 小时 ≈ 烧掉月度 error budget 的 28%（99.5% → 216 分钟/月）
```

---

## 模板 2 · 三层 Eval 设计

**来源**：[深入 06 · §1](../深入/06-Eval-Pipeline设计.md)、[Unit 2 · Week 2](../练习/Unit2-TraceEval统一可观测性/Week2-三层Eval体系设计.md)

````markdown
## Eval 设计 · <capability 名>

### L1 · Assertion（硬规则）
| 规则 | 检查方式 | 失败意味着 | 处理 |
|---|---|---|---|
| 输出是 valid JSON | json.loads() | 解析失败 | 重试 1 次 |
| 必要字段 X/Y/Z 存在 | schema check | 字段污染 | 拒绝 |
| 长度 ≤ 500 字 | len() | 啰嗦 | 截断并标注 |
| 不含黑名单词 | regex | 内容违规 | 拒绝 + 告警 |
| 引用的 source 存在 | 查已知 source 表 | 虚构来源 | 拒绝 |

### L2 · Judge 模型评分
**维度**（不超过 3 个，每维 binary pass/fail + 一句话理由——0-10 连续分是反模式，见[深入 06 · §2.1](../深入/06-Eval-Pipeline设计.md)）：
- relevance（pass/fail）
- faithfulness（pass/fail）— 尤其 RAG 场景
- completeness（pass/fail）

**Judge 模型**：<选型>（建议用**不同家族**，如主模型 Claude 则 Judge 用 GPT-mini）

**Judge Prompt 骨架**：
```
你是一个严格的评委。逐维度判定是否合格（每项先写一句话理由，再给 pass 或 fail）：
- relevance: ...
- faithfulness: ...
- completeness: ...

输出 JSON：{"relevance": {"reason": str, "verdict": "pass|fail"}, "faithfulness": {"reason": str, "verdict": "pass|fail"}, "completeness": {"reason": str, "verdict": "pass|fail"}}

只输出 JSON。

Question: {question}
Context: {context}
Response: {response}
```

**校准机制**：
- 每周抽 50-100 条让人工打分
- 算 Cohen's κ 或 agreement rate（标签一致的比例；若用多档 rubric 则 |human - judge| ≤ 1）
- 目标：κ ≥ 0.6 / agreement ≥ 70%
- 不达标 → 暂停自动决策 + 换 Judge / 改 rubric

**偏见自检**：
- Length bias（偏好长回答？）
- Position bias（顺序影响？）
- Self-preference（自家模型打自家分偏高？）
- Style bias（偏好 markdown / 列表？）

### L3 · A/B 测试
- **主指标**：<业务 KPI，如 thumbs-up 率 / 留存 / 任务完成>
- **副指标**：编辑距离、后续提问率、平均 session 时长
- **Guardrail 指标**：refusal rate、成本、延迟
- **分流**：用户级 / 请求级（每种的理由）
- **样本量**：<估算> + confidence level
- **触发上量**：主指标显著好 + guardrail 不劣化
````

---

## 模板 3 · 推理 SLO

**来源**：[第 5 章](../知识/05-AI推理服务的可靠性工程.md)、[Unit 3 · Week 1](../练习/Unit3-推理SLO与静默降级/Week1-SLI定义.md)

```markdown
## <服务名> · 推理服务 SLO

### 延迟类 SLI
| SLI | 定义 | 测量点 | 目标 | 告警 |
|---|---|---|---|---|
| TTFT p50 | 首 token 延迟中位 | 客户端 | < 500ms | > 800ms |
| TTFT p99 | 首 token 延迟 99 分位 | 客户端 | < 2s | > 3s |
| Tokens/s p50 | 输出速度中位 | 客户端 | > 25 | < 15 |
| E2E latency p99 | 整体 | 客户端 | 业务对齐 | ... |
| Queue wait time | 服务端排队 | 服务端 | < 200ms | > 500ms |

### 容量类 SLI
| SLI | 定义 | 目标 | 告警 |
|---|---|---|---|
| KV cache 占用率 | 显存占用 | < 85% | > 95% |
| Queue depth | 排队请求数 | < 2× batch | > 5× |
| GPU util | 算力利用 | 60-80% | 持续 > 95% |
| Preemption rate | 抢占率 | < 1% | > 5% |
| Cache hit rate | Prompt cache | > 80% | < 50% |

### 质量类 SLI（按任务类型分桶）
| SLI | 定义 | 目标 |
|---|---|---|
| L1 通过率 per task type | L1 assertion 通过 | > 99% |
| L2 均分 per task type | Judge 均分 | > 7.5 |
| Output length 分布 | 按任务分桶 p50/p99 | 突变 > 20% 告警 |
| Hallucination rate（抽样）| 人工 + judge 综合 | < 2% |

### Error Budget Policy
- 月度 budget：SLO 目标对应的允许"坏时间"
- **按预算消耗比例分级触发**（烧穿前就行动，不是烧穿后）：
  - 消耗 50%：通知 ML 团队，审视变更节奏
  - 消耗 90%：冻结新 feature rollout
  - 消耗 100%：回滚最近变更，所有自动决策转人工，事故升级，产品方案考虑 degrade
```

---

## 模板 4 · 容量规划

**来源**：[深入 05](../深入/05-LLM推理服务的容量规划.md)、[Unit 3 · Week 2](../练习/Unit3-推理SLO与静默降级/Week2-容量规划.md)

```markdown
## <服务名> · 容量规划

### Workload 画像
| 维度 | 当前 | 预期峰值 |
|---|---|---|
| 活跃并发用户 | <N> | <N×factor> |
| QPS | <N> | <N×factor> |
| 平均输入 token (p50) | <N> | ... |
| 平均输入 token (p95) | <N> | **长尾关键** |
| 平均输出 token (p50 / p95) | <N> / <N> | ... |
| 上下文长度分布 | 短 80% / 长 20% | ... |

### 硬件与模型
- 模型：<name + bf16/int8/int4>
- 参数量 × 每参数字节数（bf16=2B、int8=1B、int4=0.5B）≈ <权重 GB>
- GPU：<型号 + HBM GB + 带宽 TB/s>
- TP / PP / EP 策略

### 三个容量分别计算
**Prefill 容量**（compute-bound）：
- 单请求 prefill 时间 ≈ FLOPs / (TFLOPS × 效率)
- 单实例每秒 prefill 数 = 1 / 单请求时间
- 支撑预期 QPS 需要实例数：<计算>

**Decode 容量**（memory-bound）：
- 理论 tokens/s ≤ HBM 带宽 / 权重大小 = <N>
- 为保 p50 tokens/s ≥ X，单实例最多同时服务 <N> 用户
- 支撑预期并发需要实例数：<计算>

**KV Cache 容量**：
- 每 token KV cache = 2 × layers × KV_heads × head_dim × bytes = <MB>
- 每请求 KV cache = per_token × avg_context = <GB>
- 单实例并发 = 可用显存 / 每请求 KV cache = <N>
- 支撑预期并发需要实例数：<计算>

### 决策
- **取 max(Prefill, Decode, KV)** = <N> 实例
- +30% 冗余 = <N> 实例
- 美元成本估算（月度）：<$>

### Prefix Caching 校验
- 开启后有效容量 × <多少>
- 会不会改变瓶颈？

### 长尾处理
- p99 输入 token 如果 > 50k 怎么办？
- 独立 pool 还是共享？
- Per-user 上限？

### Autoscaling 触发条件
- 不用 QPS，用 **Queue depth + KV cache 占用率**
- Scale-up 阈值：Queue > 2× batch 持续 5 min
- Scale-down 阈值：连续 30 min GPU util < 30%（慢 scale down 保 cache 命中）
```

---

## 模板 5 · Agent 复合可靠性评审

**来源**：[第 4 章](../知识/04-系统架构与复合AI可靠性数学.md)、[Unit 4](../练习/Unit4-复合AI可靠性数学/总览.md)

````markdown
## <Agent 名> · 复合可靠性评审

### Step 拆解图
```
[输入] → Step 1: <名> → Step 2: <名> → ... → Step N → [输出]
```

### 每 Step 正确率估算
| Step | 类型 | p_i | 依据 | 失败模式 |
|---|---|---|---|---|
| 1 | LLM 意图理解 | 0.95 | 眼看 200 样本估 | 罕见词意图错 |
| 2 | RAG 检索 | 0.85 | eval 集跑出来的 | chunk 错位 |
| 3 | LLM 生成 | 0.80 | 同上 | 长 context 时下降 |
| 4 | Tool 执行 | 0.92 | 上游 API 历史 | 限流 / 5xx |
| 5 | LLM 合成 | 0.88 | 估算 | 忽略工具返回 |

### 端到端正确率
- 独立假设：0.95 × 0.85 × 0.80 × 0.92 × 0.88 ≈ **0.523**
- 非独立修正（有 fallback）：<估算>
- **悲观 / 乐观区间**：[0.45, 0.65]

### Gate 插入点
| 位置 | 类型 | 预期 p_i 提升 | 成本 | 延迟 |
|---|---|---|---|---|
| Step 2 后 | Retrieval 对照 | 0.85 → 0.93 | +$0.001 | +200ms |
| Step 3 后 | LLM judge | 0.80 → 0.89 | +$0.003 | +500ms |
| Step 5 后 | Assertion | 0.88 → 0.95 | 近零 | 近零 |

### Gate 后端到端
- 新 p: 0.95 × 0.93 × 0.89 × 0.92 × 0.95 ≈ **0.687**
- 提升：+16 个百分点
- 代价：+$0.004/req + 700ms

### 失效放大分析
**场景 1**：RAG 错 → 生成错 → Tool 验证只校语法不校语义 → 用户得到错答
- 起点：Step 2（15% 概率，即 1 − 0.85）
- 放大路径：Step 3 错 → Step 4 "通过" → Step 5 合理化
- 缓解：Step 2 加 retrieval gate；Step 4 改用语义验证

### Step 预算（硬上限）
- 延迟预算 30s → max N = 10 step
- 成本预算 $1/req → max M = 15 step
- Token 预算 200k → max = 按业务调
- **min(延迟, 成本, token) = 10 step**，超过必截断

### Rollback 与降级
- Agent 跑飞硬上限：step > 10 / 时长 > 30s / 成本 > $1
- 降级：切到 FAQ / 人工

### 红队发现（至少 3 条）
1. 输入超长时会怎样？
2. Tool 所依赖的外部 API 慢 / 挂时会怎样？
3. 模型升级 p_3 从 0.80 变 0.70 时整个链路变什么样？
````

---

## 模板 6 · 数值级故障 Runbook

**来源**：[第 10 章](../知识/09-工程底座.md)、[科学 03](../科学/03-Quantization为什么有时坏.md)、[Unit 5 · Week 2](../练习/Unit5-数值与编译器级调试/Week2-Runbook产出.md)

````markdown
## <服务名> · 数值级故障排查 Runbook

### 触发条件（on-call 5 秒扫）
满足 2 条以上走本 runbook：
- [ ] 可用性正常 + 延迟正常 + **质量明显降**
- [ ] 按任务类型分桶的 L2 均分一个类掉 > 1.5-2 分，或跌出该类近 30 天波动带（p5）
- [ ] 输出长度分布突变
- [ ] 数字/结构化输出错误率涨 3×+
- [ ] 最近有硬件换 / CUDA 升级 / 量化变化 / kernel 库升级
- [ ] 长 context 劣化比短 context 严重

### 分层 Triage
```
质量降了？
├─ 最近有变更？
│  └─ 有 → 先 rollback 再分析
├─ 跨任务类型都降？
│  └─ 是 → 模型 / kernel 层问题
├─ 某类任务专门崩？
│  └─ 是 → Outlier / Quantization
├─ 长 context 专门差？
│  └─ 是 → KV cache / attention 精度
└─ 某 batch size 才差？
   └─ 是 → Kernel 非确定性 / padding
```

### 诊断命令集

**A. bf16 vs fp32 差异**
```bash
python scripts/test_precision.py \
  --model $MODEL --samples golden.jsonl
# 看哪类 sample bf16 vs fp32 输出不一致
```

**B. Kernel 确定性**
```bash
python scripts/test_determinism.py \
  --prompt "..." --runs 10 --batch-sizes 1,4,16
# 全一致 = OK；有分歧 = kernel 问题
```

**C. 量化漂移**
```bash
python scripts/test_quantization.py \
  --quant int4 --reference bf16 --tasks task_A,task_B,task_C
# 按任务类型分桶看分差
```

**D. 版本 pin**
```bash
pip freeze | grep -E "torch|transformers|flash-attn|vllm|cuda"
# 和已知稳定 baseline 对比
```

### 根因库
| 症状 | 可能根因 | 验证 | 缓解 |
|---|---|---|---|
| 某类精细数字错 | Quantization outlier | 命令 C | 换 AWQ / 该类独立 pool |
| 长 context 偶发乱码 | Softmax 数值溢出 | 命令 A 长 prompt | 关长 ctx / 用 fp32 softmax |
| Batch size 差异导致结果不同 | Kernel 非确定 + padding | 命令 B | Pin kernel / 固定 batch |
| 版本升级后质量变 | Kernel 语义变 | 命令 D | 回退到稳定版本 |
| 模型版本切换后细微差 | bf16 累积差 | 命令 A | 关键任务走 fp32 |

### Fallback 策略
- 退回上一版 kernel / PyTorch / CUDA
- 临时切全精度（贵但可控）
- 受影响任务路由到稳定 pool
- 定期发 status update 让业务知道在修

### Postmortem 必填
- 症状起点时间
- 首次报警时间（差 = 检测盲区）
- 定位耗时
- 根因层级（应用 / kernel / CUDA / 硬件）
- Action items（监控 / 流程 / 工具）
````

---

## 模板 7 · Postmortem

**AI 相关事故专用**（对标 Google SRE Book postmortem，加 AI 特有字段）

```markdown
## Postmortem · <事件名> · <YYYY-MM-DD>

### 摘要
一句话说清楚发生了什么、影响多大、多久修复。

### 影响
- 受影响用户数 / 请求数
- 持续时长
- 估算业务损失（金额 / 声誉）

### 时间线（UTC）
| 时间 | 事件 |
|---|---|
| T-1h | ... 变更部署 |
| T0 | 首个用户报告 |
| T+5 | 告警触发 |
| T+15 | 人工确认 + 触发 IC |
| T+30 | 初步定位 |
| T+45 | Rollback 启动 |
| T+60 | 恢复确认 |

### 根因
- **直接触发**：XX 改动 / 上游变化
- **深层原因**：为什么我们的 gate 没挡住？
- **AI 相关因素**：涉及哪些 AI 特有机制
  - [ ] Prompt injection（[深入 07](../深入/07-Agent-Prompt-Injection红队实战.md)）
  - [ ] Silent quality regression（[深入 10 · Pattern 1](../深入/10-AI系统事故模式库.md)）
  - [ ] Cache miss storm（Pattern 2）
  - [ ] Cost explosion（Pattern 7）
  - [ ] 其他 Pattern：<填>

### 为什么我们的 eval / 监控没早发现
- 监控盲区是什么
- Eval 为什么漏了

### 为什么修复花了 <N> 分钟
- 定位慢在哪一步
- 工具 / runbook 有没有帮上忙
- 组织协作障碍

### 对照 [深入 10 事故模式](../深入/10-AI系统事故模式库.md)
- Pattern <X>：<描述>
- 本事件是否揭示了**新 pattern**？（是 → 提议加入书）

### Action Items
| 类别 | 行动项 | Owner | Due |
|---|---|---|---|
| 监控 | 加 <指标> | SRE | ... |
| 流程 | 变更审批加 <step> | ... | ... |
| 工具 | 补 <能力> | ... | ... |
| 文档 | 更新 runbook | ... | ... |
| 训练 | 做一次 tabletop | IC | ... |

### 预防类似事件
- 如果重来一次，**第一道防线**应该是什么？
- 能否**自动化检测 + 自动 rollback**这类事件？
- 组织 / 文化层面需要什么改变？

### Blameless 声明
本 postmortem 遵循 blameless 原则：**重点是系统如何失败，不是谁出了错**。任何人在同样 context 下都可能做同样决定。
```

---

## 模板 8 · 贯穿项目 README（SRE 事故助手）

**来源**：[🛠️ 贯穿项目 · SRE 事故助手](../练习/贯穿项目-SRE事故助手.md)

给项目 repo 的 `README.md` 用。每个 Unit 结束都应**更新"当前状态"** 节——这是 Capstone 的天然雏形。

````markdown
# SRE 事故助手（RAG + Tool-use Agent）

基于《AI 时代的可靠性架构》贯穿项目。本项目**不是玩具**，是作者学习 AI 可靠性架构的实战载体。

## 项目目标

接收事故描述 / 日志 / metrics，检索 runbook 与历史事故，生成带来源的结构化排查建议。
**只读**，不自动执行生产变更。

## 当前状态（Unit N / 2026-MM-DD）

> 每完成一个 Unit 更新此节。

- ✅ Unit 0：最小 CLI + RAG + tool use
- ✅ Unit 1：权限白名单 + Trifecta 分析 + 红队
- ⏳ Unit 2：Trace-Eval 一体化（进行中）
- ⬜ Unit 3：SLO / 容量 / 灰度
- ⬜ Unit 4：Step 预算 / Verifier
- ⬜ Unit 5：数值 Runbook
- ⬜ Capstone：AI 可靠性架构评审包

## 如何运行

```bash
# 安装
pip install -e .
cp .env.example .env  # 填 ANTHROPIC_API_KEY 等

# Ingest runbook 到向量库
python -m app.ingest data/runbooks/

# 跑一个问题
python -m app.agent "生产数据库 CPU 100% 怎么排查？"

# 跑 smoke eval
python -m app.eval data/eval/smoke.jsonl
```

## 数据来源

- `data/runbooks/` — <N> 条（来源：<脱敏的公司 / Google SRE Book / 公开 postmortem>）
- `data/eval/smoke.jsonl` — <N> 条冒烟测试
- `data/eval/gold.jsonl` — <N> 条（Unit 2 后）

## 工具权限

| Tool | 类型 | 授权 | 备注 |
|---|---|---|---|
| grep_logs | 只读 | auto | 日志目录白名单 |
| read_runbook | 只读 | auto | `data/runbooks/` 下 |
| query_metrics | 只读 | auto | mock 数据 |
| run_shell | 只读 | confirm | 白名单命令 |

（Forbidden：任何写入 / 对外网络请求）

## Trace / Eval 状态

- Trace 存储：`traces/*.jsonl`
- Eval pipeline：`app/eval.py`
- Judge 校准：最近一次 <YYYY-MM-DD>，Cohen's κ = <X>

## 当前 SLO（摘自 docs/slo.md）

- TTFT p99 < <N>s
- tokens/s p50 > <N>
- L1 assertion 通过率 > <X>%
- Cache hit rate > <X>%

## 已知风险

1. <第一条风险，对应深入 10 · Pattern X>
2. <...>
3. <...>

## 相关文档

- [架构评审](docs/architecture-review.md)
- [威胁模型](docs/threat-model.md)
- [SLO](docs/slo.md)
- [数值级 Runbook](docs/runbook-numeric.md)
- [Step 预算](docs/step-budget.md)

## 免责

本项目使用的 runbook 和 postmortem **已脱敏**。模型定价 / 能力**截至 <YYYY-MM>**，实际以厂商官方为准。
````

---

## 模板 9 · AI 生产就绪一页评审

**来源**：[深入 11 · AI SRE 现实图谱](../深入/11-AI-SRE现实图谱.md)、[Capstone](../练习/Capstone-AI生产架构评审包.md)

用于任何准备进入生产、扩大灰度或提升自治等级的 AI 系统。目标不是写漂亮文档，而是让团队在 30 分钟内看清：**这套系统能不能控、坏了能不能退、谁负责修**。

```markdown
## AI 生产就绪一页评审 · <系统名>

### 1. 系统定位
- 当前自治等级：L0 / L1 / L2 / L3 / L4
- 目标用户：<内部 / 外部 / on-call / 客服 / 开发者>
- 主要任务：<一句话>
- 明确不做：<三条边界>

### 2. 动作与权限
| 动作 | 当前是否允许 | 授权方式 | Blast radius | 回滚方式 |
|---|---|---|---|---|
| 读取 runbook | 是 | auto | 低 | 无需 |
| 查询指标 | 是 | auto | 低 | 无需 |
| 创建工单草稿 | 是 | auto / confirm | 中 | 删除草稿 |
| 修改生产配置 | 否 | forbidden | 高 | N/A |

### 3. 数据与知识
- 输入敏感数据：<PII / secrets / logs / tickets>
- RAG 权限策略：<按用户 / 团队 / 文档级>
- 文档过期策略：<过期时间 + owner>
- 召回失败策略：<拒答 / 转人工 / 降级搜索>

### 4. SLO 与 Guardrails
| 类别 | 指标 | 目标 | 报警 |
|---|---|---|---|
| 服务 | TTFT p99 | <N>s | > <N>s |
| 服务 | tokens/s p50 | > <N> | < <N> |
| 质量 | L1 assertion 通过率 | > <X>% | < <X>% |
| 质量 | 引用支持率 | > <X>% | < <X>% |
| 安全 | 越权召回率 | 0 | 任意出现 |
| 成本 | 单请求 p95 成本 | < $<N> | > $<N> |

### 5. Eval 与发布
- Eval 集规模：<N> 条，覆盖 <任务类型>
- 线上 trace 抽样：<X>%
- Judge-human 校准：最近 <YYYY-MM-DD>，κ / agreement = <X>
- 发布前回放：最近 <N> 条真实流量
- 回滚耗时目标：<N> 分钟

### 6. 事故模式对照
| Pattern | 本系统暴露面 | 当前防线 | 缺口 |
|---|---|---|---|
| Silent quality regression | <高/中/低> | canary eval | <...> |
| Cache miss storm | <高/中/低> | cache hit SLI | <...> |
| Tool result poisoning | <高/中/低> | data/instruction 隔离 | <...> |
| Cost explosion | <高/中/低> | step / token budget | <...> |
| PII leakage | <高/中/低> | redaction | <...> |

### 7. 责任人
| 资产 / 流程 | Owner | Backup | 检查频率 |
|---|---|---|---|
| Prompt 版本 | <name> | <name> | 每次发布 |
| RAG 知识库 | <name> | <name> | 每周 |
| Gold set | <name> | <name> | 每月 |
| Eval pipeline uptime | <name> | <name> | 实时 |
| 事故暂停自动化权限 | <role> | <role> | 每次演练 |

### 8. Go / No-Go
- Go 条件：<列出必须满足项>
- No-Go 条件：<列出一票否决项>
- 本次结论：Go / Conditional Go / Defer / No-Go
    - **Go**：可上线
    - **Conditional Go**：可上线，但需满足 P0 条件并按到期时间复查
    - **Defer**：技术上可行但当前不是上线时机（业务优先级 / 资源 / 时间窗口），回到 PRD 重新评估
    - **No-Go**：技术架构问题，需重新设计后再评审
- Conditional Go 的到期复查时间：<YYYY-MM-DD>
- Defer 的重评时间：<YYYY-MM-DD>
```

---

## 使用这些模板的原则

> [!TIP]
> 1. **别原样交差**：模板是骨架，必须用你**系统的真实信息**填肉。照搬模板 = reward hacking。
>
> 2. **数字不可以留空**：`<N>` 占位必须换成真实数字。没有数据就写"估算，依据 X"——不写数字等于没填。
>
> 3. **引用本书章节**：模板里的 `[深入 XX]` 等链接**保留**，这让你的产出可溯源，评审时有参考。
>
> 4. **对照 [Capstone](../练习/Capstone-AI生产架构评审包.md) 使用**：Capstone 的 15 节里，6 节可以直接拼这些模板。

---

## 模板版本控制

| 模板 | 最近更新 | 对应章节版本 |
|---|---|---|
| 1 Trace-Eval | 2026-07-04 | 深入 06 v2 |
| 2 三层 Eval | 2026-07-04 | 深入 06 v2 / Unit 2 W2 v1 |
| 3 推理 SLO | 2026-05-05 | Unit 3 W1 v1 |
| 4 容量规划 | 2026-05-05 | 深入 05 v1 |
| 5 复合可靠性 | 2026-05-05 | Unit 4 v1 |
| 6 数值 Runbook | 2026-05-05 | Unit 5 W2 v1 |
| 7 Postmortem | 2026-05-05 | 深入 10 v1 |
| 8 贯穿项目 README | 2026-05-05 | 贯穿项目 v1 |
| 9 AI 生产就绪评审 | 2026-05-10 | 深入 11 v1 |

书的对应章节变动时，**本附录同步**（见 [漂移度表](../维护/漂移度表.md)）。

---

[← 附录 D](D-厂商官方学习资源.md)  ·  [📖 总目录](../README.md)
