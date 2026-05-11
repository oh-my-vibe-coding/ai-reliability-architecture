---
title: 科学 01 · Attention 与 Transformer 的 SRE 视角
updated: 2026-05-05
tags: [science, transformer, attention, mechanism]
---

# 科学 01 · Attention 与 Transformer 的 SRE 视角

> [← 返回目录](../README.md)  ·  相关：[深入 01 · TTFT 与吞吐](../深入/01-首包延迟与吞吐的影响因素.md)  ·  [深入 05 · 容量规划](../深入/05-LLM推理服务的容量规划.md)

> [!NOTE]
> 这一章的目的：让你建立 **"attention 在硬件上发生了什么"** 的直觉。不推导公式，不证明定理，只讲 **SRE 为了做好工程判断必须知道的机制**。

---

## 0. 为什么 SRE 要懂 Attention

不懂：
- "1M context" 为什么实际不能全用 → 你只知道"结论"
- 为什么 GQA 能省 KV cache → 你只会"跟潮流"
- 为什么 DeepSeek sparse attention 省显存 → 你无法判断类似声明
- Attention 数值出问题会怎样 → 你调试不到这层

懂了之后：
- 能**预测**新硬件、新架构能带来多少收益
- 能**解释**为什么同样模型不同部署差这么多
- 能**调试**别人挖不下去的性能问题

---

## 1. 一句话本质

> Transformer 模型每一层的核心操作是 **"让每个位置去看它该看的位置"**——这就是 attention。

具体来说：对于序列中每个位置 $i$，模型要决定：**"应该在多大程度上参考位置 $j$ 的信息？"**

答案是一个权重矩阵 $A_{ij}$——我们称之为**注意力矩阵**。

---

## 2. Self-Attention 的机制（简化版）

### 2.1 三个角色：Query / Key / Value

每个 token 在每一层都被映射成三个向量：

| 角色 | 作用 | 类比 |
|---|---|---|
| **Q (Query)** | "我在找什么？" | 搜索框输入 |
| **K (Key)** | "我是什么？" | 文档的关键词 |
| **V (Value)** | "我携带的信息" | 文档实际内容 |

### 2.2 核心操作（简化公式）

```
attention(Q, K, V) = softmax(Q · K^T / √d) · V
```

直观理解：
1. `Q · K^T`：让 Query 和每个 Key 算相似度 → 得到 N×N 矩阵
2. `/√d`：缩放防止数值爆炸
3. `softmax`：归一化成"注意力分布"
4. `· V`：按注意力分布加权求和 Value

**结果**：每个位置得到"参考了其他所有位置的新向量"。

#### 示意图（单层 attention）

```
输入: [tok1, tok2, tok3, ... tokN]
            │
            ├──► 投影 W_Q ──► Q: [N × d]
            ├──► 投影 W_K ──► K: [N × d]
            └──► 投影 W_V ──► V: [N × d]
                    │
                    ▼
        QKᵀ/√d    → 相似度矩阵 [N × N]
                    │
                    ▼
          softmax → 注意力分布  [N × N]  （每行和为 1）
                    │
                    ▼
            × V   → 输出       [N × d]
```

**N×N 那个矩阵**就是 O(N²) 成本的来源——长 context 贵的物理根因。

### 2.3 这是 O(n²) 操作

N 个位置互相算相似度 → **N² 个相似度值**。

- 序列长度 1k：1M 次相似度计算
- 序列长度 128k：**16 Billion** 次
- 序列长度 1M：**1 Trillion** 次

这就是 **"长 context 贵"的物理根因**。

---

## 3. Prefill vs Decode 在 Attention 上发生了什么

### Prefill 阶段（输入处理）

- 输入 N 个 token
- **一次性**计算所有位置的 Q, K, V → N×d 三个矩阵
- **一次性**算 attention → N×N 矩阵
- 存下 K, V（这就是 KV cache 的来源）

```
计算量：N² × d  （主要成本）
内存写：2 × N × d × 层数  （KV cache）
```

