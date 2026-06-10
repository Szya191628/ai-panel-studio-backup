"""数据模型单元测试"""

import pytest
from datetime import datetime, timezone
from pydantic import ValidationError

import sys
sys.path.insert(0, "D:/ai-panel-studio")

from backend.models.enums import (
    DiscussionStatus,
    ParticipantRole,
    AgentPhase,
    ConsensusType,
    MessageType,
)
from backend.models.schemas import (
    DiscussionCreate,
    DiscussionResponse,
    ParticipantCreate,
    ParticipantResponse,
    MessageCreate,
    MessageResponse,
    ConsensusResponse,
    GuestGenerateRequest,
    SSEEvent,
    ConsensusUpdateEvent,
)
from backend.models.state import RoundTableState, create_initial_state, create_agent_config
from backend.models.database import Base, Discussion, Participant, Message, Consensus


# ==================== 枚举测试 ====================

class TestEnums:
    """枚举类型测试"""

    def test_discussion_status_values(self):
        assert DiscussionStatus.PENDING == "pending"
        assert DiscussionStatus.GENERATING == "generating"
        assert DiscussionStatus.CONFIRMING == "confirming"
        assert DiscussionStatus.DEBATING == "debating"
        assert DiscussionStatus.SUMMARIZING == "summarizing"
        assert DiscussionStatus.FINISHED == "finished"
        assert DiscussionStatus.FAILED == "failed"

    def test_participant_role_values(self):
        assert ParticipantRole.MODERATOR == "moderator"
        assert ParticipantRole.EXPERT == "expert"

    def test_agent_phase_values(self):
        assert AgentPhase.IDLE == "idle"
        assert AgentPhase.PREPARING == "preparing"
        assert AgentPhase.SPEAKING == "speaking"
        assert AgentPhase.LISTENING == "listening"

    def test_consensus_type_values(self):
        assert ConsensusType.CONSENSUS == "consensus"
        assert ConsensusType.DISSENSUS == "dissensus"
        assert ConsensusType.INSIGHT == "insight"

    def test_message_type_values(self):
        assert MessageType.SPEECH == "speech"
        assert MessageType.QUESTION == "question"
        assert MessageType.RESPONSE == "response"
        assert MessageType.SUMMARY == "summary"
        assert MessageType.SYSTEM == "system"


# ==================== Schema测试 ====================

class TestDiscussionSchemas:
    """讨论Schema测试"""

    def test_discussion_create_valid(self):
        data = {"topic": "AI与未来教育"}
        schema = DiscussionCreate(**data)
        assert schema.topic == "AI与未来教育"
        assert schema.expert_count == 4
        assert schema.max_rounds == 5

    def test_discussion_create_custom(self):
        data = {"topic": "远程办公", "expert_count": 3, "max_rounds": 4}
        schema = DiscussionCreate(**data)
        assert schema.expert_count == 3
        assert schema.max_rounds == 4

    def test_discussion_create_topic_too_short(self):
        with pytest.raises(ValidationError):
            DiscussionCreate(topic="A")

    def test_discussion_create_topic_too_long(self):
        with pytest.raises(ValidationError):
            DiscussionCreate(topic="A" * 201)

    def test_discussion_create_expert_count_invalid(self):
        with pytest.raises(ValidationError):
            DiscussionCreate(topic="测试话题", expert_count=1)
        with pytest.raises(ValidationError):
            DiscussionCreate(topic="测试话题", expert_count=9)

    def test_discussion_response_valid(self):
        data = {
            "id": "test-id",
            "topic": "测试话题",
            "status": DiscussionStatus.PENDING,
            "expert_count": 4,
            "max_rounds": 5,
            "current_round": 0,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }
        schema = DiscussionResponse(**data)
        assert schema.id == "test-id"
        assert schema.summary is None

    def test_discussion_response_from_attributes(self):
        """测试 from_attributes 配置"""
        assert DiscussionResponse.model_config.get("from_attributes") is True


class TestParticipantSchemas:
    """参与者Schema测试"""

    def test_participant_create_valid(self):
        data = {
            "name": "张教授",
            "role": ParticipantRole.EXPERT,
            "title": "AI研究员",
            "stance": "支持AI发展",
            "color": "#FF0000",
        }
        schema = ParticipantCreate(**data)
        assert schema.name == "张教授"
        assert schema.color == "#FF0000"

    def test_participant_create_invalid_color(self):
        with pytest.raises(ValidationError):
            ParticipantCreate(
                name="张教授",
                role=ParticipantRole.EXPERT,
                title="AI研究员",
                stance="支持AI发展",
                color="red",
            )

    def test_participant_create_name_too_long(self):
        with pytest.raises(ValidationError):
            ParticipantCreate(
                name="A" * 51,
                role=ParticipantRole.EXPERT,
                title="AI研究员",
                stance="支持AI发展",
                color="#FF0000",
            )

    def test_participant_response_has_created_at(self):
        """测试 ParticipantResponse 包含 created_at 字段"""
        assert "created_at" in ParticipantResponse.model_fields

    def test_participant_response_from_attributes(self):
        """测试 from_attributes 配置"""
        assert ParticipantResponse.model_config.get("from_attributes") is True


class TestMessageSchemas:
    """消息Schema测试"""

    def test_message_create_valid(self):
        data = {"content": "这是一条消息"}
        schema = MessageCreate(**data)
        assert schema.content == "这是一条消息"
        assert schema.message_type == MessageType.SPEECH

    def test_message_create_empty_content(self):
        with pytest.raises(ValidationError):
            MessageCreate(content="")


