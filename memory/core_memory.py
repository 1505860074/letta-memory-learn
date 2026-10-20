"""
Core Memory：永远跟着塞进 prompt 里的记忆块。
对应原项目 letta/services/block_manager.py，这里砍掉了权限校验、多租户、版本历史，
只保留 memory() 工具真正用到的 5 个操作：create / str_replace / insert / delete / rename。
"""
from memory.db import get_connection


def get_all_blocks(agent_id: str) -> list[dict]:
    """取出某个 agent 的全部 core memory 块，用于拼进 system prompt。"""
    # with ... as conn：上下文管理器，退出 with 代码块时会自动把连接关掉/归还，不用手写关闭
    with get_connection() as conn:
        # conn.execute(sql, params)：执行一条 SQL；%s 是 psycopg 的占位符，传入的参数会被安全转义
        # .fetchall()：取出查询结果的全部行（每行是一个元组 tuple）
        rows = conn.execute(
            "SELECT label, value, description FROM core_memory_blocks WHERE agent_id = %s ORDER BY label",
            (agent_id,),
        ).fetchall()
    # 把元组行转成带字段名的 dict，后面按 r[0]/r[1] 访问时语义更清楚
    return [{"label": r[0], "value": r[1], "description": r[2]} for r in rows]


def create_block(agent_id: str, path: str, file_text: str = "", description: str = "") -> str:
    label = _label_from_path(path)
    with get_connection() as conn:
        # ON CONFLICT ... DO UPDATE：Postgres 的"存在就更新、不存在就插入"（upsert）语法
        # EXCLUDED.value 指本次想要插入的那一行里的 value
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
        # .fetchone()：只取查询结果的第一行（没有匹配则返回 None）
        row = conn.execute(
            "SELECT value FROM core_memory_blocks WHERE agent_id = %s AND label = %s", (agent_id, label)
        ).fetchone()
        if row is None:
            return f"记忆块 {path} 不存在"
        value = row[0]
        if old_string not in value:
            return f"没有在 {path} 中找到要替换的文本"
        # str.replace(旧, 新, 次数)：把字符串里的旧文本换成新文本；最后的 1 表示只替换第一处
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
        # str.splitlines()：按行把一整段文本拆成一个字符串列表
        lines = row[0].splitlines()
        # list.insert(i, x)：在列表的第 i 个位置插入一个元素
        # max(0, min(insert_line, len(lines)))：把行号夹在 0 到 len(lines) 之间，防止越界
        lines.insert(max(0, min(insert_line, len(lines))), insert_text)
        # "\n".join(...)：用换行符把列表里的各行重新拼回一整段文本
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
    # str.rstrip("/")：去掉字符串结尾的 "/"；str.split("/")：按 "/" 拆成列表；[-1]：取列表最后一段
    return path.rstrip("/").split("/")[-1]
