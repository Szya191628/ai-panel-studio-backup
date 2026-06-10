"""FastAPI application entry point."""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes import discussions, guests

# Ensure data directory exists
data_dir = Path(__file__).parent.parent / "data"
data_dir.mkdir(exist_ok=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

app = FastAPI(
    title="AI Panel Studio",
    description="AI 圆桌讨论 Web App",
    version="1.0.0",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(guests.router)
app.include_router(discussions.router)


@app.get("/")
async def root():
    return {
        "name": "AI Panel Studio",
        "version": "1.0.0",
        "status": "running",
    }


@app.get("/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    from app.config import HOST, PORT

    uvicorn.run("app.main:app", host=HOST, port=PORT, reload=True)
