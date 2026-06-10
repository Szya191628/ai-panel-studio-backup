"""讨论管理服务"""

import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session

from backend.models import (
    Discussion,
    Participant,
    Message,
    Consensus,
    DiscussionStatus,
    ParticipantRole,
    AgentPhase,
    MessageType,
    ConsensusType,
)


class DiscussionService:
    """讨论管理服务"""

    def __init__(self, db: Session):
        self.db = db

    def create_discussion(
        self,
        topic: str,
        expert_count: int = 4,
        max_rounds: int = 5,
    ) -> Discussion:
        """创建新讨论"""
        discussion = Discussion(
            id=str(uuid.uuid4()),
            topic=topic,
            status=DiscussionStatus.PENDING,
            expert_count=expert_count,
            max_rounds=max_rounds,
            current_round=0,
        )
        self.db.add(discussion)
        self.db.commit()
        self.db.refresh(discussion)
        return discussion

    def get_discussion(self, discussion_id: str) -> Optional[Discussion]:
        """获取讨论"""
        return self.db.query(Discussion).filter(Discussion.id == discussion_id).first()

    def list_discussions(
        self,
        status: Optional[DiscussionStatus] = None,
    ) -> list[Discussion]:
        """获取讨论列表"""
        query = self.db.query(Discussion)
        if status:
            query = query.filter(Discussion.status == status)
        return query.order_by(Discussion.created_at.desc()).all()

    def delete_discussion(self, discussion_id: str) -> bool:
        """删除讨论"""
        discussion = self.get_discussion(discussion_id)
        if not discussion:
            return False

        if discussion.status != DiscussionStatus.PENDING:
            raise ValueError("只能删除待开始状态的讨论")

        self.db.delete(discussion)
        self.db.commit()
        return True

    def start_discussion(self, discussion_id: str) -> Discussion:
        """启动讨论"""
        discussion = self.get_discussion(discussion_id)
        if not discussion:
            raise ValueError("讨论不存在")

        if discussion.status != DiscussionStatus.PENDING:
            raise ValueError(f"讨论状态为 {discussion.status.value}，无法启动")

        # 检查参与者
        participants = self.get_participants(discussion_id)
        experts = [p for p in participants if p.role == ParticipantRole.EXPERT]
        moderators = [p for p in participants if p.role == ParticipantRole.MODERATOR]

        if len(experts) < 2:
            raise ValueError("专家人数不足，需要至少 2 位专家")

        if len(moderators) == 0:
            raise ValueError("缺少主持人")

        # 更新状态
        discussion.status = DiscussionStatus.DEBATING
        self.db.commit()
        self.db.refresh(discussion)
        return discussion

    def stop_discussion(self, discussion_id: str) -> Discussion:
        """停止讨论"""
        discussion = self.get_discussion(discussion_id)
        if not discussion:
            raise ValueError("讨论不存在")

        if discussion.status not in [DiscussionStatus.DEBATING, DiscussionStatus.SUMMARIZING]:
            raise ValueError(f"讨论状态为 {discussion.status.value}，无法停止")

        discussion.status = DiscussionStatus.FINISHED
        self.db.commit()
        self.db.refresh(discussion)
        return discussion

    def update_discussion_status(
        self,
        discussion_id: str,
        status: DiscussionStatus,
    ) -> Discussion:
        """更新讨论状态"""
        discussion = self.get_discussion(discussion_id)
        if not discussion:
            raise ValueError("讨论不存在")

        discussion.status = status
        self.db.commit()
        self.db.refresh(discussion)
        return discussion

    def update_discussion_round(
        self,
        discussion_id: str,
        current_round: int,
    ) -> Discussion:
        """更新讨论轮次"""
        discussion = self.get_discussion(discussion_id)
        if not discussion:
            raise ValueError("讨论不存在")

        discussion.current_round = current_round
        self.db.commit()
        self.db.refresh(discussion)
        return discussion

    def set_discussion_summary(
        self,
        discussion_id: str,
        summary: str,
    ) -> Discussion:
        """设置讨论总结"""
        discussion = self.get_discussion(discussion_id)
        if not discussion:
            raise ValueError("讨论不存在")

        discussion.summary = summary
        discussion.status = DiscussionStatus.FINISHED
        self.db.commit()
        self.db.refresh(discussion)
        return discussion

    # ==================== 参与者管理 ====================

    def get_participants(self, discussion_id: str) -> list[Participant]:
        """获取讨论的参与者列表"""
        return self.db.query(Participant).filter(
            Participant.discussion_id == discussion_id
        ).all()

    def get_participant(self, participant_id: str) -> Optional[Participant]:
        """获取参与者"""
        return self.db.query(Participant).filter(
            Participant.id == participant_id
        ).first()

    def create_participant(
        self,
        discussion_id: str,
        name: str,
        role: ParticipantRole,
        title: str,
        stance: str,
        color: str,
    ) -> Participant:
        """创建参与者"""
        participant = Participant(
            id=str(uuid.uuid4()),
            discussion_id=discussion_id,
            name=name,
            role=role,
            title=title,
            stance=stance,
            color=color,
            agent_phase=AgentPhase.IDLE,
        )
        self.db.add(participant)
        self.db.commit()
        self.db.refresh(participant)
        return participant

    def update_participant_phase(
        self,
        participant_id: str,
        phase: AgentPhase,
        focus_point: Optional[str] = None,
    ) -> Participant:
        """更新参与者状态"""
        participant = self.get_participant(participant_id)
        if not participant:
            raise ValueError("参与者不存在")

        participant.agent_phase = phase
        if focus_point is not None:
            participant.focus_point = focus_point
        self.db.commit()
        self.db.refresh(participant)
        return participant

    # ==================== 消息管理 ====================

    def add_message(
        self,
        discussion_id: str,
        participant_id: str,
        content: str,
        message_type: MessageType = MessageType.SPEECH,
        round_number: int = 0,
    ) -> Message:
        """添加消息"""
        # 验证参与者存在且属于该讨论
        participant = self.get_participant(participant_id)
        if not participant or participant.discussion_id != discussion_id:
            raise ValueError("参与者不存在或不属于该讨论")

        message = Message(
            id=str(uuid.uuid4()),
            discussion_id=discussion_id,
            participant_id=participant_id,
            content=content,
            message_type=message_type,
            round_number=round_number,
        )
        self.db.add(message)
        self.db.commit()
        self.db.refresh(message)
        return message

    def get_messages(
        self,
        discussion_id: str,
        limit: Optional[int] = None,
    ) -> list[Message]:
        """获取消息列表"""
        query = self.db.query(Message).filter(
            Message.discussion_id == discussion_id
        ).order_by(Message.created_at.asc())

        if limit is not None and limit >= 0:
            query = query.limit(limit)

        return query.all()

    # ==================== 共识管理 ====================

    def add_consensus(
        self,
        discussion_id: str,
        content: str,
        consensus_type: ConsensusType,
        round_number: int = 0,
    ) -> Consensus:
        """添加共识/分歧"""
        consensus = Consensus(
            id=str(uuid.uuid4()),
            discussion_id=discussion_id,
            content=content,
            consensus_type=consensus_type,
            round_number=round_number,
        )
        self.db.add(consensus)
        self.db.commit()
        self.db.refresh(consensus)
        return consensus

    def get_consensuses(self, discussion_id: str) -> list[Consensus]:
        """获取共识列表"""
        return self.db.query(Consensus).filter(
            Consensus.discussion_id == discussion_id
        ).order_by(Consensus.created_at.asc()).all()
