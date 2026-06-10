"""路由逻辑"""

from .state import AgentState


def route_after_moderator(state: AgentState) -> str:
    """主持人发言后的路由"""

    # 如果有错误，跳转到错误处理
    if state.get("error"):
        return "error_handler"

    # 如果是总结阶段，跳转到总结节点
    if state.get("phase") == "summarizing":
        return "summarizer"

    # 如果是完成阶段，结束
    if state.get("phase") == "finished":
        return "end"

    # 获取专家数量
    participants = state["participants"]
    experts = [p for p in participants if p["role"] == "expert"]

    # 如果没有专家，直接结束
    if len(experts) == 0:
        return "end"

    # 否则让第一个专家发言
    return "expert_0"


def route_after_expert(state: AgentState) -> str:
    """专家发言后的路由"""

    # 如果有错误，跳转到错误处理
    if state.get("error"):
        return "error_handler"

    # 如果是总结阶段，跳转到总结节点
    if state.get("phase") == "summarizing":
        return "summarizer"

    # 如果是完成阶段，结束
    if state.get("phase") == "finished":
        return "end"

    # 获取参与者信息
    participants = state["participants"]
    experts = [p for p in participants if p["role"] == "expert"]

    # 当前发言者索引
    current_index = state.get("current_speaker_index", 0)

    # 如果所有专家都发过言，回到主持人并递增轮次
    if current_index >= len(experts):
        return "moderator"

    # 否则让下一个专家发言
    return f"expert_{current_index}"


def increment_round(state: AgentState) -> dict:
    """递增轮次（在所有专家发言后调用）"""
    return {
        "current_round": state.get("current_round", 0) + 1,
        "current_speaker_index": 0,  # 重置发言者索引
    }
