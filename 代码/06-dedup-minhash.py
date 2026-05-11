"""
06-dedup-minhash.py
---
训练数据 MinHash 去重 snippet。

演示：
- MinHash 近重复检测的工程用法
- LSH 加速查找
- 大规模处理的参考（实际上规模要上 Spark）

对应章节：共同语言 02 · Data 是 ML 的真正核心
"""

from datasketch import MinHash, MinHashLSH


# ---- 1. 创建 MinHash ----


def text_to_minhash(text: str, num_perm: int = 128) -> MinHash:
    """把文本转成 MinHash 签名"""
    m = MinHash(num_perm=num_perm)
    # 切 shingle（3-gram of chars）
    for i in range(len(text) - 2):
        shingle = text[i : i + 3]
        m.update(shingle.encode("utf-8"))
    return m


# ---- 2. LSH 近重复检测 ----


def dedup_with_lsh(
    texts: list[dict], threshold: float = 0.8
) -> list[dict]:
    """
    texts: [{"id": ..., "text": ...}]
    threshold: Jaccard 相似度阈值
    返回去重后的 texts
    """
    lsh = MinHashLSH(threshold=threshold, num_perm=128)
    result = []
    seen_hashes = {}

    for item in texts:
        m = text_to_minhash(item["text"])

        # 查找已有相似项
        neighbors = lsh.query(m)
        if neighbors:
            # 发现近重复，跳过
            original_id = neighbors[0]
            print(f"Skipping {item['id']} (similar to {original_id})")
            continue

        # 新项，加入 LSH
        lsh.insert(item["id"], m)
        seen_hashes[item["id"]] = m
        result.append(item)

    return result


# ---- 3. 精确重复（更快、先跑）----


def exact_dedup(texts: list[dict]) -> list[dict]:
    """先用 hash 去精确重复"""
    seen = set()
    result = []
    for item in texts:
        h = hash(item["text"].strip())
        if h not in seen:
            seen.add(h)
            result.append(item)
    return result


# ---- 4. 实战流程 ----


def pipeline(raw_docs: list[dict]) -> dict:
    """完整 dedup pipeline"""
    stats = {"input": len(raw_docs)}

    # Phase 1: 精确重复
    phase1 = exact_dedup(raw_docs)
    stats["after_exact"] = len(phase1)

    # Phase 2: 近重复
    phase2 = dedup_with_lsh(phase1, threshold=0.8)
    stats["after_near"] = len(phase2)

    stats["dedup_ratio"] = 1 - stats["after_near"] / stats["input"]
    return {"docs": phase2, "stats": stats}


# ---- 5. 演示 ----

if __name__ == "__main__":
    # 模拟数据：有些完全一样、有些近似
    docs = [
        {"id": 1, "text": "The quick brown fox jumps over the lazy dog"},
        {"id": 2, "text": "The quick brown fox jumps over the lazy dog"},  # 完全重复
        {"id": 3, "text": "The quick brown fox jumps over the lazy dog."},  # 近重复
        {"id": 4, "text": "A brown fox jumps over a sleepy dog"},  # 近重复
        {"id": 5, "text": "Python is a high-level programming language"},
        {"id": 6, "text": "The weather today is very nice and sunny"},
    ]

    out = pipeline(docs)
    print("\n=== Stats ===")
    for k, v in out["stats"].items():
        print(f"  {k}: {v}")

    print("\n=== Kept docs ===")
    for d in out["docs"]:
        print(f"  [{d['id']}] {d['text']}")

    # ---- 生产上规模化 ----
    # 1. 超过 1M 文档就别用单机 datasketch
    # 2. Spark + PySpark MinHashLSH
    # 3. 或者 Trafilatura + SimHash
    # 4. 写入 Parquet，中间结果 Delta Lake
    # 5. LSH 阈值要跑 sample calibration
    # 6. Shingling 可以按 word 5-gram（语义相似更好）
    # 7. 并行度 = CPU 核数 × 1-2
    # 8. 记得做 character encoding normalization (UTF-8 NFC)
