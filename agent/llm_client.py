"""
调用 DeepSeek 的 Chat Completions API。
对应原项目 letta/llm_api/deepseek_client.py —— DeepSeek 接口与 OpenAI 完全兼容，
所以可以直接用官方 openai SDK，只把 base_url 换成 DeepSeek 的地址。
"""
import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

_client = OpenAI(
    api_key=os.environ["DEEPSEEK_API_KEY"],
    base_url="https://api.deepseek.com",
)

MODEL_NAME = "deepseek-chat"


def chat(messages: list[dict], tools: list[dict]) -> dict:
    """
    发一轮请求给模型。
    返回的 message 里，如果模型决定调用工具，message["tool_calls"] 会有内容；
    如果模型只是想直接回复用户，message["content"] 会有文本，tool_calls 为空。
    """
    response = _client.chat.completions.create(
        model=MODEL_NAME,
        messages=messages,
        tools=tools,
    )
    return response.choices[0].message.model_dump()
