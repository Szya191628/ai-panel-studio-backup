"""讨论管理接口"""

import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.core.database import get_db
from backend.core.config import (
    DEFAULT_EXPERT_COUNT,
    DEFAULT_MAX_ROUNDS,
    MIN_EXPERT_COUNT,
    MAX_EXPERT_COUNT,
)
from backend.models import (
    Discussion,
    Participant,
    DiscussionStatus,
    DiscussionCreate,
    DiscussionResponse,
    DiscussionListItem,
    ParticipantRole,
    AgentPhase,
)

router = APIRouter()


@router.get("", response_model=list[DiscussionListItem])
async def list_discussions(
    status: DiscussionStatus | None = None,
    db: Session = Depends(get_db),
):
    """获取讨论列表"""
    # 使用子查询一次性获取所有讨论的参与者数量，避免N+1查询
    participant_counts = (
        db.query(
            Participant.discussion_id,
            func.count(Participant.id).label("count"),
        )
        .group_by(Participant.discussion_id)
        .subquery()
    )

    query = db.query(Discussion, participant_counts.c.count).outerjoin(
        participant_counts, Discussion.id == participant_counts.c.discussion_id
    )

    if status:
        query = query.filter(Discussion.status == status)

    results = query.order_by(Discussion.created_at.desc()).all()

    return [
        DiscussionListItem(
            id=d.id,
            topic=d.topic,
            status=d.status,
            participant_count=count or 0,
            created_at=d.created_at,
        )
        for d, count in results
    ]


@router.post("", response_model=DiscussionResponse)
async def create_discussion(
    request: DiscussionCreate,
    db: Session = Depends(get_db),
):
    """创建新讨论"""
    discussion = Discussion(
        id=str(uuid.uuid4()),
        topic=request.topic,
        status=DiscussionStatus.PENDING,
        expert_count=request.expert_count,
        max_rounds=request.max_rounds,
        current_round=0,
    )
    db.add(discussion)
    db.commit()
    db.refresh(discussion)
    return discussion


@router.get("/{discussion_id}", response_model=DiscussionResponse)
async def get_discussion(
    discussion_id: str,
    db: Session = Depends(get_db),
):
    """获取讨论详情"""
    discussion = db.query(Discussion).filter(Discussion.id == discussion_id).first()
    if not discussion:
        raise HTTPException(status_code=404, detail="讨论不存在")
    return discussion


@router.delete("/{discussion_id}")
async def delete_discussion(
    discussion_id: str,
    db: Session = Depends(get_db),
):
    """删除讨论"""
    discussion = db.query(Discussion).filter(Discussion.id == discussion_id).first()
    if not discussion:
        raise HTTPException(status_code=404, detail="讨论不存在")

    # 只允许删除待开始状态的讨论
    if discussion.status != DiscussionStatus.PENDING:
        raise HTTPException(
            status_code=400,
            detail=f"讨论状态为 {discussion.status.value}，只能删除待开始状态的讨论"
        )

    db.delete(discussion)
    db.commit()
    return {"message": "讨论已删除"}


@router.post("/{discussion_id}/start")
async def start_discussion(
    discussion_id: str,
    db: Session = Depends(get_db),
):
    """启动讨论"""
    discussion = db.query(Discussion).filter(Discussion.id == discussion_id).first()
    if not discussion:
        raise HTTPException(status_code=404, detail="讨论不存在")

    if discussion.status != DiscussionStatus.PENDING:
        raise HTTPException(
            status_code=400,
            detail=f"讨论状态为 {discussion.status.value}，无法启动"
        )

    # 检查是否有足够的参与者
    participants = db.query(Participant).filter(
        Participant.discussion_id == discussion_id
    ).all()

    experts = [p for p in participants if p.role == ParticipantRole.EXPERT]
    moderators = [p for p in participants if p.role == ParticipantRole.MODERATOR]

    if len(experts) < MIN_EXPERT_COUNT:
        raise HTTPException(
            status_code=400,
            detail=f"专家人数不足，需要至少 {MIN_EXPERT_COUNT} 位专家"
        )

    if len(moderators) == 0:
        raise HTTPException(
            status_code=400,
            detail="缺少主持人"
        )

    # 更新讨论状态
    discussion.status = DiscussionStatus.DEBATING
    db.commit()

    return {
        "message": "讨论已启动",
        "discussion_id": discussion_id,
        "status": discussion.status.value,
    }


@router.post("/{discussion_id}/stop")
async def stop_discussion(
    discussion_id: str,
    db: Session = Depends(get_db),
):
    """停止讨论"""
    discussion = db.query(Discussion).filter(Discussion.id == discussion_id).first()
    if not discussion:
        raise HTTPException(status_code=404, detail="讨论不存在")

    if discussion.status not in [DiscussionStatus.DEBATING, DiscussionStatus.SUMMARIZING]:
        raise HTTPException(
            status_code=400,
            detail=f"讨论状态为 {discussion.status.value}，无法停止"
        )

    discussion.status = DiscussionStatus.FINISHED
    db.commit()

    return {
        "message": "讨论已停止",
        "discussion_id": discussion_id,
        "status": discussion.status.value,
    }
