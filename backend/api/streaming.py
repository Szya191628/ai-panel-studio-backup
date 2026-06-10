"""SSE流式接口 - 优化版本"""

import json
import asyncio
from datetime import datetime, timezone
from typing import AsyncGenerator
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from backend.core.database import get_db, SessionLocal
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

router = APIRouter()


async def generate_sse_event(event_type: str, data: dict) -> str:
    """生成SSE事件格式"""
    event_data = {
        "event": event_type,
        "data": data,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    return f"data: {json.dumps(event_data, ensure_ascii=False)}\n\n"


def _build_speech_event(discussion_id: str, msg, participant_dict: dict) -> dict:
    """构建发言事件数据"""
    participant = participant_dict.get(msg.participant_id)
    return {
        "discussion_id": discussion_id,
        "message_id": msg.id,
        "participant_id": msg.participant_id,
        "participant_name": participant.name if participant else "未知",
        "participant_title": participant.title if participant else "",
        "participant_color": participant.color if participant else "#000000",
        "content": msg.content,
        "message_type": msg.message_type.value,
        "round_number": msg.round_number,
        "created_at": msg.created_at.isoformat(),
    }


def _build_consensus_event(discussion_id: str, consensus) -> dict:
    """构建共识事件数据"""
    return {
        "discussion_id": discussion_id,
        "consensus": {
            "id": consensus.id,
            "content": consensus.content,
            "consensus_type": consensus.consensus_type.value,
            "round_number": consensus.round_number,
            "created_at": consensus.created_at.isoformat(),
        },
        "action": "add",
    }


async def run_discussion_background(discussion_id: str, topic: str, participants: list[dict], max_rounds: int):
    """后台运行讨论（异步）"""
    try:
        from backend.agents.graph import RoundTableGraph

        # 创建图
        graph = RoundTableGraph(participants, max_rounds)

        # 执行讨论
        result = graph.invoke(discussion_id, topic)

        # 更新讨论状态
        db = SessionLocal()
        try:
            discussion = db.query(Discussion).filter(Discussion.id == discussion_id).first()
            if discussion:
                # 保存所有消息
                from backend.services.discussion_service import DiscussionService
                service = DiscussionService(db)

                for msg in result.get("messages", []):
                    service.add_message(
                        discussion_id=discussion_id,
                        participant_id=msg["participant_id"],
                        content=msg["content"],
                        message_type=MessageType.SPEECH,
                        round_number=msg.get("round", 0),
                    )

                # 更新讨论状态
                if result.get("phase") == "finished":
                    discussion.status = DiscussionStatus.FINISHED
                    discussion.summary = result.get("summary", "")
                elif result.get("error"):
                    discussion.status = DiscussionStatus.FAILED
                else:
                    discussion.status = DiscussionStatus.FINISHED

                db.commit()
        finally:
            db.close()

    except Exception as e:
        # 更新讨论状态为失败
        db = SessionLocal()
        try:
            discussion = db.query(Discussion).filter(Discussion.id == discussion_id).first()
            if discussion:
                discussion.status = DiscussionStatus.FAILED
                db.commit()
        finally:
            db.close()


async def extract_consensus_background(discussion_id: str, topic: str):
    """后台提取共识（异步）"""
    try:
        db = SessionLocal()
        try:
            from backend.services.consensus_service import ConsensusService
            service = ConsensusService(db)
            service.extract_consensus(discussion_id, topic)
        finally:
            db.close()
    except Exception as e:
        print(f"共识提取失败: {e}")


async def discussion_event_stream(
    discussion_id: str,
) -> AsyncGenerator[str, None]:
    """讨论事件流生成器（使用独立session）"""

    # 使用独立的session，不依赖FastAPI的依赖注入
    db = SessionLocal()
    try:
        discussion = db.query(Discussion).filter(Discussion.id == discussion_id).first()
        if not discussion:
            yield await generate_sse_event("error", {"message": "讨论不存在"})
            return

        # 发送讨论状态事件
        yield await generate_sse_event("discussion_status", {
            "discussion_id": discussion_id,
            "status": discussion.status.value,
            "topic": discussion.topic,
            "current_round": discussion.current_round,
            "max_rounds": discussion.max_rounds,
        })

        # 发送参与者列表
        participants = db.query(Participant).filter(
            Participant.discussion_id == discussion_id
        ).all()

        # 构建participant字典，用于O(1)查找
        participant_dict = {p.id: p for p in participants}

        yield await generate_sse_event("participants", {
            "discussion_id": discussion_id,
            "participants": [
                {
                    "id": p.id,
                    "name": p.name,
                    "role": p.role.value,
                    "title": p.title,
                    "stance": p.stance,
                    "color": p.color,
                    "agent_phase": p.agent_phase.value,
                    "focus_point": p.focus_point,
                }
                for p in participants
            ],
        })

        # 发送历史消息
        messages = db.query(Message).filter(
            Message.discussion_id == discussion_id
        ).order_by(Message.created_at.asc()).all()

        # 使用set跟踪已处理的消息ID
        seen_message_ids = set()
        seen_consensus_ids = set()

        for msg in messages:
            yield await generate_sse_event("speech", _build_speech_event(discussion_id, msg, participant_dict))
            seen_message_ids.add(msg.id)

        # 发送共识/分歧
        consensuses = db.query(Consensus).filter(
            Consensus.discussion_id == discussion_id
        ).order_by(Consensus.created_at.asc()).all()

        for c in consensuses:
            yield await generate_sse_event("consensus_update", _build_consensus_event(discussion_id, c))
            seen_consensus_ids.add(c.id)

        # 如果讨论进行中，进入轮询模式
        if discussion.status in [DiscussionStatus.DEBATING, DiscussionStatus.SUMMARIZING]:
            poll_count = 0
            max_polls = 600  # 最多轮询10分钟
            refresh_counter = 0

            while poll_count < max_polls:
                await asyncio.sleep(0.5)  # 每0.5秒轮询一次
                poll_count += 1

                # 检查新消息
                all_messages = db.query(Message).filter(
                    Message.discussion_id == discussion_id,
                ).order_by(Message.created_at.asc()).all()

                new_messages = [m for m in all_messages if m.id not in seen_message_ids]

                for msg in new_messages:
                    yield await generate_sse_event("speech", _build_speech_event(discussion_id, msg, participant_dict))
                    seen_message_ids.add(msg.id)

                # 检查新共识
                all_consensuses = db.query(Consensus).filter(
                    Consensus.discussion_id == discussion_id,
                ).order_by(Consensus.created_at.asc()).all()

                new_consensuses = [c for c in all_consensuses if c.id not in seen_consensus_ids]

                for c in new_consensuses:
                    yield await generate_sse_event("consensus_update", _build_consensus_event(discussion_id, c))
                    seen_consensus_ids.add(c.id)

                # 每5秒刷新一次参与者状态
                refresh_counter += 1
                if refresh_counter >= 10:
                    refresh_counter = 0
                    db.expire_all()
                    participants = db.query(Participant).filter(
                        Participant.discussion_id == discussion_id
                    ).all()
                    participant_dict = {p.id: p for p in participants}

                    yield await generate_sse_event("agent_status", {
                        "discussion_id": discussion_id,
                        "participants": [
                            {
                                "id": p.id,
                                "name": p.name,
                                "agent_phase": p.agent_phase.value,
                                "focus_point": p.focus_point,
                            }
                            for p in participants
                        ],
                    })

                # 检查讨论是否结束
                db.expire(discussion)
                if discussion.status == DiscussionStatus.FINISHED:
                    yield await generate_sse_event("discussion_finished", {
                        "discussion_id": discussion_id,
                        "summary": discussion.summary,
                    })
                    break
                elif discussion.status == DiscussionStatus.FAILED:
                    yield await generate_sse_event("discussion_failed", {
                        "discussion_id": discussion_id,
                        "error": "讨论执行失败",
                    })
                    break

        # 发送完成事件
        yield await generate_sse_event("done", {
            "discussion_id": discussion_id,
            "message": "事件流结束",
        })

    finally:
        db.close()


@router.get("/{discussion_id}")
async def stream_discussion(
    discussion_id: str,
    db: Session = Depends(get_db),
):
    """SSE流式订阅讨论事件"""
    # 只用传入的session做存在性检查
    discussion = db.query(Discussion).filter(Discussion.id == discussion_id).first()
    if not discussion:
        raise HTTPException(status_code=404, detail="讨论不存在")

    return StreamingResponse(
        discussion_event_stream(discussion_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/{discussion_id}/start")
async def start_discussion_stream(
    discussion_id: str,
    db: Session = Depends(get_db),
):
    """启动讨论（异步执行）"""
    discussion = db.query(Discussion).filter(Discussion.id == discussion_id).first()
    if not discussion:
        raise HTTPException(status_code=404, detail="讨论不存在")

    if discussion.status != DiscussionStatus.PENDING:
        raise HTTPException(status_code=400, detail="讨论状态不允许启动")

    # 检查参与者
    participants = db.query(Participant).filter(
        Participant.discussion_id == discussion_id
    ).all()

    experts = [p for p in participants if p.role == ParticipantRole.EXPERT]
    moderators = [p for p in participants if p.role == ParticipantRole.MODERATOR]

    if len(experts) < 2:
        raise HTTPException(status_code=400, detail="专家人数不足")
    if len(moderators) == 0:
        raise HTTPException(status_code=400, detail="缺少主持人")

    # 更新状态为讨论中
    discussion.status = DiscussionStatus.DEBATING
    db.commit()

    # 异步启动讨论
    participant_dicts = [
        {
            "id": p.id,
            "name": p.name,
            "role": p.role.value,
            "title": p.title,
            "stance": p.stance,
            "color": p.color,
        }
        for p in participants
    ]

    asyncio.create_task(
        run_discussion_background(
            discussion_id,
            discussion.topic,
            participant_dicts,
            discussion.max_rounds,
        )
    )

    return {"message": "讨论已启动", "discussion_id": discussion_id}
