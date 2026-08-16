"""
Agent Loop：整个项目的"心脏"，对应原项目 letta/agents/letta_agent.py 的核心循环。
一次 step() 对应用户发一条消息、agent 处理完并给出最终回复的完整过程，中间可能反复调用记忆工具。

真实调用链（这是整个学习项目要复现的主线）：
用户发消息
  -> 组装 prompt：core memory(永远在) + recall memory(最近若干条历史) + 这条新消息
  -> 调用 DeepSeek，带上 4 个记忆工具的 schema
  -> 模型自己决定：直接回复，还是先调用某个记忆工具
  -> 如果是工具调用：执行对应的 Python 函数(读/写 core/recall/archival memory)，
     把执行结果作为一条 "tool" 消息喂回去，再问模型一次
  -> 重复上一步，直到模型给出面向用户的最终文本回复
  -> 把这轮的 user/assistant 消息落盘进 recall memory，供以后回忆
"""
import json

from agent import llm_client
from memory import core_memory, recall_memory
from tools.memory_tools import TOOL_SCHEMAS, execute_tool_call

MAX_TOOL_ROUNDS = 5  # 防止模型陷入死循环反复调用工具，原项目里也有类似的步数上限保护


def _build_system_prompt(agent_id: str) -> str:
    blocks = core_memory.get_all_blocks(agent_id)
    if not blocks:
        return "你是一个会持续积累记忆的助手。你可以调用工具来读写你的长期记忆。"
    memory_text = "\n".join(f"[{b['label']}] {b['value']}" for b in blocks)
    return (
        "你是一个会持续积累记忆的助手。以下是你当前的 core memory（这部分内容永远可见）：\n"
        f"{memory_text}\n"
        "如果对话中出现值得长期记住的信息，主动调用工具把它写进 core memory 或 archival memory。"
    )


def step(agent_id: str, user_text: str) -> str:
    system_prompt = _build_system_prompt(agent_id)  # 第一步：拼 core memory 进 system prompt
    history = recall_memory.get_recent_messages(agent_id, limit=20)  # 第二步：取最近历史当上下文

    messages = [{"role": "system", "content": system_prompt}]
    messages += [{"role": m["role"], "content": m["content"]} for m in history]
    messages.append({"role": "user", "content": user_text})

    for _ in range(MAX_TOOL_ROUNDS):
        reply = llm_client.chat(messages, TOOL_SCHEMAS)  # 第三步：问模型
        tool_calls = reply.get("tool_calls")

        if not tool_calls:  # 模型直接给出面向用户的回复，循环结束
            final_text = reply.get("content") or ""
            recall_memory.append_message(agent_id, "user", user_text)  # 第五步：落盘这轮对话
            recall_memory.append_message(agent_id, "assistant", final_text)
            return final_text

        # 模型选择了调用工具：把模型这条带 tool_calls 的消息原样放回上下文，
        # 再把每个工具的执行结果作为 role="tool" 的消息接上去
        messages.append(reply)
        for call in tool_calls:
            name = call["function"]["name"]
            arguments = json.loads(call["function"]["arguments"] or "{}")
            result = execute_tool_call(agent_id, name, arguments)  # 第四步：真正执行记忆读写
            messages.append({"role": "tool", "tool_call_id": call["id"], "content": result})

    return "（已达到工具调用轮数上限，未能给出最终回复）"
