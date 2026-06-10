"""主持人节点 - 沉浸式版本"""

import asyncio
from langchain_core.messages import SystemMessage

from ..state import AgentState
from ..prompts import PromptManager
from ..llm import create_llm, build_message_history


async def emit_agent_status(participant_id: str, status: str, focus_point: str = None):
    """发送智能体状态更新（用于实时展示）"""
    # 这个函数会被SSE流调用，实时更新前端状态
    pass


def moderator_node(state: AgentState) -> dict:
    """主持人节点：负责开场、追问、串联和总结"""

    # 获取当前参与者信息
    participants = state["participants"]
    moderator = next((p for p in participants if p["role"] == "moderator"), None)

    if not moderator:
        return {
            "error": "未找到主持人",
            "phase": "error",
        }

    # 构建系统提示词
    system_prompt = PromptManager.get_moderator_prompt(
        topic=state["topic"],
        current_round=state["current_round"],
        max_rounds=state["max_rounds"],
        participants=participants,
    )

    # 构建消息历史（使用共享辅助函数）
    messages = [SystemMessage(content=system_prompt)]
    messages.extend(build_message_history(state["messages"], participants, max_messages=10))

    # 如果是开场，添加开场引导
    if state["current_round"] == 0 and len(state["messages"]) == 0:
        from langchain_core.messages import HumanMessage
        messages.append(HumanMessage(content="请开始本次圆桌讨论，介绍主题和参与者。"))

    # 如果是最后一轮，准备总结
    if state["current_round"] >= state["max_rounds"]:
        from langchain_core.messages import HumanMessage
        messages.append(HumanMessage(content="讨论即将结束，请对本次讨论进行总结。"))

    try:
        # 调用LLM（使用共享工厂）
        llm = create_llm(temperature=0.7)
        response = llm.invoke(messages)

        # 决定下一阶段
        next_phase = "debating"
        if state["current_round"] >= state["max_rounds"]:
            next_phase = "summarizing"

        # 返回主持人发言（包含思考过程）
        return {
            "messages": [{
                "participant_id": moderator["id"],
                "participant_name": moderator["name"],
                "content": response.content,
                "round": state["current_round"],
                "thinking_process": {
                    "status": "speaking",
                    "focus_point": f"正在引导第{state['current_round']+1}轮讨论",
                    "key_points": _extract_key_points(response.content),
                },
            }],
            "phase": next_phase,
        }

    except Exception as e:
        return {
            "error": f"主持人节点错误: {str(e)}",
            "phase": "error",
        }


def _extract_key_points(content: str) -> list[str]:
    """从发言中提取关键点"""
    # 简单的关键词提取
    key_points = []
    sentences = content.split("。")
    for sentence in sentences[:3]:
        if len(sentence.strip()) > 5:
            key_points.append(sentence.strip())
    return key_points
