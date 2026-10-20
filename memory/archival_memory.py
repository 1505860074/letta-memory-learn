"""
Archival Memory：长期知识库，按语义相似度检索，理论上可以无限大。
对应原项目 letta/services/archive_manager.py + passage_manager.py。

原项目用云端 embedding API（OpenAI 等）把文本转成向量；本学习项目为了不依赖额外账号，
换成本地开源的 sentence-transformers 小模型来生成向量——pgvector 的存储和检索机制本身
是真实的，只是向量"从哪来"这一步换成了免费本地方案。
"""
# functools.lru_cache：标准库提供的装饰器，把函数结果缓存起来，相同参数只真正计算一次
from functools import lru_cache

from memory.db import get_connection

_MODEL_NAME = "all-MiniLM-L6-v2"  # 输出 384 维向量，体积小（约80MB），CPU 上也能跑


@lru_cache(maxsize=1)  # 缓存最近 1 次结果：这样模型只会被加载一次，之后重复调用直接复用
def _get_embedder():
    # 延迟加载：只有真正调用到 archival memory 时才加载模型，加快项目启动速度
    # sentence-transformers 第三方库：SentenceTransformer 是本地文本向量（embedding）模型
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(_MODEL_NAME)


def _embed(text: str) -> list[float]:
    # .encode(...)：SentenceTransformer 的方法，把文本编码成向量；
    # normalize_embeddings=True 表示输出归一化后的单位向量（配合余弦距离使用）
    vector = _get_embedder().encode(text, normalize_embeddings=True)
    # .tolist()：numpy 数组的方法，转成普通 Python list，psycopg 才能把它当作 vector 写入数据库
    return vector.tolist()


def archival_memory_insert(agent_id: str, content: str, tags: list[str] | None = None) -> str:
    embedding = _embed(content)
    with get_connection() as conn:
        # RETURNING id：让 INSERT 顺便把新生成的主键 id 返回回来
        # .fetchone()：只取返回结果的第一行
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
                # tags && %s：Postgres 的数组运算符，判断两个标签数组是否有交集（是否有共同标签）
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
    # {r[2]:.3f}：格式化说明符，把距离值保留 3 位小数
    lines = [f"(相似度距离 {r[2]:.3f}) {r[0]}" for r in rows]
    return f"找到 {len(rows)} 条相关记忆：\n" + "\n".join(lines)
