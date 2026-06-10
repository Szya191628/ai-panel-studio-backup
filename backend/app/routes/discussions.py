"""Discussion routes."""

from __future__ import annotations

import asyncio
import json
from typing import Optional

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.core import PanelCore
from app.sse import sse_manager

router = APIRouter(prefix="/api/discussions", tags=["discussions"])
core = PanelCore()


class CreateDiscussionRequest(BaseModel):
    topic: str
    host: dict
    experts: list[dict]
    max_rounds: int = 5


class SpeakRequest(BaseModel):
    participant_id: str
    content: str
    speech_type: str = "statement"
    reply_to: Optional[int] = None


class EndRequest(BaseModel):
    conclusion: Optional[str] = None


@router.post("")
async def create_discussion(req: CreateDiscussionRequest):
    """Create a new discussion."""
    return await core.create_discussion(
        req.topic, req.host, req.experts, req.max_rounds
    )


@router.get("")
async def list_discussions(
    status: Optional[str] = Query(None),
    limit: int = Query(20),
):
    """List discussions."""
    return await core.list_discussions(status, limit)


@router.get("/{discussion_id}")
async def get_discussion(discussion_id: str):
    """Get discussion details."""
    return await core.get_discussion(discussion_id)


@router.post("/{discussion_id}/confirm")
async def confirm_discussion(discussion_id: str):
    """Confirm guests and start discussion."""
    return await core.confirm_and_start(discussion_id)


@router.post("/{discussion_id}/speak")
async def record_speech(discussion_id: str, req: SpeakRequest):
    """Record a speech."""
    return await core.record_speech(
        discussion_id,
        req.participant_id,
        req.content,
        req.speech_type,
        req.reply_to,
    )


@router.post("/{discussion_id}/generate-speech")
async def generate_speech(discussion_id: str, participant_id: str):
    """Generate and record a speech using AI."""
    return await core.generate_and_record_speech(discussion_id, participant_id)


@router.get("/{discussion_id}/status")
async def get_status(discussion_id: str):
    """Get discussion status."""
    return await core.get_status(discussion_id)


@router.post("/{discussion_id}/end")
async def end_discussion(discussion_id: str, req: EndRequest):
    """End a discussion."""
    return await core.end_discussion(discussion_id, req.conclusion)


@router.post("/{discussion_id}/run")
async def run_discussion(discussion_id: str, max_rounds: Optional[int] = None):
    """Run a full discussion automatically."""
    return await core.run_discussion(discussion_id, max_rounds)


@router.get("/{discussion_id}/events")
async def sse_events(discussion_id: str):
    """SSE endpoint for real-time events."""

    async def event_generator():
        queue = await sse_manager.subscribe(discussion_id)
        try:
            # Send initial ping
            yield "event: ping\ndata: {}\n\n"

            while True:
                try:
                    message = await asyncio.wait_for(queue.get(), timeout=30)
                    event = message["event"]
                    data = json.dumps(message["data"], ensure_ascii=False)
                    yield f"event: {event}\ndata: {data}\n\n"
                except asyncio.TimeoutError:
                    # Send keepalive
                    yield ": keepalive\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            await sse_manager.unsubscribe(discussion_id, queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
