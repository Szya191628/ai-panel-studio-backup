"""服务层单元测试"""

import pytest
from unittest.mock import patch, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import sys
sys.path.insert(0, "D:/ai-panel-studio")

from backend.models.database import Base
from backend.models import DiscussionStatus, ParticipantRole, ConsensusType
from backend.services.discussion_service import DiscussionService
from backend.services.guest_generator import GuestGeneratorService
from backend.services.consensus_service import ConsensusService


# 使用文件数据库进行测试
TEST_DATABASE_URL = "sqlite:///./test_services.db"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(autouse=True)
def setup_database():
    """每个测试前重建数据库"""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db():
    """获取测试数据库会话"""
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


# ==================== DiscussionService测试 ====================

class TestDiscussionService:
    """讨论管理服务测试"""

    def test_create_discussion(self, db):
        """测试创建讨论"""
        service = DiscussionService(db)
        discussion = service.create_discussion(
            topic="AI与教育",
            expert_count=4,
            max_rounds=5,
        )

        assert discussion.id is not None
        assert discussion.topic == "AI与教育"
        assert discussion.status == DiscussionStatus.PENDING
        assert discussion.expert_count == 4
        assert discussion.max_rounds == 5

    def test_get_discussion(self, db):
        """测试获取讨论"""
        service = DiscussionService(db)
        created = service.create_discussion(topic="测试话题")

        fetched = service.get_discussion(created.id)
        assert fetched is not None
        assert fetched.id == created.id
        assert fetched.topic == "测试话题"

    def test_get_discussion_not_found(self, db):
        """测试获取不存在的讨论"""
        service = DiscussionService(db)
        result = service.get_discussion("nonexistent")
        assert result is None

    def test_list_discussions(self, db):
        """测试获取讨论列表"""
        service = DiscussionService(db)
        service.create_discussion(topic="话题1")
        service.create_discussion(topic="话题2")

        discussions = service.list_discussions()
        assert len(discussions) == 2

    def test_list_discussions_with_status_filter(self, db):
        """测试按状态筛选讨论"""
        service = DiscussionService(db)
        service.create_discussion(topic="话题1")
        service.create_discussion(topic="话题2")

        discussions = service.list_discussions(status=DiscussionStatus.PENDING)
        assert len(discussions) == 2

    def test_delete_discussion(self, db):
        """测试删除讨论"""
        service = DiscussionService(db)
        discussion = service.create_discussion(topic="测试话题")

        result = service.delete_discussion(discussion.id)
        assert result is True

        fetched = service.get_discussion(discussion.id)
        assert fetched is None

    def test_delete_discussion_not_pending(self, db):
        """测试删除非待开始状态的讨论"""
        service = DiscussionService(db)
        discussion = service.create_discussion(topic="测试话题")
        discussion.status = DiscussionStatus.DEBATING
        db.commit()

        with pytest.raises(ValueError, match="只能删除待开始状态的讨论"):
            service.delete_discussion(discussion.id)

    def test_start_discussion(self, db):
        """测试启动讨论"""
        service = DiscussionService(db)
        discussion = service.create_discussion(topic="测试话题", expert_count=2)

        # 添加主持人
        service.create_participant(
            discussion_id=discussion.id,
            name="主持人",
            role=ParticipantRole.MODERATOR,
            title="资深主持人",
            stance="中立",
            color="#4A90D9",
        )

        # 添加专家
        service.create_participant(
            discussion_id=discussion.id,
            name="专家1",
            role=ParticipantRole.EXPERT,
            title="领域专家",
            stance="支持",
            color="#E74C3C",
        )
        service.create_participant(
            discussion_id=discussion.id,
            name="专家2",
            role=ParticipantRole.EXPERT,
            title="领域专家",
            stance="反对",
            color="#2ECC71",
        )

        # 启动讨论
        started = service.start_discussion(discussion.id)
        assert started.status == DiscussionStatus.DEBATING

    def test_start_discussion_without_moderator(self, db):
        """测试没有主持人时启动讨论"""
        service = DiscussionService(db)
        discussion = service.create_discussion(topic="测试话题", expert_count=2)

        # 只添加专家
        service.create_participant(
            discussion_id=discussion.id,
            name="专家1",
            role=ParticipantRole.EXPERT,
            title="领域专家",
            stance="支持",
            color="#E74C3C",
        )
        service.create_participant(
            discussion_id=discussion.id,
            name="专家2",
            role=ParticipantRole.EXPERT,
            title="领域专家",
            stance="反对",
            color="#2ECC71",
        )

        with pytest.raises(ValueError, match="缺少主持人"):
            service.start_discussion(discussion.id)

    def test_start_discussion_without_experts(self, db):
        """测试没有专家时启动讨论"""
        service = DiscussionService(db)
        discussion = service.create_discussion(topic="测试话题", expert_count=2)

        # 只添加主持人
        service.create_participant(
            discussion_id=discussion.id,
            name="主持人",
            role=ParticipantRole.MODERATOR,
            title="资深主持人",
            stance="中立",
            color="#4A90D9",
        )

        with pytest.raises(ValueError, match="专家人数不足"):
            service.start_discussion(discussion.id)

    def test_stop_discussion(self, db):
        """测试停止讨论"""
        service = DiscussionService(db)
        discussion = service.create_discussion(topic="测试话题")

        # 先启动
        service.create_participant(
            discussion_id=discussion.id,
            name="主持人",
            role=ParticipantRole.MODERATOR,
            title="主持人",
            stance="中立",
            color="#4A90D9",
        )
        service.create_participant(
            discussion_id=discussion.id,
            name="专家1",
            role=ParticipantRole.EXPERT,
            title="专家",
            stance="支持",
            color="#E74C3C",
        )
        service.create_participant(
            discussion_id=discussion.id,
            name="专家2",
            role=ParticipantRole.EXPERT,
            title="专家",
            stance="反对",
            color="#2ECC71",
        )
        service.start_discussion(discussion.id)

        # 停止讨论
        stopped = service.stop_discussion(discussion.id)
        assert stopped.status == DiscussionStatus.FINISHED

    def test_update_discussion_status(self, db):
        """测试更新讨论状态"""
        service = DiscussionService(db)
        discussion = service.create_discussion(topic="测试话题")

        updated = service.update_discussion_status(
            discussion.id,
            DiscussionStatus.DEBATING,
        )
        assert updated.status == DiscussionStatus.DEBATING

    def test_update_discussion_round(self, db):
        """测试更新讨论轮次"""
        service = DiscussionService(db)
        discussion = service.create_discussion(topic="测试话题")

        updated = service.update_discussion_round(discussion.id, 3)
        assert updated.current_round == 3

    def test_set_discussion_summary(self, db):
        """测试设置讨论总结"""
        service = DiscussionService(db)
        discussion = service.create_discussion(topic="测试话题")

        updated = service.set_discussion_summary(discussion.id, "这是总结")
        assert updated.summary == "这是总结"
        assert updated.status == DiscussionStatus.FINISHED


