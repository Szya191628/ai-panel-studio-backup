"""Guest generation routes."""

from __future__ import annotations

import json

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.core import PanelCore

router = APIRouter(prefix="/api/guests", tags=["guests"])
core = PanelCore()


class GenerateRequest(BaseModel):
    topic: str
    expert_count: int = 4
    language: str = "zh"


@router.post("/generate")
async def generate_guests(req: GenerateRequest):
    """Generate host and expert profiles for a topic."""
    return await core.generate_guests(req.topic, req.expert_count)


@router.post("/generate/stream")
async def generate_guests_stream(req: GenerateRequest):
    """Generate host and expert profiles with streaming progress."""

    async def event_generator():
        # 发送开始事件
        yield f"data: {json.dumps({'type': 'start', 'message': '正在连接 AI 服务...'}, ensure_ascii=False)}\n\n"

        # 发送进度事件
        yield f"data: {json.dumps({'type': 'progress', 'step': 1, 'message': '正在分析话题...'}, ensure_ascii=False)}\n\n"

        # 调用生成
        result = await core.generate_guests(req.topic, req.expert_count)

        yield f"data: {json.dumps({'type': 'progress', 'step': 2, 'message': '正在生成嘉宾信息...'}, ensure_ascii=False)}\n\n"

        # 发送结果
        yield f"data: {json.dumps({'type': 'complete', 'data': result}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
