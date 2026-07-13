# app/lessons/m03_02_retriever.py
"""课次 03.02 · Retrieve：内存索引余弦相似度 topK。

本文件为 03.02 课件原文，后续课次请勿修改。
"""

from __future__ import annotations

from app.lessons.m02_03_embeddings import cosine, embed_texts
from app.lessons.m03_02_ingest import InMemoryIndex
from app.lessons.m03_02_splitters import Chunk


def retrieve(
    index: InMemoryIndex,
    query: str,
    *,
    top_k: int = 2,
) -> list[tuple[Chunk, float]]:
    """在内存索引里做向量相似度检索。"""
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
