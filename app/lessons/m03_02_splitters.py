# app/lessons/m03_02_splitters.py
"""课次 03.02 · Index 前半：把长文档切成可检索的 chunk。

本文件为 03.02 课件原文，后续课次请勿修改。
提供两种最小切法：split_fixed / split_by_heading。
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Chunk:
    """一块可入库、可检索的文本单元。"""

    text: str
    chunk_id: int
    source: str = ""


def split_fixed(
    text: str,
    *,
    size: int = 400,
    overlap: int = 80,
    source: str = "",
) -> list[Chunk]:
    """固定长度切分（带重叠）。"""
    if size <= 0:
        raise ValueError("size 必须为正数")
    if overlap >= size:
        raise ValueError("overlap 必须小于 size")

    chunks: list[Chunk] = []
    i, cid = 0, 0
    while i < len(text):
        piece = text[i : i + size]
        chunks.append(Chunk(text=piece, chunk_id=cid, source=source))
        cid += 1
        i += size - overlap
    return chunks


def split_by_heading(text: str, *, source: str = "") -> list[Chunk]:
    """按 Markdown 二级标题 ``## `` 切分；无标题则整篇一块。"""
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
        Chunk(text=p.strip(), chunk_id=i, source=source)
        for i, p in enumerate(parts)
        if p.strip()
    ]
