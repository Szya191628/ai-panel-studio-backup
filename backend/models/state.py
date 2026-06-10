"""LangGraph状态定义"""

from typing import Annotated, TypedDict
from operator import add
from langchain_core.messages import BaseMessage

from .enums import DiscussionStatus, ParticipantRole


class RoundTableState(TypedDict):
    """
    圆桌讨论状态

    使用 Annotated + operator.add 实现消息追加（非覆盖）
    """

    # ==================== 核心状态 ====================

    # 消息历史（追加模式）
    messages: Annotated[list[BaseMessage], add]

    # 讨论主题
    topic: str

    # 参与者配置列表
    # [{"id": "...", "name": "张教授", "role": "expert", "system_prompt": "..."}]
    participants: list[dict]

    # ==================== 讨论进度 ====================

    # 当前发言者索引
    current_speaker_index: int

    # 当前轮次
    round_number: int

    # 最大轮次
    max_rounds: int

    # 讨论阶段（复用 DiscussionStatus 枚举值）
    phase: str

    # ==================== 记录与分析 ====================

    # 结构化意见记录（追加模式）
    # [{"agent": "张教授", "round": 1, "opinion": "..."}]
    opinions: Annotated[list[dict], add]

    # 共识列表（追加模式）
    # [{"content": "...", "type": "consensus|dissensus|insight"}]
    consensuses: Annotated[list[dict], add]

    # 最终总结
    summary: str

    # ==================== 错误处理 ====================

    # 错误信息
    error: str


class AgentConfig(TypedDict):
    """智能体配置"""

    # 参与者ID
    id: str

    # 参与者姓名
    name: str

    # 角色（复用 ParticipantRole 枚举值）
    role: str

    # 职业/Title
    title: str

    # 立场
    stance: str

    # 专属颜色
    color: str

    # 系统提示词
    system_prompt: str


class StreamEvent(TypedDict):
    """流式事件"""

    # 事件类型
    event: str

    # 事件数据
    data: dict

    # 讨论ID
    discussion_id: str

    # 时间戳
    timestamp: str


def create_initial_state(
    topic: str,
    participants: list[dict],
    max_rounds: int = 5
) -> RoundTableState:
    """创建初始状态"""

    return {
        "messages": [],
        "topic": topic,
        "participants": participants,
        "current_speaker_index": 0,
        "round_number": 0,
        "max_rounds": max_rounds,
        "phase": DiscussionStatus.PENDING.value,
        "opinions": [],
        "consensuses": [],
        "summary": "",
        "error": "",
    }


def create_agent_config(
    id: str,
    name: str,
    role: str,
    title: str,
    stance: str,
    color: str,
    system_prompt: str
) -> AgentConfig:
    """创建智能体配置"""

    return {
        "id": id,
        "name": name,
        "role": role,
        "title": title,
        "stance": stance,
        "color": color,
        "system_prompt": system_prompt,
    }
