"""AI圆桌讨论 - 数据模型层"""

from .enums import (
    DiscussionStatus,
    ParticipantRole,
    AgentPhase,
    ConsensusType,
    MessageType,
)
from .schemas import (
    DiscussionCreate,
    DiscussionResponse,
    DiscussionListItem,
    ParticipantCreate,
    ParticipantResponse,
    MessageCreate,
    MessageResponse,
    ConsensusResponse,
    GuestGenerateRequest,
    GuestGenerateResponse,
    SSEEvent,
    SpeechEvent,
    PhaseChangeEvent,
    AgentStatusEvent,
    ConsensusUpdateEvent,
)
from .state import RoundTableState, AgentConfig, StreamEvent
from .database import Base, Discussion, Participant, Message, Consensus

__all__ = [
    # Enums
    "DiscussionStatus",
    "ParticipantRole",
    "AgentPhase",
    "ConsensusType",
    "MessageType",
    # Schemas - Discussion
    "DiscussionCreate",
    "DiscussionResponse",
    "DiscussionListItem",
    # Schemas - Participant
    "ParticipantCreate",
    "ParticipantResponse",
    "GuestGenerateRequest",
    "GuestGenerateResponse",
    # Schemas - Message
    "MessageCreate",
    "MessageResponse",
    # Schemas - Consensus
    "ConsensusResponse",
    # Schemas - SSE Events
    "SSEEvent",
    "SpeechEvent",
    "PhaseChangeEvent",
    "AgentStatusEvent",
    "ConsensusUpdateEvent",
    # State
    "RoundTableState",
    "AgentConfig",
    "StreamEvent",
    # Database
    "Base",
    "Discussion",
    "Participant",
    "Message",
    "Consensus",
]
