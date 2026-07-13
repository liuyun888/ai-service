# app/lessons/m03_03_splitters.py
"""课次 03.03 · 文档分割对比工具（在 03.02 基础上追加）。

本文件为 03.03 课件原文，后续课次请勿修改。
只 import 03.02 的 split_fixed，不修改 m03_02_splitters.py。
"""

from __future__ import annotations

from dataclasses import dataclass

from app.lessons.m03_02_splitters import split_fixed
from app.lessons.m03_02_splitters import Chunk as Chunk0302


@dataclass
class Chunk:
    """03.03 在 03.02 基础上增加 section 元数据。"""

    text: str
    chunk_id: int
    source: str = ""
    section: str = ""


def _section_from_part(part: str) -> str:
    for line in part.splitlines():
        if line.startswith("## "):
            return line[3:].strip()
    return ""


def split_by_heading(text: str, *, source: str = "") -> list[Chunk]:
    """按 ``## `` 切分，并提取 section 小节名。"""
    parts: list[str] = []
    buf: list[str] = []
    for line in text.splitlines(keepends=True):
        if line.startswith("## ") and buf:
            parts.append("".join(buf))
            buf = [line]
        else:
            buf.append(line)
    if buf:
        parts.append("".join(buf))
    if not parts:
        parts = [text]
    return [
        Chunk(
            text=p.strip(),
            chunk_id=i,
            source=source,
            section=_section_from_part(p),
        )
        for i, p in enumerate(parts)
        if p.strip()
    ]


@dataclass
class SplitCompareResult:
    fixed: list[Chunk0302]
    heading: list[Chunk]
    source: str


def compare_strategies(
    text: str,
    *,
    source: str = "",
    fixed_size: int = 200,
    fixed_overlap: int = 40,
) -> SplitCompareResult:
    """同一文档跑固定切分 vs 按标题切分。"""
    return SplitCompareResult(
        fixed=split_fixed(text, size=fixed_size, overlap=fixed_overlap, source=source),
        heading=split_by_heading(text, source=source),
        source=source,
    )


def find_chunks_containing(chunks: list[Chunk], keyword: str) -> list[Chunk]:
    return [c for c in chunks if keyword in c.text]


def format_chunk_preview(chunk: Chunk | Chunk0302, *, max_len: int = 80) -> str:
    section = getattr(chunk, "section", "") or ""
    meta = f"[{section}] " if section else ""
    body = chunk.text[:max_len].replace("\n", " ")
    suffix = "..." if len(chunk.text) > max_len else ""
    return f"chunk {chunk.chunk_id} {meta}{body}{suffix}"
