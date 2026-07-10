import os
from dotenv import load_dotenv

load_dotenv()


def require_env(name: str, default: str | None = None) -> str:
    value = os.getenv(name, default)
    if value is None or value == "":
        raise RuntimeError(f"环境变量 {name} 未设置，请检查 .env")
    return value


APP_NAME = require_env("APP_NAME", "ai-service")
APP_PORT = int(require_env("APP_PORT", "8001"))
DEFAULT_LLM = require_env("DEFAULT_LLM", "glm")
# 密钥允许本课阶段为空字符串，但键必须存在于 .env
ZHIPUAI_API_KEY = os.getenv("ZHIPUAI_API_KEY", "")
MILVUS_HOST = require_env("MILVUS_HOST", "127.0.0.1")
MILVUS_PORT = int(require_env("MILVUS_PORT", "19530"))