# ==================== 参与者管理测试 ====================

class TestParticipantService:
    """参与者管理测试"""

    def test_create_participant(self, db):
        """测试创建参与者"""
        service = DiscussionService(db)
        discussion = service.create_discussion(topic="测试话题")

        participant = service.create_participant(
            discussion_id=discussion.id,
            name="张教授",
            role=ParticipantRole.EXPERT,
            title="AI研究员",
            stance="支持AI",
            color="#FF0000",
        )

        assert participant.id is not None
        assert participant.name == "张教授"
        assert participant.role == ParticipantRole.EXPERT
        assert participant.color == "#FF0000"

    def test_get_participants(self, db):
        """测试获取参与者列表"""
        service = DiscussionService(db)
        discussion = service.create_discussion(topic="测试话题")

        service.create_participant(
            discussion_id=discussion.id,
            name="主持人",
            role=ParticipantRole.MODERATOR,
            title="主持人",
            stance="中立",
            color="#4A90D9",
        )
        service.create_participant(
            discussion_id=discussion.id,
            name="专家1",
            role=ParticipantRole.EXPERT,
            title="专家",
            stance="支持",
            color="#E74C3C",
        )

        participants = service.get_participants(discussion.id)
        assert len(participants) == 2

    def test_update_participant_phase(self, db):
        """测试更新参与者状态"""
        service = DiscussionService(db)
        discussion = service.create_discussion(topic="测试话题")

        participant = service.create_participant(
            discussion_id=discussion.id,
            name="专家",
            role=ParticipantRole.EXPERT,
            title="专家",
            stance="支持",
            color="#E74C3C",
        )

        from backend.models import AgentPhase
        updated = service.update_participant_phase(
            participant.id,
            AgentPhase.SPEAKING,
            "正在讨论AI的影响",
        )

        assert updated.agent_phase == AgentPhase.SPEAKING
        assert updated.focus_point == "正在讨论AI的影响"


