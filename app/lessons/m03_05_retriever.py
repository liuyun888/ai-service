# app/lessons/m03_05_retriever.py
"""课次 03.05 · 相似度检索（内存 + Milvus + 格式化工具）。

本文件为 03.05 课件原文，后续课次请勿修改。
只 import 03.02 / 03.04 模块，不修改前置课次文件。
"""

from __future__ import annotations

from dataclasses import dataclass

from app.lessons.m03_02_ingest import InMemoryIndex, build_index
from app.lessons.m03_02_retriever import retrieve as retrieve_memory
from app.lessons.m03_03_splitters import Chunk
from app.lessons.m03_04_milvus_store import MilvusIndex, search_milvus

# 03.05 对外 re-export build_index，供演示脚本使用
__all__ = [
    "RetrievedHit",
    "build_index",
    "format_hit",
    "hits_to_retrieved",
    "retrieve",
]


@dataclass
class RetrievedHit:
    text: str
    score: float
    source: str = ""
    section: str = ""
    chunk_id: int = 0

    @classmethod
    def from_tuple(cls, chunk: Chunk, score: float) -> RetrievedHit:
        return cls(
            text=chunk.text,
            score=score,
            source=chunk.source,
            section=chunk.section,
            chunk_id=chunk.chunk_id,
        )


def retrieve(
    index: InMemoryIndex | MilvusIndex,
    query: str,
    *,
    top_k: int = 2,
) -> list[tuple[Chunk, float]]:
    """内存索引走 03.02；Milvus 索引走 03.04 ANN search。"""
    if top_k <= 0:
        raise ValueError("top_k 必须为正数")

    if hasattr(index, "items"):
        return retrieve_memory(index, query, top_k=top_k)
    return search_milvus(index, query, top_k=top_k)


def format_hit(chunk: Chunk, score: float, *, max_len: int = 72) -> str:
    section = f"[{chunk.section}] " if chunk.section else ""
    preview = chunk.text[:max_len].replace("\n", " ")
    suffix = "..." if len(chunk.text) > max_len else ""
    return (
        f"{score:.4f}  {chunk.source}  chunk {chunk.chunk_id}  "
        f"{section}{preview}{suffix}"
    )


def hits_to_retrieved(hits: list[tuple[Chunk, float]]) -> list[RetrievedHit]:
    return [RetrievedHit.from_tuple(c, s) for c, s in hits]
