"""总结节点"""

from langchain_core.messages import SystemMessage

from ..state import AgentState
from ..prompts import PromptManager
from ..llm import create_llm, build_message_history


def summarizer_node(state: AgentState) -> dict:
    """总结节点：对讨论进行总结"""

    participants = state["participants"]
    moderator = next((p for p in participants if p["role"] == "moderator"), None)

    if not moderator:
        return {
            "error": "未找到主持人进行总结",
            "phase": "error",
        }

    # 构建总结提示词
    system_prompt = PromptManager.get_summary_prompt(
        topic=state["topic"],
        current_round=state["current_round"],
        participants=participants,
    )

    # 构建消息历史（使用共享辅助函数，截断最近20条）
    messages = [SystemMessage(content=system_prompt)]
    messages.extend(build_message_history(state["messages"], participants, max_messages=20))

    # 添加总结引导
    from langchain_core.messages import HumanMessage
    messages.append(HumanMessage(content="请对本次讨论进行全面总结，提炼各方核心观点和最终共识。"))

    try:
        # 调用LLM（使用共享工厂，较低温度以获得更稳定的总结）
        llm = create_llm(temperature=0.5)
        response = llm.invoke(messages)

        # 返回总结
        return {
            "messages": [{
                "participant_id": moderator["id"],
                "participant_name": moderator["name"],
                "content": response.content,
                "round": state["current_round"],
                "is_summary": True,
            }],
            "phase": "finished",
        }

    except Exception as e:
        return {
            "error": f"总结节点错误: {str(e)}",
            "phase": "error",
        }
