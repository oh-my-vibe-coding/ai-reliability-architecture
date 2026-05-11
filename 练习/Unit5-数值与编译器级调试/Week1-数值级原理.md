---
title: Unit 5 · Week 1 · 数值级原理 + 复现实验
updated: 2026-05-05
tags: [part-3, practice, unit5, week]
---

# Unit 5 · Week 1 · 数值级原理 + 复现实验设计

> [← Unit 5 总览](总览.md)  ·  [← 返回目录](../../README.md)

## 本周目标

从概念进入**实操**——搭一个最小复现实验，亲手看到 bf16/fp32 差异、kernel 非确定性。

## 任务清单

### 准备（15 分钟）
- [ ] 有一张能用的 GPU（本地 / 云端 / Colab 都行），或准备走下方低配替代路线
- [ ] 装 PyTorch + transformers（或 vLLM）

> [!TIP]
> **没有 GPU 的替代路径**（A-C 档仍可完成 Mastery Gate；D 档部分满足，需后续补实操）：
>
> **选项 A · Colab / Kaggle / 云 GPU**（推荐）
> - T4（16GB）更适合跑 7B 量化或小模型；bf16/full precision 建议使用 L4/A10/H100 级别资源
> - 免费额度和 GPU 型号会变化，实际以平台当天分配为准
> - URL: https://colab.research.google.com/
>
> **选项 B · 更小的模型**
> - Qwen3-1.5B / Phi-3-mini 在 MacBook 上可跑（bf16 或 int8）
> - 不够 frontier 但**足够展示数值层现象**
> - 用 `transformers` 或 `mlx`（Apple Silicon 专用，推理飞快）
>
> **选项 C · 纯 CPU toy example**
> - 跳过模型层，直接写**NumPy / PyTorch CPU 模式的 softmax 数值实验**
> - 故意构造极值触发 bf16 vs fp32 差异
> - 能完成**实验 A** 和概念学习，但**看不到端到端效应**
>
> **选项 D · 只读不做**
> - 读懂 Anthropic 事故复盘 + PyTorch determinism docs
> - 在 Week 2 的 Runbook 里**标注"本 runbook 未在 GPU 上实测"**
> - **Mastery Gate 影响**："做过真实排查"这条只算部分满足；**需要后续 on-call 或跑一次 toy 实验**补齐
>
> **优先级**：A > B > C > D。**不要因为没 GPU 就彻底跳过 Unit 5**——数值层直觉对 SRE 架构师有长期价值。

### 阅读 · B3 · 45 分钟（无 AI）

**主读**：Anthropic · 《A postmortem of three recent issues》**第四次重读**
  - **这次专注"bf16 / kernel / 数值"的那几段**
  - 理解他们如何**定位到 kernel 层面** bug

**辅读**：PyTorch · Numerical reproducibility docs
  - URL: https://pytorch.org/docs/stable/notes/randomness.html

**辅读**（10 分钟）：NVIDIA · CUDA determinism guide
  - 搜 "CUDA programming guide determinism"

**记录**：
- PyTorch 哪些操作**默认非确定**？
- `torch.use_deterministic_algorithms(True)` 会关掉哪些 kernel？
- bf16 vs fp32 在 softmax 上的数值差异直觉

### 产出 · B2 · 90-120 分钟（最少动手 60 分钟）

#### 实验 A · bf16 vs fp32 对同一 prompt 的差异

```python
# 伪代码示意
model_bf16 = load_model("llama-3-7b", dtype=torch.bfloat16)
model_fp32 = load_model("llama-3-7b", dtype=torch.float32)

prompts = [
    # 挑 20 条你自己场景的样本
]
for p in prompts:
    out_bf16 = generate(model_bf16, p, temperature=0, seed=42)
    out_fp32 = generate(model_fp32, p, temperature=0, seed=42)
    if out_bf16 != out_fp32:
        print(f"DIFF on {p[:30]}")
        # 计算 token-level 第一个不同的位置
```

**无 GPU 的简化版（选项 C）**：

```python
# 纯 NumPy / PyTorch CPU 展示 bf16 精度损失
import torch

def softmax(x, dtype):
    x = x.to(dtype)
    e = torch.exp(x - x.max())
    return e / e.sum()

# 构造极值触发 bf16 精度问题
logits = torch.tensor([[100.0, 100.0001, 50.0, 0.0]])  # 前两个接近但不同
p_fp32 = softmax(logits, torch.float32)
p_bf16 = softmax(logits, torch.bfloat16)

print(f"fp32: {p_fp32}")
print(f"bf16: {p_bf16}")
print(f"diff: {(p_fp32 - p_bf16.float()).abs().max()}")

# 观察：bf16 可能把 100.0 和 100.0001 视作相同
# 这和 attention 层的实际精度问题同源
```

**记录**：
- 完全相同的比例
- 有差异时，第一个不同 token 出现在位置 X（平均）
- 差异对最终答案的意义（语义是否一致？）

