# app/rag/ingest.py
"""Index · 后半：chunk → Embedding → 可检索索引。

本课用 **内存索引**（InMemoryIndex）跑通四步闭环；
03.04 会把同一套 chunk 写入 Milvus Collection。
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.models.embeddings import default_embedding_model, embed_texts
from app.rag.splitters import Chunk


@dataclass
class IndexedChunk:
    """已向量化的单块：原文 + 向量。"""

    chunk: Chunk
    vector: list[float]


@dataclass
class InMemoryIndex:
    """内存版向量库：本课演示用，进程结束即消失。

    :param items: 所有已索引块
    :param model: 建索引时用的 Embedding 模型名（检索必须用同一模型）
    """

    items: list[IndexedChunk] = field(default_factory=list)
    model: str = ""


def build_index(chunks: list[Chunk]) -> InMemoryIndex:
    """对一批 chunk 做真实 Embedding 并建成内存索引。

    :param chunks: splitters 产出的块列表
    :return: 可交给 retriever.retrieve 的索引对象
    :raises ValueError: chunks 为空
    """
    if not chunks:
        raise ValueError("chunks 不能为空，请先切分文档")

    texts = [c.text for c in chunks]
    vectors = embed_texts(texts)
    model = default_embedding_model()

    items = [
        IndexedChunk(chunk=chunk, vector=vec)
        for chunk, vec in zip(chunks, vectors, strict=True)
    ]
    return InMemoryIndex(items=items, model=model)
