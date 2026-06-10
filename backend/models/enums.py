"""枚举类型定义"""

from enum import Enum


class DiscussionStatus(str, Enum):
    """讨论状态"""
    PENDING = "pending"          # 待开始
    GENERATING = "generating"    # 生成嘉宾中
    CONFIRMING = "confirming"    # 确认嘉宾中
    DEBATING = "debating"        # 讨论中
    SUMMARIZING = "summarizing"  # 总结中
    FINISHED = "finished"        # 已结束
    FAILED = "failed"            # 失败


class ParticipantRole(str, Enum):
    """参与者角色"""
    MODERATOR = "moderator"      # 主持人
    EXPERT = "expert"            # 专家


class AgentPhase(str, Enum):
    """智能体运行阶段"""
    IDLE = "idle"                # 待机
    PREPARING = "preparing"      # 准备发言
    SPEAKING = "speaking"        # 发言中
    LISTENING = "listening"      # 倾听中


class ConsensusType(str, Enum):
    """共识类型"""
    CONSENSUS = "consensus"      # 共识
    DISSENSUS = "dissensus"      # 分歧
    INSIGHT = "insight"          # 洞见


class MessageType(str, Enum):
    """消息类型"""
    SPEECH = "speech"            # 正常发言
    QUESTION = "question"        # 提问
    RESPONSE = "response"        # 回应
    SUMMARY = "summary"          # 总结
    SYSTEM = "system"            # 系统消息