**特性**：大矩阵乘法，**GPU 算力打满** → Compute-bound

### Decode 阶段（逐 token 生成）

- 当前已有 N 个 token
- 生成第 N+1 个 token
- **只算当前位置**的 Q（1×d）
- 和**全部历史 K**（N×d）做 attention → 得到 1×N attention 分布
- 加权 V → 新 token 的向量

```
计算量：N × d  （小！）
内存读：整个模型参数 + 整个 KV cache
```

**特性**：计算量小，但要读巨量数据 → **Memory-bandwidth-bound**

> [!IMPORTANT]
> **这就是为什么[深入 01](../深入/01-首包延迟与吞吐的影响因素.md) 说 prefill 和 decode 的瓶颈根本不同**——它们在 attention 层做的事情**量级完全不同**。

---

## 4. KV Cache 为什么能存（节省 99% 计算）

观察一件事：**每生成新 token 时，历史 token 的 K 和 V 完全不变**。

证明直觉：K 和 V 是由 token 本身和它前面的上下文决定的；新 token 加进来不改变它们的历史位置。

**所以：K 和 V 只算一次，存下来，之后 decode 全部复用**。

如果不缓存：
- 每生成一个 token 要重新 prefill 一次
- 1000 个输出 token = 1000 次 O(N²) 重算
- **完全不可用**

缓存后：
- 每生成一个 token = 1 次 O(N) 读
- 显存空间换计算时间

> [!TIP]
> **Prompt Caching（[深入 02](../深入/02-Prompt-Caching原理.md)）就是把 KV cache 的生命周期从"单次对话"延长到"跨请求"**。原理完全一样。

---

## 5. Multi-Head Attention 和 GQA

### Multi-Head：不同"视角"并行

单个 attention 只能学一种关联（比如语法关联）。Multi-Head 让模型**同时从多个角度看**：

- Head 1 学语法关联
- Head 2 学语义相似
- Head 3 学共指（"它"指代什么）
- Head N ...

**代价**：N 个 head 就有 N 份 K 和 V → KV cache 大 N 倍。

### GQA：让多个 Q head 共享一组 KV

**关键观察**：Q 差异要大（每个 head 看不同东西），但 **K 和 V 可以少一些**。

GQA（Grouped Query Attention）：
- 保留 64 个 Q head
- 但只有 8 个 K、V head（8 个 Q 共享一组 KV）
- **KV cache 减 8 倍**

**SRE 含义**：

| 模型 | KV head 数 | 相对 KV cache |
|---|---|---|
| 传统 MHA（64 heads）| 64 | 1.0× |
| GQA（KV=8）| 8 | **0.125×** |
| MQA（KV=1）| 1 | 0.016× |

现代模型（Llama 3、Mistral、Qwen、DeepSeek）**几乎全用 GQA**——这是容量规划[深入 05](../深入/05-LLM推理服务的容量规划.md) 的前提。

---

## 6. 新变种：SRE 该知道的进化

### Sliding Window Attention（Mistral）
每个位置**只看最近 W 个位置**，不是全部。把 O(N²) 降到 O(N·W)。
- **好处**：长 context 计算量线性而非平方
- **代价**：远距离信息丢失
- **SRE 含义**：Mistral 的"无限 context"有代价；评估长 context 任务时实测必要

### Sparse Attention（DeepSeek V3.2）
动态选择"哪些位置值得注意"，只算选中的。
- **好处**：长 context 省显存省算力
- **代价**：需要好的选择器（否则丢重要信息）
- **SRE 含义**：便宜的长 context 开始成为现实，但要做自己的 eval

### Attention Sink
保留前几个 token（"起始锚点"）永远关注，中间做 sliding。
- **好处**：长对话保持"记忆起点"
- **SRE 含义**：解释了为什么"system prompt 放最前"除了 caching 外还有 attention 理由

---

## 7. Attention 为什么会数值出问题

SRE 必须知道的故障面：

