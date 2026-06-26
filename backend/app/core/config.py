"""
配置管理模块
从 .env 文件加载环境变量
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# 加载 .env 文件
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(env_path)


class Settings:
    """应用配置类"""
    
    # 应用信息
    APP_NAME: str = os.getenv("APP_NAME", "AssetAllocationAgent")
    DEBUG: bool = os.getenv("DEBUG", "true").lower() == "true"
    
    # 服务器
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    
    # 通义千问 API Key
    DASHSCOPE_API_KEY: str = os.getenv("DASHSCOPE_API_KEY", "")
    
    # LLM 模型选择
    # qwen-max: 最强能力，用于复杂对话
    # qwen-turbo: 快速响应，用于简单通知
    LLM_MODEL_MAIN: str = "qwen-max"
    LLM_MODEL_FAST: str = "qwen-turbo"
    
    # Redis（用于存对话状态）
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    # 数据库
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")


# 全局配置实例
settings = Settings()