# ==================== 消息管理测试 ====================

class TestMessageService:
    """消息管理测试"""

    def test_add_message(self, db):
        """测试添加消息"""
        service = DiscussionService(db)
        discussion = service.create_discussion(topic="测试话题")

        participant = service.create_participant(
            discussion_id=discussion.id,
            name="专家",
            role=ParticipantRole.EXPERT,
            title="专家",
            stance="支持",
            color="#E74C3C",
        )

        from backend.models import MessageType
        message = service.add_message(
            discussion_id=discussion.id,
            participant_id=participant.id,
            content="我认为AI很有前景",
            message_type=MessageType.SPEECH,
            round_number=1,
        )

        assert message.id is not None
        assert message.content == "我认为AI很有前景"
        assert message.round_number == 1

    def test_get_messages(self, db):
        """测试获取消息列表"""
        service = DiscussionService(db)
        discussion = service.create_discussion(topic="测试话题")

        participant = service.create_participant(
            discussion_id=discussion.id,
            name="专家",
            role=ParticipantRole.EXPERT,
            title="专家",
            stance="支持",
            color="#E74C3C",
        )

        from backend.models import MessageType
        service.add_message(
            discussion_id=discussion.id,
            participant_id=participant.id,
            content="消息1",
            message_type=MessageType.SPEECH,
        )
        service.add_message(
            discussion_id=discussion.id,
            participant_id=participant.id,
            content="消息2",
            message_type=MessageType.SPEECH,
        )

        messages = service.get_messages(discussion.id)
        assert len(messages) == 2
        assert messages[0].content == "消息1"
        assert messages[1].content == "消息2"

    def test_get_messages_with_limit(self, db):
        """测试限制消息数量"""
        service = DiscussionService(db)
        discussion = service.create_discussion(topic="测试话题")

        participant = service.create_participant(
            discussion_id=discussion.id,
            name="专家",
            role=ParticipantRole.EXPERT,
            title="专家",
            stance="支持",
            color="#E74C3C",
        )

        from backend.models import MessageType
        for i in range(5):
            service.add_message(
                discussion_id=discussion.id,
                participant_id=participant.id,
                content=f"消息{i}",
                message_type=MessageType.SPEECH,
            )

        messages = service.get_messages(discussion.id, limit=3)
        assert len(messages) == 3


# ==================== 共识管理测试 ====================

class TestConsensusService:
    """共识管理测试"""

    def test_add_consensus(self, db):
        """测试添加共识"""
        service = DiscussionService(db)
        discussion = service.create_discussion(topic="测试话题")

        consensus = service.add_consensus(
            discussion_id=discussion.id,
            content="各方都认为AI很重要",
            consensus_type=ConsensusType.CONSENSUS,
            round_number=1,
        )

        assert consensus.id is not None
        assert consensus.content == "各方都认为AI很重要"
        assert consensus.consensus_type == ConsensusType.CONSENSUS

    def test_get_consensuses(self, db):
        """测试获取共识列表"""
        service = DiscussionService(db)
        discussion = service.create_discussion(topic="测试话题")

        service.add_consensus(
            discussion_id=discussion.id,
            content="共识1",
            consensus_type=ConsensusType.CONSENSUS,
        )
        service.add_consensus(
            discussion_id=discussion.id,
            content="分歧1",
            consensus_type=ConsensusType.DISSENSUS,
        )

        consensuses = service.get_consensuses(discussion.id)
        assert len(consensuses) == 2
        assert consensuses[0].consensus_type == ConsensusType.CONSENSUS
        assert consensuses[1].consensus_type == ConsensusType.DISSENSUS


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
