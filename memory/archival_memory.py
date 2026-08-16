"""
Archival Memory：长期知识库，按语义相似度检索，理论上可以无限大。
对应原项目 letta/services/archive_manager.py + passage_manager.py。

原项目用云端 embedding API（OpenAI 等）把文本转成向量；本学习项目为了不依赖额外账号，
换成本地开源的 sentence-transformers 小模型来生成向量——pgvector 的存储和检索机制本身
是真实的，只是向量"从哪来"这一步换成了免费本地方案。
"""
from functools import lru_cache

from memory.db import get_connection

_MODEL_NAME = "all-MiniLM-L6-v2"  # 输出 384 维向量，体积小（约80MB），CPU 上也能跑


@lru_cache(maxsize=1)
def _get_embedder():
    # 延迟加载：只有真正调用到 archival memory 时才加载模型，加快项目启动速度
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(_MODEL_NAME)


def _embed(text: str) -> list[float]:
    vector = _get_embedder().encode(text, normalize_embeddings=True)
    return vector.tolist()


def archival_memory_insert(agent_id: str, content: str, tags: list[str] | None = None) -> str:
    embedding = _embed(content)
    with get_connection() as conn:
        row = conn.execute(
            "INSERT INTO archival_passages (agent_id, content, tags, embedding) VALUES (%s, %s, %s, %s) RETURNING id",
            (agent_id, content, tags or [], embedding),
        ).fetchone()
    return f"已存入 archival memory，编号 {row[0]}"


def archival_memory_search(agent_id: str, query: str, tags: list[str] | None = None, top_k: int = 5) -> str:
    query_embedding = _embed(query)
    with get_connection() as conn:
        if tags:
            rows = conn.execute(
                # <=> 是 pgvector 提供的"余弦距离"运算符，值越小代表越相似
                # ::vector 显式类型转换：这里 embedding <=> %s 是一个计算表达式，不像 INSERT 那样
                # 有列类型信息可以自动推断参数类型，所以要手动告诉 Postgres "%s 是个 vector"
                "SELECT content, tags, embedding <=> %s::vector AS distance FROM archival_passages "
                "WHERE agent_id = %s AND tags && %s ORDER BY distance ASC LIMIT %s",
                (query_embedding, agent_id, tags, top_k),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT content, tags, embedding <=> %s::vector AS distance FROM archival_passages "
                "WHERE agent_id = %s ORDER BY distance ASC LIMIT %s",
                (query_embedding, agent_id, top_k),
            ).fetchall()
    if not rows:
        return "archival memory 里没有找到相关内容。"
    lines = [f"(相似度距离 {r[2]:.3f}) {r[0]}" for r in rows]
    return f"找到 {len(rows)} 条相关记忆：\n" + "\n".join(lines)
