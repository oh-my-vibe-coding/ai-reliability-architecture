"""
07-canary-check.py
---
Canary token 污染检测：检查训练数据是否泄漏了 eval set。

演示：
- N-gram 匹配检测 contamination
- Canary token 方法
- 规模化处理的简化版

对应章节：共同语言 02 · Data 是 ML 的真正核心
"""

import hashlib
import random
import string
from collections import Counter


# ---- 方法 1: N-gram Contamination Check ----


def get_ngrams(text: str, n: int = 13) -> set[str]:
    """生成词级 n-gram"""
    words = text.split()
    if len(words) < n:
        return set()
    return {" ".join(words[i : i + n]) for i in range(len(words) - n + 1)}


def check_ngram_contamination(
    eval_samples: list[str], training_corpus_sample: list[str], n: int = 13
) -> dict:
    """
    检查 eval 样本是否在训练数据里出现过 n-gram 级重合。

    返回：{sample_id: [matched_ngrams]}
    """
    training_ngrams: Counter = Counter()
    for doc in training_corpus_sample:
        training_ngrams.update(get_ngrams(doc, n))

    contamination = {}
    for i, sample in enumerate(eval_samples):
        sample_ngrams = get_ngrams(sample, n)
        matches = sample_ngrams & set(training_ngrams.keys())
        if matches:
            contamination[i] = list(matches)
    return contamination


# ---- 方法 2: Canary Token 检测 ----


def generate_canary(seed: str = None) -> str:
    """生成一个独特、不太可能自然产生的字符串"""
    if seed:
        random.seed(seed)
    # 用 Unicode 不常见字符 + hash 伪随机
    random_suffix = "".join(random.choices(string.ascii_letters + string.digits, k=16))
    canary = f"CANARY_TOKEN_♠_{random_suffix}_♣_{hashlib.md5(random_suffix.encode()).hexdigest()[:8]}"
    return canary


def embed_canaries_in_eval(eval_samples: list[dict]) -> list[dict]:
    """在每个 eval 样本里嵌入一个 canary（供后续检测模型记住与否）"""
    result = []
    for sample in eval_samples:
        canary = generate_canary(seed=str(sample["id"]))
        # 混入样本末尾或 metadata
        new_sample = {**sample, "_canary": canary}
        # 实际使用中，canary 应该在"eval 完整发布"之前就嵌进去
        result.append(new_sample)
    return result


def check_model_memorized_canary(
    model_output: str, canaries: list[str]
) -> list[str]:
    """检查模型输出是否"记得"canary（意味着训练时看到了）"""
    return [c for c in canaries if c in model_output]


# ---- 方法 3: Exact match check（最简单）----


def exact_match_check(
    eval_samples: list[str], training_corpus: list[str]
) -> list[int]:
    """找出完全出现在训练数据里的 eval 样本"""
    training_set = set(doc.strip() for doc in training_corpus)
    return [i for i, sample in enumerate(eval_samples) if sample.strip() in training_set]


# ---- 演示 ----

if __name__ == "__main__":
    # 模拟数据
    eval_samples = [
        "What is the boiling point of water at sea level in Celsius degrees?",
        "The quick brown fox jumps over the lazy dog many times in training data",
        "Calculate the derivative of x squared with respect to x.",
    ]

    training_corpus = [
        "Water boils at 100 degrees Celsius at sea level. This is a fundamental fact.",
        "The quick brown fox jumps over the lazy dog many times in training data",  # 完全泄漏
        "Calculus is important. The derivative of x^2 is 2x...",
    ]

    # 1. Exact match
    exact_matches = exact_match_check(eval_samples, training_corpus)
    print(f"\n=== Exact matches ===")
    for i in exact_matches:
        print(f"  Sample #{i}: {eval_samples[i][:80]}")

    # 2. N-gram check
    ngram_contam = check_ngram_contamination(eval_samples, training_corpus, n=10)
    print(f"\n=== N-gram contamination (n=10) ===")
    for idx, matches in ngram_contam.items():
        print(f"  Sample #{idx}: {len(matches)} matching n-grams")
        for m in matches[:2]:
            print(f"    - \"{m}\"")

    # 3. Canary
    canary = generate_canary(seed="example")
    print(f"\n=== Example canary ===")
    print(f"  {canary}")
    print("  Embed this in your private eval set.")
    print("  Later test: does the trained model output it when prompted?")

    # ---- 生产上规模化 ----
    # 1. 训练数据可达 TB 级，扫描用 Spark + Bloom Filter
    # 2. Bloom filter 先粗筛，命中再精确检查
    # 3. 多 n 值同时做（n=8, 13, 20）
    # 4. Canary 要每个 version 独立，便于追溯泄漏发生的时点
    # 5. 和 ML 团队约定：eval 集发布后不再加入训练（流程保证）
    # 6. 内部 held-out eval 从不发布（Anthropic、OpenAI 都这么做）
