"""Pydantic Schema定义 - API契约"""

from typing import Optional, Literal
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

from .enums import DiscussionStatus, ParticipantRole, AgentPhase, ConsensusType, MessageType


# ==================== 讨论相关 Schema ====================

class DiscussionCreate(BaseModel):
    """创建讨论请求"""
    topic: str = Field(..., min_length=2, max_length=200, description="讨论主题")
    expert_count: int = Field(default=4, ge=2, le=8, description="专家人数")
    max_rounds: int = Field(default=5, ge=1, le=20, description="最大讨论轮次")


class DiscussionResponse(BaseModel):
    """讨论响应"""
    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., description="讨论ID")
    topic: str = Field(..., description="讨论主题")
    status: DiscussionStatus = Field(..., description="讨论状态")
    expert_count: int = Field(..., description="专家人数")
    max_rounds: int = Field(..., description="最大轮次")
    current_round: int = Field(default=0, description="当前轮次")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    summary: Optional[str] = Field(None, description="讨论总结")


class DiscussionListItem(BaseModel):
    """讨论列表项"""
    model_config = ConfigDict(from_attributes=True)

    id: str
    topic: str
    status: DiscussionStatus
    participant_count: int
    created_at: datetime


# ==================== 参与者相关 Schema ====================

class ParticipantCreate(BaseModel):
    """创建参与者请求"""
    name: str = Field(..., min_length=1, max_length=50, description="姓名")
    role: ParticipantRole = Field(..., description="角色")
    title: str = Field(..., min_length=1, max_length=100, description="职业/Title")
    stance: str = Field(..., min_length=1, max_length=200, description="立场")
    color: str = Field(..., pattern=r"^#[0-9A-Fa-f]{6}$", description="专属颜色标识")


class ParticipantResponse(BaseModel):
    """参与者响应"""
    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., description="参与者ID")
    discussion_id: str = Field(..., description="所属讨论ID")
    name: str = Field(..., description="姓名")
    role: ParticipantRole = Field(..., description="角色")
    title: str = Field(..., description="职业/Title")
    stance: str = Field(..., description="立场")
    color: str = Field(..., description="专属颜色标识")
    agent_phase: AgentPhase = Field(default=AgentPhase.IDLE, description="智能体状态")
    focus_point: Optional[str] = Field(None, description="当前关注点")
    created_at: Optional[datetime] = Field(None, description="创建时间")


class GuestGenerateRequest(BaseModel):
    """嘉宾生成请求"""
    topic: str = Field(..., min_length=2, max_length=200, description="讨论主题")
    expert_count: int = Field(default=4, ge=2, le=8, description="专家人数")


class GuestGenerateResponse(BaseModel):
    """嘉宾生成响应"""
    moderator: ParticipantResponse = Field(..., description="主持人")
    experts: list[ParticipantResponse] = Field(..., description="专家列表")


# ==================== 消息相关 Schema ====================

class MessageCreate(BaseModel):
    """创建消息请求"""
    content: str = Field(..., min_length=1, max_length=2000, description="消息内容")
    message_type: MessageType = Field(default=MessageType.SPEECH, description="消息类型")


class MessageResponse(BaseModel):
    """消息响应"""
    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., description="消息ID")
    discussion_id: str = Field(..., description="所属讨论ID")
    participant_id: str = Field(..., description="发言者ID")
    participant_name: str = Field(..., description="发言者姓名")
    participant_title: str = Field(..., description="发言者Title")
    participant_color: str = Field(..., description="发言者颜色")
    content: str = Field(..., description="消息内容")
    message_type: MessageType = Field(..., description="消息类型")
    round_number: int = Field(..., description="轮次")
    created_at: datetime = Field(..., description="创建时间")


# ==================== 共识/分歧相关 Schema ====================

class ConsensusResponse(BaseModel):
    """共识/分歧响应"""
    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., description="共识ID")
    discussion_id: str = Field(..., description="所属讨论ID")
    content: str = Field(..., description="共识/分歧内容")
    consensus_type: ConsensusType = Field(..., description="类型")
    round_number: int = Field(..., description="轮次")
    created_at: datetime = Field(..., description="创建时间")


# ==================== SSE事件 Schema ====================

class SSEEvent(BaseModel):
    """SSE事件"""
    event: str = Field(..., description="事件类型")
    data: dict = Field(..., description="事件数据")
    discussion_id: str = Field(..., description="讨论ID")


class SpeechEvent(BaseModel):
    """发言事件"""
    participant_id: str
    participant_name: str
    participant_title: str
    participant_color: str
    content: str
    round_number: int


class PhaseChangeEvent(BaseModel):
    """阶段变更事件"""
    phase: DiscussionStatus
    round_number: int
    message: Optional[str] = None


class AgentStatusEvent(BaseModel):
    """智能体状态事件"""
    participant_id: str
    participant_name: str
    agent_phase: AgentPhase
    focus_point: Optional[str] = None


class ConsensusUpdateEvent(BaseModel):
    """共识更新事件"""
    consensus: ConsensusResponse
    action: Literal["add", "update", "remove"] = Field(..., description="add | update | remove")
