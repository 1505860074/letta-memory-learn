"""
把三层记忆的 Python 函数，包装成大模型 function calling 能"看懂"的工具定义。
对应原项目 letta/functions/function_sets/base.py（原项目还有 schema_generator.py 自动从函数签名
生成 JSON schema，这里为了教学直观，改成手写 schema，两者是等价的）。

模型每一轮推理时，会看到下面 TOOL_SCHEMAS 里的工具列表和说明，自己判断"这轮该不该调用、调用哪个"。
"""
from memory import archival_memory, core_memory, recall_memory

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "core_memory_append",
            "description": "把一句话追加写入 core memory 中的某个记忆块（比如 persona、human 偏好）。"
            "core memory 会永远出现在你的 system prompt 里，适合存少量、需要一直记住的信息。",
            "parameters": {
                "type": "object",
                "properties": {
                    "label": {"type": "string", "description": "记忆块的名字，例如 'human'、'persona'"},
                    "content": {"type": "string", "description": "要记住的内容"},
                },
                "required": ["label", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "archival_memory_insert",
            "description": "把一段自包含的事实/总结存入archival memory（长期知识库），可被以后语义检索到。"
            "适合存不需要一直挂在眼前、但以后可能用得上的信息。",
            "parameters": {
                "type": "object",
                "properties": {
                    "content": {"type": "string", "description": "要存储的内容，应清晰、自包含"},
                    "tags": {"type": "array", "items": {"type": "string"}, "description": "可选的分类标签"},
                },
                "required": ["content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "archival_memory_search",
            "description": "按语义相似度在 archival memory 中检索相关内容。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "要搜索的问题或关键词"},
                    "top_k": {"type": "integer", "description": "返回条数，默认5"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "conversation_search",
            "description": "在完整历史对话(recall memory)中做关键词搜索，找回不在当前上下文窗口里的旧消息。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "搜索关键词"},
                    "limit": {"type": "integer", "description": "返回条数，默认5"},
                },
                "required": ["query"],
            },
        },
    },
]


def _core_memory_append(agent_id: str, label: str, content: str) -> str:
    """在已有 core memory 块末尾追加一行；块不存在就新建。是 memory(command="str_replace"/"create") 的简化封装。"""
    blocks = {b["label"]: b for b in core_memory.get_all_blocks(agent_id)}
    path = f"/memories/{label}"
    if label not in blocks or not blocks[label]["value"]:
        return core_memory.create_block(agent_id, path, file_text=content)
    old_value = blocks[label]["value"]
    new_value = old_value + "\n" + content
    return core_memory.str_replace(agent_id, path, old_value, new_value)


DISPATCH = {
    "core_memory_append": lambda agent_id, **kw: _core_memory_append(agent_id, **kw),
    "archival_memory_insert": lambda agent_id, **kw: archival_memory.archival_memory_insert(agent_id, **kw),
    "archival_memory_search": lambda agent_id, **kw: archival_memory.archival_memory_search(agent_id, **kw),
    "conversation_search": lambda agent_id, **kw: recall_memory.conversation_search(agent_id, **kw),
}


def execute_tool_call(agent_id: str, name: str, arguments: dict) -> str:
    """agent_loop 从模型返回的 tool_call 里拿到 name/arguments，丢进这里执行，拿到字符串结果。"""
    if name not in DISPATCH:
        return f"未知工具: {name}"
    return DISPATCH[name](agent_id, **arguments)
