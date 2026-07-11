# app/models/embeddings.py
"""Embedding 封装：把文本变成真实向量（禁止伪随机/哈希假向量）。

支持两种 Provider（由环境变量 EMBEDDING_PROVIDER 选择）：

1. ``openai``：OpenAI 兼容 Embeddings API（智谱 / 讯飞 MaaS / 其他网关）
2. ``local``：本机 fastembed 真实模型（默认 BAAI/bge-small-zh-v1.5，中文友好）

本课验收以「真 API / 真模型返回的浮点向量 + 余弦相似度」为准。
"""

from __future__ import annotations

import math
import os
from functools import lru_cache
from pathlib import Path
from typing import Sequence

from dotenv import load_dotenv

_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(_ROOT / ".env")


def _provider() -> str:
    return os.getenv("EMBEDDING_PROVIDER", "local").strip().lower() or "local"


def default_embedding_model() -> str:
    """当前 Provider 下的默认模型名。"""
    if _provider() == "local":
        return os.getenv("EMBEDDING_MODEL", "BAAI/bge-small-zh-v1.5").strip()
    return os.getenv("EMBEDDING_MODEL", "embedding-3").strip()


def _openai_client():
    """构造 OpenAI 兼容客户端（Embedding 专用）。"""
    from openai import OpenAI

    api_key = (
        os.getenv("EMBEDDING_API_KEY", "").strip()
        or os.getenv("ZHIPUAI_API_KEY", "").strip()
        or os.getenv("OPENAI_API_KEY", "").strip()
    )
    base_url = (
        os.getenv("EMBEDDING_BASE_URL", "").strip()
        or os.getenv("OPENAI_BASE_URL", "").strip()
    )
    # 智谱常见兼容地址；若未配 BASE_URL 且有智谱 Key，走官方
    if not base_url and os.getenv("ZHIPUAI_API_KEY", "").strip():
        base_url = "https://open.bigmodel.cn/api/paas/v4"
    if not api_key:
        raise RuntimeError(
            "EMBEDDING_PROVIDER=openai 时需要 EMBEDDING_API_KEY / ZHIPUAI_API_KEY / OPENAI_API_KEY"
        )
    if not base_url:
        raise RuntimeError("缺少 EMBEDDING_BASE_URL 或 OPENAI_BASE_URL")
    return OpenAI(api_key=api_key, base_url=base_url)


@lru_cache(maxsize=1)
def _local_model():
    """懒加载本地 Embedding 模型（首次会下载 ONNX，需联网一次）。"""
    try:
        from fastembed import TextEmbedding
    except ImportError as e:
        raise RuntimeError(
            "本地 Embedding 需要 fastembed：pip install 'fastembed>=0.5'"
        ) from e
    return TextEmbedding(model_name=default_embedding_model())


def embed_texts(texts: Sequence[str]) -> list[list[float]]:
    """对多段文本做真实向量化，返回与 texts 等长的向量列表。

    :param texts: 待向量化文本；不可为空列表
    :return: ``list[list[float]]``，同一调用内各向量维度相同
    :raises ValueError: texts 为空
    :raises RuntimeError: Provider / 密钥 / 依赖未就绪
    """
    if not texts:
        raise ValueError("texts 不能为空")

    provider = _provider()
    if provider == "local":
        vectors = [list(map(float, v)) for v in _local_model().embed(list(texts))]
        return vectors

    if provider in {"openai", "zhipu", "api"}:
        client = _openai_client()
        resp = client.embeddings.create(
            model=default_embedding_model(),
            input=list(texts),
        )
        # API 可能乱序，按 index 排回
        ordered = sorted(resp.data, key=lambda d: d.index)
        return [list(map(float, d.embedding)) for d in ordered]

    raise RuntimeError(
        f"未知 EMBEDDING_PROVIDER={provider!r}，请用 local 或 openai"
    )


def cosine(a: list[float], b: list[float]) -> float:
    """余弦相似度，范围约 [-1, 1]；语义越近通常越高。"""
    if len(a) != len(b):
        raise ValueError(f"维度不一致：{len(a)} vs {len(b)}")
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)


def embedding_dim(sample_text: str = "维度探测") -> int:
    """调用一次真实 Embedding，返回维度（与向量库 Collection 契约对齐）。"""
    return len(embed_texts([sample_text])[0])
