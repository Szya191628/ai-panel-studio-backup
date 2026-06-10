"""Configuration management - environment variables only."""

import os
from pathlib import Path

# Database
DATABASE_PATH = os.getenv("DATABASE_PATH", str(Path(__file__).parent.parent / "data" / "panel_studio.db"))

# LLM API (Deepseek V4 Flash)
LLM_API_KEY = os.getenv("LLM_API_KEY", "sk-Gtf1j0Gjnff5sbhP0a59hvIgFRmoDeIKTdDuv0VjT51s7CMF")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.openai-proxy.org/v1")
LLM_MODEL = os.getenv("LLM_MODEL", "deepseek-v4-flash")

# Server
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))
