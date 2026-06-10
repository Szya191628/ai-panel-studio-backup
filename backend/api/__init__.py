"""API路由模块"""

from fastapi import APIRouter

from .health import router as health_router
from .discussions import router as discussions_router
from .participants import router as participants_router
from .streaming import router as streaming_router

# 创建主路由
api_router = APIRouter(prefix="/api")

# 注册子路由
api_router.include_router(health_router, tags=["健康检查"])
api_router.include_router(discussions_router, prefix="/discussions", tags=["讨论管理"])
api_router.include_router(participants_router, prefix="/participants", tags=["参与者管理"])
api_router.include_router(streaming_router, prefix="/streaming", tags=["SSE流"])

__all__ = ["api_router"]
