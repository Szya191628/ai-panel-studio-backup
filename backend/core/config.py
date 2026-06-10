"""应用配置"""

import os
from pathlib import Path
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 项目根目录
BASE_DIR = Path(__file__).resolve().parent.parent

# 数据库配置
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR.parent}/ai_panel_studio.db")

# LLM配置
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "sk-yZOv2EE4CK1ng32lJ7TEZLmjC6SYgiZEk0zku2ENAhxz9oAZ")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.openai-proxy.org/v1")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "qwen3.5-flash")

# 应用配置
APP_NAME = "AI Panel Studio"
APP_VERSION = "0.1.0"
DEBUG = os.getenv("DEBUG", "false").lower() == "true"

# CORS配置
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:5173").split(",")

# 讨论配置
DEFAULT_EXPERT_COUNT = 4
DEFAULT_MAX_ROUNDS = 5
MIN_EXPERT_COUNT = 2
MAX_EXPERT_COUNT = 8
MIN_MAX_ROUNDS = 1
MAX_MAX_ROUNDS = 20
