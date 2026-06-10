"""健康检查接口"""

from fastapi import APIRouter, Depends, Response
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.core.database import get_db
from backend.core.config import APP_NAME, APP_VERSION

router = APIRouter()


@router.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "app": APP_NAME,
        "version": APP_VERSION,
    }


@router.get("/health/db")
async def db_health_check(response: Response, db: Session = Depends(get_db)):
    """数据库健康检查"""
    try:
        db.execute(text("SELECT 1"))
        return {
            "status": "healthy",
            "database": "connected",
        }
    except Exception as e:
        response.status_code = 503
        return {
            "status": "unhealthy",
            "database": "disconnected",
            "error": str(e),
        }
