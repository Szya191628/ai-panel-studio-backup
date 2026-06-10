"""LangGraph图构建 - 并行优化版本"""

import asyncio
from typing import Optional
from langgraph.graph import StateGraph, END

from .state import AgentState, create_agent_state
from .nodes import moderator_node, create_expert_node, summarizer_node
from .routing import route_after_moderator, increment_round


def create_parallel_expert_node(experts: list[dict]):
    """创建并行专家节点 - 所有专家同时发言"""

    async def parallel_experts_node(state: AgentState) -> dict:
        """并行执行所有专家节点"""
        from .nodes.expert import create_expert_node
        from .llm import create_llm, build_message_history
        from langchain_core.messages import SystemMessage, HumanMessage
        from ..prompts import PromptManager

        participants = state["participants"]
        expert_list = [p for p in participants if p["role"] == "expert"]

        # 并行调用所有专家
        async def call_expert(expert_index: int, expert: dict):
            """单个专家调用"""
            try:
                # 构建系统提示词
                system_prompt = PromptManager.get_expert_prompt(
                    expert=expert,
                    topic=state["topic"],
                    current_round=state["current_round"],
                    max_rounds=state["max_rounds"],
                )

                # 构建消息历史
                messages = [SystemMessage(content=system_prompt)]
                messages.extend(build_message_history(state["messages"], participants, max_messages=10))

                # 添加发言引导
                if len(state["messages"]) == 0:
                    messages.append(HumanMessage(content="请开始发言，表达你对讨论主题的看法。"))
                else:
                    messages.append(HumanMessage(content="请继续发言，回应其他参与者的观点或补充你的看法。"))

                # 调用LLM
                llm = create_llm(temperature=0.7)
                response = await asyncio.to_thread(llm.invoke, messages)

                return {
                    "expert_index": expert_index,
                    "participant_id": expert["id"],
                    "participant_name": expert["name"],
                    "content": response.content,
                    "round": state["current_round"],
                }
            except Exception as e:
                return {
                    "expert_index": expert_index,
                    "participant_id": expert["id"],
                    "participant_name": expert["name"],
                    "content": f"[{expert['name']}发言失败: {str(e)}]",
                    "round": state["current_round"],
                    "error": str(e),
                }

        # 并行执行所有专家
        tasks = [call_expert(i, expert) for i, expert in enumerate(expert_list)]
        results = await asyncio.gather(*tasks)

        # 按专家顺序排列结果
        results.sort(key=lambda x: x["expert_index"])

        # 构建返回消息
        messages = []
        errors = []
        for r in results:
            messages.append({
                "participant_id": r["participant_id"],
                "participant_name": r["participant_name"],
                "content": r["content"],
                "round": r["round"],
            })
            if "error" in r:
                errors.append(r["error"])

        return {
            "messages": messages,
            "current_speaker_index": len(expert_list),  # 标记所有专家都已发言
            "error": "; ".join(errors) if errors else "",
        }

    return parallel_experts_node


