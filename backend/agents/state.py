"""智能体状态定义"""

from typing import Annotated, TypedDict
from operator import add


class AgentState(TypedDict):
    """智能体运行时状态"""

    # 讨论ID
    discussion_id: str

    # 讨论主题
    topic: str

    # 当前轮次
    current_round: int

    # 最大轮次
    max_rounds: int

    # 参与者列表
    # [{"id": "...", "name": "张教授", "role": "expert", "title": "...", "stance": "...", "system_prompt": "..."}]
    participants: list[dict]

    # 当前发言者索引
    current_speaker_index: int

    # 消息历史（追加模式）
    # [{"participant_id": "...", "content": "...", "round": 1}]
    messages: Annotated[list[dict], add]

    # 共识列表（追加模式）
    # [{"content": "...", "type": "consensus|dissensus|insight"}]
    consensuses: Annotated[list[dict], add]

    # 讨论阶段
    phase: str

    # 错误信息
    error: str


def create_agent_state(
    discussion_id: str,
    topic: str,
    participants: list[dict],
    max_rounds: int = 5,
) -> AgentState:
    """创建初始智能体状态"""

    return {
        "discussion_id": discussion_id,
        "topic": topic,
        "current_round": 0,
        "max_rounds": max_rounds,
        "participants": participants,
        "current_speaker_index": 0,
        "messages": [],
        "consensuses": [],
        "phase": "setup",
        "error": "",
    }