### 7.1 Softmax 数值稳定性

`softmax(x)` 里有 `e^x`。如果 x 很大（比如 attention score 飙到 80），`e^80` 溢出。

**实现上**：要做 `x - max(x)` 保护 → 这个"减 max"操作在 FlashAttention、bf16 实现里**可能出 bug**。

Anthropic 2026 年初的事故就有一部分属于此类——**kernel 实现出 bug 了，softmax 变成近似 argmax，输出质量悄悄降**。

### 7.2 bf16 vs fp32 的精度损失

Attention 矩阵乘的中间结果如果用 bf16，在**极端长 context + 极端 attention 分布**时会损失精度。

**症状**：
- 短 context 全对
- 长 context 质量劣化
- 但指标全绿

**对抗**：关键算子强制 fp32 累加；做数值 eval。

### 7.3 Kernel 非确定性

CUDA kernel 在**不同 batch size、不同 padding** 下可能走不同的代码路径，结果有微小差异。累积在深层可能放大。

**SRE 要做的**：
- 生产固定 kernel 版本（pin PyTorch / CUDA / FlashAttention 版本）
- 灰度发布 kernel 升级前做数值回归测试

---

## 8. SRE 可以观测的信号

| 信号 | 说明 | 异常含义 |
|---|---|---|
| **Attention kernel 吞吐** (TFLOPS) | 由 GPU profiler 给 | 突降 → kernel 退化 |
| **KV cache 压缩比** | 期望 vs 实际占用 | 突高 → GQA 配置被改或失效 |
| **Per-layer attention entropy** | 可选高级指标 | 突降至接近 0 → softmax 坏了（argmax-like） |
| **长 context 质量曲线** | eval vs context 长度 | 尾部塌陷 → kernel / 数值问题 |

---

## 9. SRE 的实操清单

- [ ] 理解你部署模型的 **KV head 配置**（GQA group size）
- [ ] 知道单个请求的 **KV cache 大小**（见[深入 05](../深入/05-LLM推理服务的容量规划.md) 公式）
- [ ] 知道你用的是标准 MHA、GQA、Sliding Window、还是 Sparse
- [ ] Pin 推理引擎版本（vLLM / SGLang / TGI 的小版本）
- [ ] 有长 context 专门 eval（不只是 100k 单针的"needle"，要多针多跳）
- [ ] 升级 CUDA / PyTorch / FlashAttention 前做数值回归测试

---

## 10. 给 SRE 的一句话总结

> [!IMPORTANT]
> Attention 的两件事你要刻在脑子里：
>
> 1. **O(N²) 是本质**——长 context 的成本没法消除，只能用新架构（sliding/sparse）绕开，每种绕法都有代价。
> 2. **K/V 在历史上不变**——这是 KV cache、Prompt Caching、prefix sharing 的共同物理基础。
>
> 懂这两件，[深入 01/02/05] 里的工程决策就不再是"记忆"，而是"推理"。

---

## 11. 参考资料

- Vaswani et al · 《Attention is All You Need》(2017) — https://arxiv.org/abs/1706.03762
- Ainslie et al · 《GQA: Training Generalized Multi-Query Transformer》(2023) — https://arxiv.org/abs/2305.13245
- Dao · 《FlashAttention-2》(2023) — https://arxiv.org/abs/2307.08691
- Xiao et al · 《Efficient Streaming LLMs with Attention Sinks》(2023) — https://arxiv.org/abs/2309.17453
- Jiang et al · 《Mistral 7B (Sliding Window Attention)》(2023) — https://arxiv.org/abs/2310.06825
- DeepSeek · V3.2 Technical Report (sparse attention) — https://github.com/deepseek-ai/DeepSeek-V3
- Horace He · 《Making Deep Learning Go Brrrr From First Principles》— https://horace.io/brrr_intro.html

---

[📖 目录](../README.md)  ·  [科学 02 · "Lost in the Middle" 为什么会发生 →](02-Lost-in-the-Middle.md)
