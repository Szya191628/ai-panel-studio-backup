"""专家节点工厂 - 沉浸式版本"""

import asyncio
from langchain_core.messages import HumanMessage, SystemMessage

from ..state import AgentState
from ..prompts import PromptManager
from ..llm import create_llm, build_message_history


def create_expert_node(expert_index: int):
    """创建专家节点"""

    def expert_node(state: AgentState) -> dict:
        """专家节点：根据当前讨论内容自主发言"""

        participants = state["participants"]
        experts = [p for p in participants if p["role"] == "expert"]

        if expert_index >= len(experts):
            return {
                "error": f"专家索引 {expert_index} 超出范围",
                "phase": "error",
            }

        expert = experts[expert_index]

        # 构建系统提示词
        system_prompt = PromptManager.get_expert_prompt(
            expert=expert,
            topic=state["topic"],
            current_round=state["current_round"],
            max_rounds=state["max_rounds"],
        )

        # 构建消息历史（使用共享辅助函数）
        messages = [SystemMessage(content=system_prompt)]
        messages.extend(build_message_history(state["messages"], participants, max_messages=10))

        # 添加发言引导
        if len(state["messages"]) == 0:
            messages.append(HumanMessage(content="请开始发言，表达你对讨论主题的看法。"))
        else:
            messages.append(HumanMessage(content="请继续发言，回应其他参与者的观点或补充你的看法。"))

        try:
            # 调用LLM（使用共享工厂）
            llm = create_llm(temperature=0.7)
            response = llm.invoke(messages)

            # 计算下一个发言者索引
            next_index = state.get("current_speaker_index", 0) + 1

            # 返回专家发言（包含思考过程）
            return {
                "messages": [{
                    "participant_id": expert["id"],
                    "participant_name": expert["name"],
                    "content": response.content,
                    "round": state["current_round"],
                    "thinking_process": {
                        "status": "speaking",
                        "focus_point": f"基于{expert['stance']}立场发言",
                        "key_points": _extract_key_points(response.content),
                        "stance": expert["stance"],
                    },
                }],
                "current_speaker_index": next_index,
            }

        except Exception as e:
            return {
                "error": f"专家节点错误 ({expert['name']}): {str(e)}",
                "phase": "error",
            }

    return expert_node


def _extract_key_points(content: str) -> list[str]:
    """从发言中提取关键点"""
    key_points = []
    sentences = content.split("。")
    for sentence in sentences[:3]:
        if len(sentence.strip()) > 5:
            key_points.append(sentence.strip())
    return key_points
