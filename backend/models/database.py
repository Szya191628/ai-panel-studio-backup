"""SQLAlchemy数据库模型"""

from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text, Enum as SQLEnum, CheckConstraint
from sqlalchemy.orm import relationship, declarative_base

from .enums import DiscussionStatus, ParticipantRole, AgentPhase, ConsensusType, MessageType

Base = declarative_base()


def _utc_now():
    """返回UTC时间（替代已废弃的datetime.utcnow）"""
    return datetime.now(timezone.utc)


class Discussion(Base):
    """讨论表"""
    __tablename__ = "discussions"
    __table_args__ = (
        CheckConstraint("expert_count >= 2 AND expert_count <= 8", name="ck_expert_count_range"),
    )

    id = Column(String(36), primary_key=True, comment="讨论ID")
    topic = Column(String(200), nullable=False, comment="讨论主题")
    status = Column(
        SQLEnum(DiscussionStatus, native_enum=False, values_callable=lambda x: [e.value for e in x]),
        default=DiscussionStatus.PENDING,
        nullable=False,
        comment="讨论状态"
    )
    expert_count = Column(Integer, default=4, nullable=False, comment="专家人数")
    max_rounds = Column(Integer, default=5, nullable=False, comment="最大轮次")
    current_round = Column(Integer, default=0, nullable=False, comment="当前轮次")
    summary = Column(Text, nullable=True, comment="讨论总结")
    created_at = Column(DateTime, default=_utc_now, nullable=False, comment="创建时间")
    updated_at = Column(DateTime, default=_utc_now, onupdate=_utc_now, nullable=False, comment="更新时间")

    # 关系
    participants = relationship("Participant", back_populates="discussion", cascade="all, delete-orphan")
    messages = relationship("Message", back_populates="discussion", cascade="all, delete-orphan")
    consensuses = relationship("Consensus", back_populates="discussion", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "topic": self.topic,
            "status": self.status.value if hasattr(self.status, 'value') else self.status,
            "expert_count": self.expert_count,
            "max_rounds": self.max_rounds,
            "current_round": self.current_round,
            "summary": self.summary,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class Participant(Base):
    """参与者表"""
    __tablename__ = "participants"

    id = Column(String(36), primary_key=True, comment="参与者ID")
    discussion_id = Column(String(36), ForeignKey("discussions.id"), nullable=False, comment="所属讨论ID")
    name = Column(String(50), nullable=False, comment="姓名")
    role = Column(
        SQLEnum(ParticipantRole, native_enum=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        comment="角色"
    )
    title = Column(String(100), nullable=False, comment="职业/Title")
    stance = Column(String(200), nullable=False, comment="立场")
    color = Column(String(7), nullable=False, comment="专属颜色标识")
    agent_phase = Column(
        SQLEnum(AgentPhase, native_enum=False, values_callable=lambda x: [e.value for e in x]),
        default=AgentPhase.IDLE,
        nullable=False,
        comment="智能体状态"
    )
    focus_point = Column(String(200), nullable=True, comment="当前关注点")
    created_at = Column(DateTime, default=_utc_now, nullable=False, comment="创建时间")

    # 关系（仅 Discussion 保留 cascade，Participant 不对 Message 做 cascade）
    discussion = relationship("Discussion", back_populates="participants")
    messages = relationship("Message", back_populates="participant", lazy="selectin")

    def to_dict(self):
        return {
            "id": self.id,
            "discussion_id": self.discussion_id,
            "name": self.name,
            "role": self.role.value if hasattr(self.role, 'value') else self.role,
            "title": self.title,
            "stance": self.stance,
            "color": self.color,
            "agent_phase": self.agent_phase.value if hasattr(self.agent_phase, 'value') else self.agent_phase,
            "focus_point": self.focus_point,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Message(Base):
    """消息表"""
    __tablename__ = "messages"

    id = Column(String(36), primary_key=True, comment="消息ID")
    discussion_id = Column(String(36), ForeignKey("discussions.id"), nullable=False, comment="所属讨论ID")
    participant_id = Column(String(36), ForeignKey("participants.id"), nullable=False, comment="发言者ID")
    content = Column(Text, nullable=False, comment="消息内容")
    message_type = Column(
        SQLEnum(MessageType, native_enum=False, values_callable=lambda x: [e.value for e in x]),
        default=MessageType.SPEECH,
        nullable=False,
        comment="消息类型"
    )
    round_number = Column(Integer, default=0, nullable=False, comment="轮次")
    created_at = Column(DateTime, default=_utc_now, nullable=False, comment="创建时间")

    # 关系
    discussion = relationship("Discussion", back_populates="messages")
    participant = relationship("Participant", back_populates="messages")

    def to_dict(self):
        participant = self.participant
        return {
            "id": self.id,
            "discussion_id": self.discussion_id,
            "participant_id": self.participant_id,
            "participant_name": participant.name if participant else None,
            "participant_title": participant.title if participant else None,
            "participant_color": participant.color if participant else None,
            "content": self.content,
            "message_type": self.message_type.value if hasattr(self.message_type, 'value') else self.message_type,
            "round_number": self.round_number,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Consensus(Base):
    """共识/分歧表"""
    __tablename__ = "consensuses"

    id = Column(String(36), primary_key=True, comment="共识ID")
    discussion_id = Column(String(36), ForeignKey("discussions.id"), nullable=False, comment="所属讨论ID")
    content = Column(Text, nullable=False, comment="共识/分歧内容")
    consensus_type = Column(
        SQLEnum(ConsensusType, native_enum=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        comment="类型"
    )
    round_number = Column(Integer, default=0, nullable=False, comment="轮次")
    created_at = Column(DateTime, default=_utc_now, nullable=False, comment="创建时间")

    # 关系
    discussion = relationship("Discussion", back_populates="consensuses")

    def to_dict(self):
        return {
            "id": self.id,
            "discussion_id": self.discussion_id,
            "content": self.content,
            "consensus_type": self.consensus_type.value if hasattr(self.consensus_type, 'value') else self.consensus_type,
            "round_number": self.round_number,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