#### 实验 B · Kernel 非确定性

```python
# 同 prompt 跑 10 次，temperature=0
outputs = [generate(model, prompt, temp=0, seed=42) for _ in range(10)]
# 看是否都相同
```

**预期**：大部分情况相同，但**偶发**会不同（同一个 batch size 内）。

如果都相同，试：
- 改 batch size（单独跑 vs 凑 batch 一起跑）
- 改 padding 方式
- 开 vs 关 FlashAttention

找出**让同 prompt 输出不同**的触发条件。

**低配替代（路线 C）**：

```python
# 纯 PyTorch CPU 展示 reduce op 的非确定性
import torch

torch.use_deterministic_algorithms(False)  # 默认
x = torch.randn(1000, 1000)

results = []
for _ in range(10):
    # 某些 reduction op 在 CPU 上也可能非确定（特别是 atomic add）
    r = torch.nn.functional.softmax(x @ x.T, dim=-1).sum()
    results.append(r.item())

# 打印差异（一般 CPU 上会相同，但说明 kernel 确定性是配置出来的，不是天然的）
print(f"结果: {results}")
print(f"差异: {max(results) - min(results)}")

# 对比：开确定性模式
torch.use_deterministic_algorithms(True, warn_only=True)
# 重跑——某些 kernel 会拒绝运行（抛异常提示"no deterministic version"）
```

**意义**：即使不跑大模型，也能**亲手见证 PyTorch 哪些 op 默认非确定**——这是 runbook 里关键一节。

#### 实验 C · 长 context 的精度累积

```python
# 短 context 和长 context 的 attention 精度
short_ctx = "..." * 100 tokens
long_ctx = "..." * 50000 tokens
# 在结尾放同一个关键 instruction
# 对比两种情况的输出质量
```

**低配替代（路线 C）**：

```python
# 纯矩阵层面模拟：长序列的 softmax 累积精度损失
import torch

def simulate_attention(seq_len: int, dtype):
    # 伪 attention: Q @ K^T 后 softmax
    Q = torch.randn(1, seq_len, 64).to(dtype)
    K = torch.randn(1, seq_len, 64).to(dtype)
    scores = (Q @ K.transpose(-1, -2)) / (64 ** 0.5)
    return torch.nn.functional.softmax(scores, dim=-1)

# 对比 bf16 vs fp32 在不同序列长度下的偏差
for seq_len in [128, 1024, 8192]:
    a = simulate_attention(seq_len, torch.bfloat16).float()
    b = simulate_attention(seq_len, torch.float32)
    diff = (a - b).abs().mean()
    print(f"seq_len={seq_len}, mean abs diff = {diff:.6f}")

# 观察：seq_len 越大，bf16 的累积误差越明显
# 这就是"长 context 更容易出数值问题"的数学本质
```

**意义**：不需要 GPU 也能**定量观察**"长 context 放大精度损失"，为运维长 context 服务提供直觉。

#### Section · 观察总结（200 字）

写下：
- 你观察到的**最惊讶**的现象
- 这些现象如果在生产出现，**用现有监控能看出来吗**？
- 哪些指标应该加到 [Unit 3 · SLI](../Unit3-推理SLO与静默降级/Week1-SLI定义.md) 清单里？

### AI 挑错

**关键问题**：
- "我的实验 setup 有没有坑？（seed 没 pin、batch 没控制、采样不是真 greedy）"
- "观察到的差异能**区分**是'真的不一样'还是'测量噪声'吗？"

### 预测 · B1 · 每日 5 分钟

本周每次看 LLM 生产问题，先猜：
- "这有可能是数值级问题吗？"
- "如果是，在哪一层？"

## 周末自检

- [ ] 至少跑完**两个实验**（可以不是上面三个的其中两个）
- [ ] 记录了具体的观察
- [ ] 实验可被**重复跑**（代码 / seed / 环境都记录了）
- [ ] 能解释**生产场景下这些问题如何暴露**

**无 GPU 读者的调整自检**：
- [ ] 至少完成**实验 A 的简化版**（CPU softmax 数值差异）
- [ ] 读懂 Anthropic 事故复盘中的数值部分
- [ ] 能解释 bf16 的精度损失如何累积到端到端效应
- [ ] 在 Week 2 Runbook 里标注"未在 GPU 上实测"

**未达标的表现**：
- 只读没做实验（GPU 用户）/ 没做简化实验（CPU 用户）
- 跑了但没记录（忘了设 seed）
- 不能解释看到的差异

## 学习科学标注

- **Bloom 层级**：**应用（Apply）+ 分析（Analyze）**
- **关联章节**：[第 9 章 · 工程底座](../../知识/09-工程底座.md)、[科学 03](../../科学/03-Quantization为什么有时坏.md)

---

下一步 → [Unit 5 · Week 2 · Runbook 产出](Week2-Runbook产出.md)
