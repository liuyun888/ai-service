# app/rag/splitters.py
"""Index · 前半：把长文档切成可检索的 chunk。

本课提供两种最小切法（03.03 会深入讲 size/overlap/语义边界）：
- split_fixed：固定长度 + 重叠（保底方案）
- split_by_heading：按 Markdown 二级标题 ## 切（更贴语义）
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Chunk:
    """一块可入库、可检索的文本单元。

    :param text: 块正文
    :param chunk_id: 同文档内的序号，从 0 起
    :param source: 来源文件名，便于引用与排错
    """

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
    """固定长度切分（带重叠）。

    :param size: 每块目标字符数（本课用字符近似，生产可换 token）
    :param overlap: 相邻块重复字符数，减轻「答案卡在刀口」
    :raises ValueError: size 非法或 overlap >= size
    """
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
    """按 Markdown 二级标题 ``## `` 切分；无标题则整篇一块。

    适合政策/讲义/SOP：每个 ## 小节往往对应一个可回答的主题。
    """
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
