"""
03-local-rag.py
---
本地 RAG：SQLite + sqlite-vec + Claude。
不依赖任何云向量数据库。

演示：
- 文档切片、embedding、存储
- 向量检索
- 检索 → 拼 prompt → 生成（带引用）

对应章节：Unit 0 · Week 2 · 本地 RAG
"""

import sqlite3
import sqlite_vec
from openai import OpenAI
from anthropic import Anthropic

openai_client = OpenAI()  # OPENAI_API_KEY
claude = Anthropic()

EMBEDDING_MODEL = "text-embedding-3-small"  # 1536-d
CHAT_MODEL = "claude-sonnet-4-6"


# ---- 1. 初始化 DB ----


def init_db(path: str = "rag.db"):
    conn = sqlite3.connect(path)
    conn.enable_load_extension(True)
    sqlite_vec.load(conn)
    conn.enable_load_extension(False)

    cursor = conn.cursor()
    # vec0 表：固定维度的向量
    cursor.execute(
        "CREATE VIRTUAL TABLE IF NOT EXISTS chunks USING vec0(embedding float[1536])"
    )
    # 配套元数据表
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS chunk_meta (
            id INTEGER PRIMARY KEY,
            source TEXT,
            content TEXT
        )
        """
    )
    conn.commit()
    return conn


# ---- 2. Chunking（简单版）----


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 100) -> list[str]:
    """按字数切片（生产场景建议按 token 或段落）"""
    chunks = []
    i = 0
    while i < len(text):
        chunks.append(text[i : i + chunk_size])
        i += chunk_size - overlap
    return chunks


# ---- 3. Embedding ----


def embed(texts: list[str]) -> list[list[float]]:
    """批量 embed"""
    response = openai_client.embeddings.create(model=EMBEDDING_MODEL, input=texts)
    return [d.embedding for d in response.data]


# ---- 4. Ingest 文档 ----


def ingest(conn, source: str, text: str):
    chunks = chunk_text(text)
    embeddings = embed(chunks)

    cursor = conn.cursor()
    for chunk, emb in zip(chunks, embeddings):
        # 先存元数据
        cursor.execute(
            "INSERT INTO chunk_meta (source, content) VALUES (?, ?)", (source, chunk)
        )
        chunk_id = cursor.lastrowid
        # 再存向量（用相同 id）
        cursor.execute(
            "INSERT INTO chunks (rowid, embedding) VALUES (?, ?)",
            (chunk_id, sqlite_vec.serialize_float32(emb)),
        )
    conn.commit()
    print(f"Ingested {len(chunks)} chunks from {source}")


# ---- 5. 检索 ----


def retrieve(conn, query: str, k: int = 5) -> list[dict]:
    query_emb = embed([query])[0]

    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT chunk_meta.id, chunk_meta.source, chunk_meta.content, distance
        FROM chunks
        JOIN chunk_meta ON chunk_meta.id = chunks.rowid
        WHERE embedding MATCH ?
        ORDER BY distance
        LIMIT ?
        """,
        (sqlite_vec.serialize_float32(query_emb), k),
    )
    return [
        {"id": row[0], "source": row[1], "content": row[2], "distance": row[3]}
        for row in cursor.fetchall()
    ]


# ---- 6. 生成回答（强制引用）----


def answer(conn, query: str, k: int = 5) -> str:
    results = retrieve(conn, query, k)
    if not results:
        return "没有在知识库中找到相关内容。"

    context_text = "\n\n".join(
        [
            f"[来源 #{i+1}: {r['source']}]\n{r['content']}"
            for i, r in enumerate(results)
        ]
    )

    prompt = f"""基于以下文档片段回答问题。规则：
1. 只使用提供的文档内容
2. 每个结论必须标注来源编号（如 [#1]）
3. 如果文档里没有答案，直接说"文档里没有"

文档：
{context_text}

问题：{query}

回答："""

    response = claude.messages.create(
        model=CHAT_MODEL,
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text


# ---- 7. 演示 ----

if __name__ == "__main__":
    conn = init_db("/tmp/rag.db")

    # 假设我们有一些 runbook
    runbook = """
    # 磁盘告警处理 Runbook

    当收到磁盘使用率 > 90% 告警时：
    1. 先确认告警真实性：df -h 查看实际使用
    2. 清理最大的日志：find /var/log -name "*.log" -size +1G
    3. 老日志归档到 S3：参考 scripts/archive-logs.sh
    4. 仍然不够的话，扩容 EBS volume

    # CPU 告警处理 Runbook

    CPU > 80% 持续 5 分钟：
    1. top -o %CPU 找出 top 进程
    2. 检查是不是 runaway process
    3. 联系业务 owner 确认
    4. 必要时 kill -TERM（不要 kill -9 除非紧急）
    """

    ingest(conn, "ops-runbook.md", runbook)

    print("\n=== 查询 1 ===")
    print(answer(conn, "磁盘满了怎么办？"))

    print("\n=== 查询 2 ===")
    print(answer(conn, "如何扩容网络带宽？"))  # 文档里没有，看它会不会诚实说"没"

    # ---- 改进方向 ----
    # 1. Chunking 按 token 而非字符
    # 2. 加 rerank 阶段（bge-reranker）
    # 3. Metadata 过滤（按 source 过滤）
    # 4. 对 embedding 做 normalization
    # 5. 批量 ingest 时做 dedup
    # 6. 加 embedding 缓存（避免重复算）
