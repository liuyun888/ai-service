# app/lessons/m03_04_ingest.py
"""课次 03.04 · 向量化入库（Milvus knowledge_base）。

本文件为 03.04 课件原文，后续课次请勿修改。
"""

from __future__ import annotations

from pathlib import Path

from app.lessons.m03_03_splitters import Chunk, split_by_heading
from app.lessons.m03_04_milvus_store import ingest_chunks_to_milvus


def load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def chunks_from_file(path: Path, *, strategy: str = "heading") -> list[Chunk]:
    text = load_text(path)
    if strategy == "fixed":
        from app.lessons.m03_02_splitters import split_fixed as _sf

        return [
            Chunk(text=c.text, chunk_id=c.chunk_id, source=c.source)
            for c in _sf(text, source=path.name)
        ]
    return split_by_heading(text, source=path.name)


def chunks_from_paths(
    paths: list[Path],
    *,
    strategy: str = "heading",
) -> list[Chunk]:
    all_chunks: list[Chunk] = []
    for path in paths:
        all_chunks.extend(chunks_from_file(path, strategy=strategy))
    return all_chunks


def ingest_paths(
    paths: list[Path],
    *,
    strategy: str = "heading",
    replace_sources: bool = True,
    recreate_on_dim_mismatch: bool = False,
) -> int:
    """遍历文件 → 切分 → embed → 写入 Milvus。"""
    if not paths:
        raise ValueError("paths 不能为空")

    chunks = chunks_from_paths(paths, strategy=strategy)
    per_file: dict[str, int] = {}
    for c in chunks:
        per_file[c.source] = per_file.get(c.source, 0) + 1
    for name, n in sorted(per_file.items()):
        print(f"  {name}: {n} chunks")

    return ingest_chunks_to_milvus(
        chunks,
        replace_sources=replace_sources,
        recreate_on_dim_mismatch=recreate_on_dim_mismatch,
    )


def connect_milvus_index():
    from app.lessons.m03_04_milvus_store import connect_milvus_index as _connect

    return _connect()


def count_entities():
    from app.lessons.m03_04_milvus_store import count_entities as _count

    return _count()
