# app/models/embeddings.py
"""Embedding 封装：把文本变成真实向量（禁止伪随机/哈希假向量）。

【小白直觉】
Chat 模型吐的是「下一句话」；Embedding 模型吐的是「一串固定长度的小数」。
这串小数叫向量，语义相近的句子，向量在空间里更靠近——所以能做检索。

支持两种 Provider（环境变量 EMBEDDING_PROVIDER）：
1. openai —— 调云端 OpenAI 兼容 Embeddings API（智谱 / 讯飞等）
2. local  —— 本机 fastembed 真模型（默认 BAAI/bge-small-zh-v1.5）

本课验收：真模型返回的浮点向量 + 余弦相似度，不要用 random/哈希假向量。
"""

from __future__ import annotations

import math
import os
from functools import lru_cache
from pathlib import Path
from typing import Sequence

from dotenv import load_dotenv

# embeddings.py 在 app/models/ 下，parents[2] = ai-service 根目录
_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(_ROOT / ".env")


def _provider() -> str:
    """读取当前用哪家 Embedding：local / openai（默认 local，跟课零门槛）。"""
    return os.getenv("EMBEDDING_PROVIDER", "local").strip().lower() or "local"


def default_embedding_model() -> str:
    """当前 Provider 下的默认模型名。

    - local：中文友好的 bge-small-zh（输出维度 512）
    - openai：常见如智谱 embedding-3（维度可配，常 1024/2048）
    """
    if _provider() == "local":
        return os.getenv("EMBEDDING_MODEL", "BAAI/bge-small-zh-v1.5").strip()
    return os.getenv("EMBEDDING_MODEL", "embedding-3").strip()


def _openai_client():
    """构造「只用于 Embedding」的 OpenAI 兼容客户端。

    Key / Base URL 查找顺序：
    1. EMBEDDING_*（专用，优先）
    2. 退回 ZHIPUAI_API_KEY / OPENAI_API_KEY
    注意：对话用的 Coding Plan 网关往往没有 /embeddings，别和 Chat 地址混为一谈。
    """
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
    # 有智谱 Key、但没写 BASE_URL 时，走智谱官方兼容地址
    if not base_url and os.getenv("ZHIPUAI_API_KEY", "").strip():
        base_url = "https://open.bigmodel.cn/api/paas/v4"
    if not api_key:
        raise RuntimeError(
            "EMBEDDING_PROVIDER=openai 时需要 "
            "EMBEDDING_API_KEY / ZHIPUAI_API_KEY / OPENAI_API_KEY"
        )
    if not base_url:
        raise RuntimeError("缺少 EMBEDDING_BASE_URL 或 OPENAI_BASE_URL")
    return OpenAI(api_key=api_key, base_url=base_url)


@lru_cache(maxsize=1)
def _local_model():
    """懒加载本地 Embedding 模型。

    lru_cache：整个进程只加载一次，避免每次 embed 都重新读盘。
    第一次运行会下载 ONNX 模型文件，需要联网。
    """
    try:
        from fastembed import TextEmbedding
    except ImportError as e:
        raise RuntimeError(
            "本地 Embedding 需要 fastembed：pip install 'fastembed>=0.5'"
        ) from e
    return TextEmbedding(model_name=default_embedding_model())


def embed_texts(texts: Sequence[str]) -> list[list[float]]:
    """对多段文本做真实向量化。

    :param texts: 待向量化文本列表，例如 ["句1", "句2"]
    :return: 与 texts 等长的向量列表；同一批内每条维度相同
    :raises ValueError: texts 为空
    :raises RuntimeError: Provider / 密钥 / 依赖未就绪
    """
    if not texts:
        raise ValueError("texts 不能为空")

    provider = _provider()

    # ----- 本机真模型 -----
    if provider == "local":
        # fastembed 返回的是可迭代对象，转成 list[float] 方便后面算余弦
        vectors = [list(map(float, v)) for v in _local_model().embed(list(texts))]
        return vectors

    # ----- 云端 OpenAI 兼容 Embeddings API -----
    if provider in {"openai", "zhipu", "api"}:
        client = _openai_client()
        resp = client.embeddings.create(
            model=default_embedding_model(),
            input=list(texts),
        )
        # 有的网关返回顺序会乱，按 index 排回与输入一致
        ordered = sorted(resp.data, key=lambda d: d.index)
        return [list(map(float, d.embedding)) for d in ordered]

    raise RuntimeError(
        f"未知 EMBEDDING_PROVIDER={provider!r}，请用 local 或 openai"
    )


def cosine(a: list[float], b: list[float]) -> float:
    """余弦相似度：衡量两个向量「方向」有多像。

    公式：dot(a,b) / (|a| * |b|)
    范围大约 [-1, 1]；语义越近通常越高（同模型、同任务下对比才有意义）。

    :raises ValueError: 两条向量长度（维度）不一致
    """
    if len(a) != len(b):
        raise ValueError(f"维度不一致：{len(a)} vs {len(b)}")
    # 点积
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    # 各自的欧氏长度（L2 范数）
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    if na == 0.0 or nb == 0.0:
        return 0.0  # 零向量没有方向，约定相似度为 0
    return dot / (na * nb)


def embedding_dim(sample_text: str = "维度探测") -> int:
    """探测当前模型输出多少维。

    写入 Milvus 前必须与 Collection 声明的 dim 一致，否则入库失败。
    """
    return len(embed_texts([sample_text])[0])
