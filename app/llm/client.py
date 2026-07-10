# app/llm/client.py
"""OpenAI 兼容客户端：全项目只在这里创建，脚本与业务代码统一 import。"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

# 以 ai-service 根目录为基准加载 .env（无论从哪启动都能找到）
_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(_ROOT / ".env")


def make_client() -> OpenAI:
    """创建 OpenAI 兼容客户端：base_url / api_key 来自环境变量。"""
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    base_url = os.getenv("OPENAI_BASE_URL", "").strip()
    if not api_key:
        raise RuntimeError("缺少 OPENAI_API_KEY，请在 .env 中填写控制台 API Key")
    if not base_url:
        raise RuntimeError("缺少 OPENAI_BASE_URL，请在 .env 中填写 OpenAI 兼容地址")
    return OpenAI(api_key=api_key, base_url=base_url)


def default_model() -> str:
    """读取默认模型名，避免各脚本各自写死。"""
    return os.getenv("OPENAI_MODEL", "sensen-code-latest").strip()


def call_chat(
    messages: list[dict[str, str]],
    *,
    temperature: float = 0.2,
    client: OpenAI | None = None,
) -> str:
    """按 messages 角色列表调用 chat.completions，返回模型正文。"""
    c = client or make_client()
    resp = c.chat.completions.create(
        model=default_model(),
        messages=messages,
        temperature=temperature,
    )
    return resp.choices[0].message.content or ""