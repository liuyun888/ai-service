# app/rag/retriever.py
"""Retrieve：用户问题 → topK 相关 chunk。

在线路径的第一步质量闸门：检索错了，后面 Augment/Generate 再强也会「一本正经地错」。
"""

from __future__ import annotations

from app.models.embeddings import cosine, embed_texts
from app.rag.ingest import InMemoryIndex
from app.rag.splitters import Chunk


def retrieve(
    index: InMemoryIndex,
    query: str,
    *,
    top_k: int = 2,
) -> list[tuple[Chunk, float]]:
    """在内存索引里做向量相似度检索。

    :param index: build_index 返回的索引
    :param query: 用户问题
    :param top_k: 返回最相似的前 K 块
    :return: [(Chunk, 相似度分数), ...] 按分数降序
    """
    if not index.items:
        return []
    if top_k <= 0:
        raise ValueError("top_k 必须为正数")

    q_vec = embed_texts([query])[0]
    scored: list[tuple[Chunk, float]] = []
    for item in index.items:
        score = cosine(q_vec, item.vector)
        scored.append((item.chunk, score))

    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:top_k]
