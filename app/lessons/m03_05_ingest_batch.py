# app/lessons/m03_05_ingest_batch.py
"""课次 03.05 · 多文档批量切分（检索演示用）。

本文件为 03.05 课件原文，后续课次请勿修改。
"""

from __future__ import annotations

from pathlib import Path

from app.lessons.m03_02_splitters import split_fixed as split_fixed_0302
from app.lessons.m03_03_splitters import Chunk, split_by_heading


def chunks_from_markdown_dir(
    root: Path,
    *,
    strategy: str = "heading",
) -> list[Chunk]:
    """从目录批量读取 Markdown 并切分。"""
    if not root.is_dir():
        raise FileNotFoundError(f"样例目录不存在：{root}")

    paths = sorted(root.glob("*.md"))
    if not paths:
        raise ValueError(f"目录下没有 .md 文件：{root}")

    all_chunks: list[Chunk] = []
    for path in paths:
        text = path.read_text(encoding="utf-8")
        if strategy == "fixed":
            # 固定切分仍用 03.02 实现，再转成 03.03 Chunk
            for c in split_fixed_0302(text, source=path.name):
                all_chunks.append(
                    Chunk(text=c.text, chunk_id=c.chunk_id, source=c.source)
                )
        else:
            all_chunks.extend(split_by_heading(text, source=path.name))
    return all_chunks
