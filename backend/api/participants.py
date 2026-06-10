"""参与者管理接口"""

import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.core.database import get_db
from backend.core.config import MIN_EXPERT_COUNT, MAX_EXPERT_COUNT
from backend.models import (
    Discussion,
    Participant,
    DiscussionStatus,
    ParticipantRole,
    AgentPhase,
    ParticipantCreate,
    ParticipantResponse,
    GuestGenerateRequest,
    GuestGenerateResponse,
)

router = APIRouter()


def _get_discussion_or_404(discussion_id: str, db: Session) -> Discussion:
    """获取讨论或返回404"""
    discussion = db.query(Discussion).filter(Discussion.id == discussion_id).first()
    if not discussion:
        raise HTTPException(status_code=404, detail="讨论不存在")
    return discussion


@router.get("/{discussion_id}", response_model=list[ParticipantResponse])
async def list_participants(
    discussion_id: str,
    db: Session = Depends(get_db),
):
    """获取讨论的参与者列表"""
    _get_discussion_or_404(discussion_id, db)

    participants = db.query(Participant).filter(
        Participant.discussion_id == discussion_id
    ).all()
    return participants


@router.post("/{discussion_id}", response_model=ParticipantResponse)
async def create_participant(
    discussion_id: str,
    request: ParticipantCreate,
    db: Session = Depends(get_db),
):
    """创建参与者"""
    discussion = _get_discussion_or_404(discussion_id, db)

    if discussion.status != DiscussionStatus.PENDING:
        raise HTTPException(
            status_code=400,
            detail="只能在讨论待开始状态时添加参与者"
        )

    # 检查专家人数限制
    if request.role == ParticipantRole.EXPERT:
        expert_count = db.query(Participant).filter(
            Participant.discussion_id == discussion_id,
            Participant.role == ParticipantRole.EXPERT,
        ).count()
        if expert_count >= discussion.expert_count:
            raise HTTPException(
                status_code=400,
                detail=f"专家人数已达到上限 {discussion.expert_count}"
            )

    # 检查主持人唯一性
    if request.role == ParticipantRole.MODERATOR:
        moderator_exists = db.query(Participant).filter(
            Participant.discussion_id == discussion_id,
            Participant.role == ParticipantRole.MODERATOR,
        ).first()
        if moderator_exists:
            raise HTTPException(
                status_code=400,
                detail="主持人已存在，每个讨论只能有一个主持人"
            )

    participant = Participant(
        id=str(uuid.uuid4()),
        discussion_id=discussion_id,
        name=request.name,
        role=request.role,
        title=request.title,
        stance=request.stance,
        color=request.color,
        agent_phase=AgentPhase.IDLE,
    )
    db.add(participant)
    db.commit()
    db.refresh(participant)
    return participant


@router.delete("/{discussion_id}/{participant_id}")
async def delete_participant(
    discussion_id: str,
    participant_id: str,
    db: Session = Depends(get_db),
):
    """删除参与者"""
    participant = db.query(Participant).filter(
        Participant.id == participant_id,
        Participant.discussion_id == discussion_id,
    ).first()
    if not participant:
        raise HTTPException(status_code=404, detail="参与者不存在")

    discussion = _get_discussion_or_404(discussion_id, db)
    if discussion.status != DiscussionStatus.PENDING:
        raise HTTPException(
            status_code=400,
            detail="只能在讨论待开始状态时删除参与者"
        )

    db.delete(participant)
    db.commit()
    return {"message": "参与者已删除"}


@router.post("/{discussion_id}/generate", response_model=GuestGenerateResponse)
async def generate_guests(
    discussion_id: str,
    request: GuestGenerateRequest,
    db: Session = Depends(get_db),
):
    """AI生成嘉宾阵容"""
    discussion = _get_discussion_or_404(discussion_id, db)

    if discussion.status != DiscussionStatus.PENDING:
        raise HTTPException(
            status_code=400,
            detail="只能在讨论待开始状态时生成嘉宾"
        )

    # 验证expert_count在合理范围内
    if request.expert_count < MIN_EXPERT_COUNT or request.expert_count > MAX_EXPERT_COUNT:
        raise HTTPException(
            status_code=400,
            detail=f"专家人数必须在 {MIN_EXPERT_COUNT} 到 {MAX_EXPERT_COUNT} 之间"
        )

    old_status = discussion.status
    try:
        # 更新讨论状态为生成中
        discussion.status = DiscussionStatus.GENERATING
        db.flush()

        # TODO: 调用LLM生成嘉宾（在模块3实现）
        # 这里先返回一个示例嘉宾阵容
        moderator = Participant(
            id=str(uuid.uuid4()),
            discussion_id=discussion_id,
            name="AI主持人",
            role=ParticipantRole.MODERATOR,
            title="资深媒体人",
            stance="中立引导者",
            color="#4A90D9",
            agent_phase=AgentPhase.IDLE,
        )
        db.add(moderator)

        experts = []
        colors = ["#E74C3C", "#2ECC71", "#F39C12", "#9B59B6", "#1ABC9C", "#E67E22", "#3498DB", "#2C3E50"]
        for i in range(request.expert_count):
            expert = Participant(
                id=str(uuid.uuid4()),
                discussion_id=discussion_id,
                name=f"AI专家{i+1}",
                role=ParticipantRole.EXPERT,
                title=f"领域专家{i+1}",
                stance=f"立场{i+1}",
                color=colors[i % len(colors)],
                agent_phase=AgentPhase.IDLE,
            )
            db.add(expert)
            experts.append(expert)

        # 更新讨论状态为确认中
        discussion.status = DiscussionStatus.CONFIRMING
        discussion.expert_count = request.expert_count
        db.commit()

        db.refresh(moderator)
        for e in experts:
            db.refresh(e)

        return GuestGenerateResponse(
            moderator=moderator,
            experts=experts,
        )

    except Exception as e:
        db.rollback()
        # 恢复原始状态
        discussion.status = old_status
        db.commit()
        raise HTTPException(
            status_code=500,
            detail=f"生成嘉宾失败: {str(e)}"
        )
