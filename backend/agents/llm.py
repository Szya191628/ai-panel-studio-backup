"""LLM工厂 - 共享ChatOpenAI实例"""

from langchain_openai import ChatOpenAI
from backend.core.config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL


def create_llm(temperature: float = 0.7, streaming: bool = False) -> ChatOpenAI:
    """创建LLM实例"""
    return ChatOpenAI(
        model=DEEPSEEK_MODEL,
        api_key=DEEPSEEK_API_KEY,
        base_url=DEEPSEEK_BASE_URL,
        temperature=temperature,
        streaming=streaming,
    )


def build_message_history(
    messages: list[dict],
    participants: list[dict],
    max_messages: int = 10,
) -> list:
    """构建消息历史（共享辅助函数）"""
    from langchain_core.messages import HumanMessage

    # 构建participant字典用于O(1)查找
    participant_dict = {p["id"]: p for p in participants}

    result = []
    for msg in messages[-max_messages:]:
        participant = participant_dict.get(msg["participant_id"])
        name = participant["name"] if participant else "未知"
        result.append(HumanMessage(content=f"{name}: {msg['content']}"))

    return result
