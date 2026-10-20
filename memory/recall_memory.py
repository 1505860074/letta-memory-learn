"""
Recall Memory：完整对话历史，不受 context window 大小限制。
对应原项目 letta/services/message_manager.py，这里把"混合搜索(文本+向量)"简化成纯文本 ILIKE 匹配，
语义检索的能力留给 archival_memory 去演示，避免两层都做一遍同样的事，混淆学习重点。
"""
from memory.db import get_connection


def append_message(agent_id: str, role: str, content: str) -> None:
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO messages (agent_id, role, content) VALUES (%s, %s, %s)",
            (agent_id, role, content),
        )


def get_recent_messages(agent_id: str, limit: int = 20) -> list[dict]:
    """agent_loop 用这个函数取"最近几轮对话"作为当前 context window 里的历史。"""
    with get_connection() as conn:
        # ORDER BY id DESC LIMIT %s：按 id 倒序排，只取最近的 limit 条
        rows = conn.execute(
            "SELECT role, content FROM messages WHERE agent_id = %s ORDER BY id DESC LIMIT %s",
            (agent_id, limit),
        ).fetchall()
    # reversed(rows)：内置函数，把"倒序取出的结果"翻转回正常的时间先后顺序
    return [{"role": r[0], "content": r[1]} for r in reversed(rows)]


def conversation_search(agent_id: str, query: str | None = None, limit: int = 5) -> str:
    with get_connection() as conn:
        if query:
            # ILIKE：Postgres 里"不区分大小写"的模糊匹配；两边的 % 是通配符（匹配任意字符）
            rows = conn.execute(
                "SELECT role, content, created_at FROM messages "
                "WHERE agent_id = %s AND content ILIKE %s ORDER BY id DESC LIMIT %s",
                (agent_id, f"%{query}%", limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT role, content, created_at FROM messages WHERE agent_id = %s ORDER BY id DESC LIMIT %s",
                (agent_id, limit),
            ).fetchall()
    if not rows:
        return "没有找到匹配的历史消息。"
    lines = [f"[{r[2]}] {r[0]}: {r[1]}" for r in rows]
    # len(rows)：Python 内置函数，返回对象的长度（这里是结果条数）
    return f"找到 {len(rows)} 条结果：\n" + "\n".join(lines)