class RoundTableGraph:
    """圆桌讨论图 - 并行优化版本"""

    def __init__(self, participants: list[dict], max_rounds: int = 5):
        """
        初始化圆桌讨论图

        Args:
            participants: 参与者列表
            max_rounds: 最大讨论轮次
        """
        self.participants = participants
        self.max_rounds = max_rounds
        self.experts = [p for p in participants if p["role"] == "expert"]
        self.moderator = next((p for p in participants if p["role"] == "moderator"), None)

        if not self.moderator:
            raise ValueError("必须包含一个主持人")

        if len(self.experts) == 0:
            raise ValueError("必须包含至少一个专家")

        # 构建图
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """构建LangGraph状态图 - 并行版本"""

        # 创建状态图
        workflow = StateGraph(AgentState)

        # 添加主持人节点
        workflow.add_node("moderator", moderator_node)

        # 添加并行专家节点（所有专家同时发言）
        workflow.add_node("parallel_experts", create_parallel_expert_node(self.experts))

        # 添加轮次递增节点
        workflow.add_node("increment_round", increment_round)

        # 添加总结节点
        workflow.add_node("summarizer", summarizer_node)

        # 添加错误处理节点
        def error_handler(state: AgentState) -> dict:
            """错误处理节点"""
            return {
                "phase": "error",
                "error": state.get("error", "未知错误"),
            }

        workflow.add_node("error_handler", error_handler)

        # 设置入口点
        workflow.set_entry_point("moderator")

        # 主持人 -> 并行专家/总结/错误
        def route_after_moderator_parallel(state: AgentState) -> str:
            """主持人发言后的路由（并行版本）"""
            if state.get("error"):
                return "error_handler"
            if state.get("phase") == "summarizing":
                return "summarizer"
            if state.get("phase") == "finished":
                return "end"
            return "parallel_experts"

        workflow.add_conditional_edges(
            "moderator",
            route_after_moderator_parallel,
            {
                "parallel_experts": "parallel_experts",
                "summarizer": "summarizer",
                "end": END,
                "error_handler": "error_handler",
            },
        )

        # 并行专家 -> 轮次递增/总结/错误
        def route_after_parallel_experts(state: AgentState) -> str:
            """并行专家发言后的路由"""
            if state.get("error"):
                return "error_handler"
            if state.get("phase") == "summarizing":
                return "summarizer"
            if state.get("phase") == "finished":
                return "end"
            # 检查是否达到最大轮次
            if state.get("current_round", 0) >= state.get("max_rounds", 5):
                return "summarizer"
            return "increment_round"

        workflow.add_conditional_edges(
            "parallel_experts",
            route_after_parallel_experts,
            {
                "increment_round": "increment_round",
                "summarizer": "summarizer",
                "end": END,
                "error_handler": "error_handler",
            },
        )

        # 轮次递增 -> 主持人
        workflow.add_edge("increment_round", "moderator")

        # 总结 -> 结束
        workflow.add_edge("summarizer", END)

        # 错误处理 -> 结束
        workflow.add_edge("error_handler", END)

        # 编译图
        return workflow.compile()

    def _create_initial_state(
        self,
        discussion_id: str,
        topic: str,
        initial_messages: Optional[list[dict]] = None,
    ) -> AgentState:
        """创建初始状态"""
        initial_state = create_agent_state(
            discussion_id=discussion_id,
            topic=topic,
            participants=self.participants,
            max_rounds=self.max_rounds,
        )

        # 如果有初始消息，添加到状态中
        if initial_messages:
            initial_state["messages"] = initial_messages

        return initial_state

    def invoke(
        self,
        discussion_id: str,
        topic: str,
        initial_messages: Optional[list[dict]] = None,
    ) -> dict:
        """
        执行讨论

        Args:
            discussion_id: 讨论ID
            topic: 讨论主题
            initial_messages: 初始消息（可选）

        Returns:
            最终状态
        """
        initial_state = self._create_initial_state(discussion_id, topic, initial_messages)

        # 执行图
        try:
            result = self.graph.invoke(initial_state)
            return result
        except Exception as e:
            return {
                **initial_state,
                "error": f"图执行错误: {str(e)}",
                "phase": "error",
            }

    def stream(
        self,
        discussion_id: str,
        topic: str,
        initial_messages: Optional[list[dict]] = None,
    ):
        """
        流式执行讨论

        Args:
            discussion_id: 讨论ID
            topic: 讨论主题
            initial_messages: 初始消息（可选）

        Yields:
            状态更新
        """
        initial_state = self._create_initial_state(discussion_id, topic, initial_messages)

        # 流式执行图
        try:
            for event in self.graph.stream(initial_state, stream_mode="updates"):
                yield event
        except Exception as e:
            yield {
                "error": f"图执行错误: {str(e)}",
                "phase": "error",
            }
