"""
Core Memory：永远跟着塞进 prompt 里的记忆块。
对应原项目 letta/services/block_manager.py，这里砍掉了权限校验、多租户、版本历史，
只保留 memory() 工具真正用到的 5 个操作：create / str_replace / insert / delete / rename。
"""
from memory.db import get_connection


def get_all_blocks(agent_id: str) -> list[dict]:
    """取出某个 agent 的全部 core memory 块，用于拼进 system prompt。"""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT label, value, description FROM core_memory_blocks WHERE agent_id = %s ORDER BY label",
            (agent_id,),
        ).fetchall()
    return [{"label": r[0], "value": r[1], "description": r[2]} for r in rows]


def create_block(agent_id: str, path: str, file_text: str = "", description: str = "") -> str:
    label = _label_from_path(path)
    with get_connection() as conn:
        conn.execute(
            """INSERT INTO core_memory_blocks (agent_id, label, value, description)
               VALUES (%s, %s, %s, %s)
               ON CONFLICT (agent_id, label) DO UPDATE SET value = EXCLUDED.value, description = EXCLUDED.description""",
            (agent_id, label, file_text, description),
        )
    return f"已创建记忆块 {path}"


def str_replace(agent_id: str, path: str, old_string: str, new_string: str) -> str:
    label = _label_from_path(path)
    with get_connection() as conn:
        row = conn.execute(
            "SELECT value FROM core_memory_blocks WHERE agent_id = %s AND label = %s", (agent_id, label)
        ).fetchone()
        if row is None:
            return f"记忆块 {path} 不存在"
        value = row[0]
        if old_string not in value:
            return f"没有在 {path} 中找到要替换的文本"
        new_value = value.replace(old_string, new_string, 1)
        conn.execute(
            "UPDATE core_memory_blocks SET value = %s, updated_at = now() WHERE agent_id = %s AND label = %s",
            (new_value, agent_id, label),
        )
    return f"已更新记忆块 {path}"


def insert(agent_id: str, path: str, insert_line: int, insert_text: str) -> str:
    label = _label_from_path(path)
    with get_connection() as conn:
        row = conn.execute(
            "SELECT value FROM core_memory_blocks WHERE agent_id = %s AND label = %s", (agent_id, label)
        ).fetchone()
        if row is None:
            return f"记忆块 {path} 不存在"
        lines = row[0].splitlines()
        lines.insert(max(0, min(insert_line, len(lines))), insert_text)
        new_value = "\n".join(lines)
        conn.execute(
            "UPDATE core_memory_blocks SET value = %s, updated_at = now() WHERE agent_id = %s AND label = %s",
            (new_value, agent_id, label),
        )
    return f"已在 {path} 第 {insert_line} 行插入内容"


def delete(agent_id: str, path: str) -> str:
    label = _label_from_path(path)
    with get_connection() as conn:
        conn.execute("DELETE FROM core_memory_blocks WHERE agent_id = %s AND label = %s", (agent_id, label))
    return f"已删除记忆块 {path}"


def rename(agent_id: str, old_path: str, new_path: str | None = None, description: str | None = None) -> str:
    old_label = _label_from_path(old_path)
    with get_connection() as conn:
        if new_path:
            new_label = _label_from_path(new_path)
            conn.execute(
                "UPDATE core_memory_blocks SET label = %s WHERE agent_id = %s AND label = %s",
                (new_label, agent_id, old_label),
            )
        if description is not None:
            conn.execute(
                "UPDATE core_memory_blocks SET description = %s WHERE agent_id = %s AND label = %s",
                (description, agent_id, new_label if new_path else old_label),
            )
    return f"已更新记忆块 {old_path}"


def _label_from_path(path: str) -> str:
    # 原项目用 "/memories/xxx" 这种路径风格指代一个记忆块，这里只取最后一段当作 label
    return path.rstrip("/").split("/")[-1]