class TestGuestGenerateSchemas:
    """嘉宾生成Schema测试"""

    def test_guest_generate_request_valid(self):
        data = {"topic": "AI与教育", "expert_count": 4}
        schema = GuestGenerateRequest(**data)
        assert schema.topic == "AI与教育"
        assert schema.expert_count == 4


class TestSSEEventSchemas:
    """SSE事件Schema测试"""

    def test_consensus_update_event_action_literal(self):
        """测试 ConsensusUpdateEvent.action 使用 Literal 约束"""
        event = ConsensusUpdateEvent(
            consensus=ConsensusResponse(
                id="test-id",
                discussion_id="disc-id",
                content="测试共识",
                consensus_type=ConsensusType.CONSENSUS,
                round_number=1,
                created_at=datetime.now(timezone.utc),
            ),
            action="add",
        )
        assert event.action == "add"

    def test_consensus_update_event_action_invalid(self):
        """测试无效 action 值被拒绝"""
        with pytest.raises(ValidationError):
            ConsensusUpdateEvent(
                consensus=ConsensusResponse(
                    id="test-id",
                    discussion_id="disc-id",
                    content="测试共识",
                    consensus_type=ConsensusType.CONSENSUS,
                    round_number=1,
                    created_at=datetime.now(timezone.utc),
                ),
                action="invalid_action",
            )


# ==================== State测试 ====================

class TestState:
    """LangGraph状态测试"""

    def test_create_initial_state(self):
        participants = [
            {"id": "1", "name": "专家A", "role": "expert"},
            {"id": "2", "name": "专家B", "role": "expert"},
        ]
        state = create_initial_state(
            topic="测试话题",
            participants=participants,
            max_rounds=5,
        )

        assert state["topic"] == "测试话题"
        assert state["participants"] == participants
        assert state["max_rounds"] == 5
        assert state["round_number"] == 0
        assert state["phase"] == DiscussionStatus.PENDING.value
        assert state["messages"] == []
        assert state["opinions"] == []
        assert state["consensuses"] == []
        assert state["summary"] == ""
        assert state["error"] == ""

    def test_create_agent_config(self):
        config = create_agent_config(
            id="test-id",
            name="张教授",
            role=ParticipantRole.EXPERT.value,
            title="AI研究员",
            stance="支持AI",
            color="#FF0000",
            system_prompt="你是一个专家",
        )

        assert config["id"] == "test-id"
        assert config["name"] == "张教授"
        assert config["role"] == ParticipantRole.EXPERT.value
        assert config["color"] == "#FF0000"

    def test_state_phase_uses_enum_values(self):
        """测试 state phase 使用 DiscussionStatus 枚举值"""
        state = create_initial_state(topic="test", participants=[])
        assert state["phase"] in [s.value for s in DiscussionStatus]


# ==================== ORM模型测试 ====================

class TestORMModels:
    """SQLAlchemy ORM模型测试"""

    def test_discussion_to_dict(self):
        """测试 Discussion.to_dict()"""
        now = datetime.now(timezone.utc)
        d = Discussion(
            id="test-id",
            topic="测试话题",
            status=DiscussionStatus.PENDING,
            expert_count=4,
            max_rounds=5,
            current_round=0,
            created_at=now,
            updated_at=now,
        )
        result = d.to_dict()
        assert result["id"] == "test-id"
        assert result["status"] == "pending"
        assert result["expert_count"] == 4

    def test_participant_to_dict(self):
        """测试 Participant.to_dict()"""
        p = Participant(
            id="test-id",
            discussion_id="disc-id",
            name="张教授",
            role=ParticipantRole.EXPERT,
            title="AI研究员",
            stance="支持AI",
            color="#FF0000",
            agent_phase=AgentPhase.IDLE,
        )
        result = p.to_dict()
        assert result["id"] == "test-id"
        assert result["role"] == "expert"
        assert result["agent_phase"] == "idle"

    def test_message_to_dict(self):
        """测试 Message.to_dict()"""
        m = Message(
            id="test-id",
            discussion_id="disc-id",
            participant_id="part-id",
            content="测试消息",
            message_type=MessageType.SPEECH,
            round_number=1,
        )
        result = m.to_dict()
        assert result["id"] == "test-id"
        assert result["message_type"] == "speech"
        assert result["participant_name"] is None  # participant not loaded

    def test_consensus_to_dict(self):
        """测试 Consensus.to_dict()"""
        c = Consensus(
            id="test-id",
            discussion_id="disc-id",
            content="测试共识",
            consensus_type=ConsensusType.CONSENSUS,
            round_number=1,
        )
        result = c.to_dict()
        assert result["id"] == "test-id"
        assert result["consensus_type"] == "consensus"

    def test_discussion_status_enum_roundtrip(self):
        """测试 SQLEnum 状态值的往返"""
        d = Discussion(
            id="test-id",
            topic="测试",
            status=DiscussionStatus.DEBATING,
            expert_count=4,
        )
        assert d.status == DiscussionStatus.DEBATING
        assert d.status.value == "debating"

    def test_discussion_expert_count_constraint(self):
        """测试 expert_count CHECK 约束存在"""
        # 验证表定义中包含约束
        table = Discussion.__table__
        constraints = [c for c in table.constraints if hasattr(c, 'name')]
        constraint_names = [c.name for c in constraints]
        assert "ck_expert_count_range" in constraint_names


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
