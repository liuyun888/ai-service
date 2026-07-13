# app/rag/splitters.py
"""Index · 前半：把长文档切成可检索的 chunk。

03.02 提供两种最小切法：
- split_fixed：固定长度 + 重叠（保底方案）
- split_by_heading：按 Markdown 二级标题 ## 切（更贴语义）

03.03 追加 compare_strategies / section 元数据，用于两种切法并排对比。
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Chunk:
    """一块可入库、可检索的文本单元。

    :param text: 块正文
    :param chunk_id: 同文档内的序号，从 0 起
    :param source: 来源文件名，便于引用与排错
    :param section: 所属小节标题（按标题切分时有值；固定切分通常为空）
    """

    text: str
    chunk_id: int
    source: str = ""
    section: str = ""


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


def _section_from_part(part: str) -> str:
    """从一块文本里提取第一个 ``## `` 标题，用作 section 元数据。"""
    for line in part.splitlines():
        if line.startswith("## "):
            return line[3:].strip()
    return ""


def split_by_heading(text: str, *, source: str = "") -> list[Chunk]:
    """按 Markdown 二级标题 ``## `` 切分；无标题则整篇一块。

    适合政策/讲义/SOP：每个 ## 小节往往对应一个可回答的主题。
    每块会带上 ``section`` 元数据，便于后续引用与过滤。
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
    """同一文档、两种切法的对比结果（03.03 动手实操用）。"""

    fixed: list[Chunk]
    heading: list[Chunk]
    source: str


def compare_strategies(
    text: str,
    *,
    source: str = "",
    fixed_size: int = 200,
    fixed_overlap: int = 40,
) -> SplitCompareResult:
    """对同一文档跑固定切分 vs 按标题切分，便于并排对比块数与内容完整性。"""
    return SplitCompareResult(
        fixed=split_fixed(
            text, size=fixed_size, overlap=fixed_overlap, source=source
        ),
        heading=split_by_heading(text, source=source),
        source=source,
    )


def find_chunks_containing(chunks: list[Chunk], keyword: str) -> list[Chunk]:
    """找出包含某关键词的块（演示「第 4 步」类问题时哪块更完整）。"""
    return [c for c in chunks if keyword in c.text]


def format_chunk_preview(chunk: Chunk, *, max_len: int = 80) -> str:
    """把一块压成单行预览，方便打印到终端或笔记。"""
    meta = f"[{chunk.section}] " if chunk.section else ""
    body = chunk.text[:max_len].replace("\n", " ")
    suffix = "..." if len(chunk.text) > max_len else ""
    return f"chunk {chunk.chunk_id} {meta}{body}{suffix}"
