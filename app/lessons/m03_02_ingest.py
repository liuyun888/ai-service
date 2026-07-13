# app/lessons/m03_02_ingest.py
"""课次 03.02 · Index 后半：chunk → Embedding → 内存索引。

本文件为 03.02 课件原文，后续课次请勿修改。
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.lessons.m02_03_embeddings import default_embedding_model, embed_texts
from app.lessons.m03_02_splitters import Chunk


@dataclass
class IndexedChunk:
    chunk: Chunk
    vector: list[float]


@dataclass
class InMemoryIndex:
    items: list[IndexedChunk] = field(default_factory=list)
    model: str = ""


def build_index(chunks: list[Chunk]) -> InMemoryIndex:
    """对一批 chunk 做真实 Embedding 并建成内存索引。"""
    if not chunks:
        raise ValueError("chunks 不能为空，请先切分文档")

    texts = [c.text for c in chunks]
    vectors = embed_texts(texts)
    model = default_embedding_model()

    if len(chunks) != len(vectors):
        raise ValueError("chunk 数与向量数不一致")

    items = [
        IndexedChunk(chunk=chunk, vector=vec)
        for chunk, vec in zip(chunks, vectors)
    ]
    return InMemoryIndex(items=items, model=model)
