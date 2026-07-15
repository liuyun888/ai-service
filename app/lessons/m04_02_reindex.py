# app/lessons/m04_02_reindex.py
"""课次 04.02 · 切片边界诊断 + 按 source 增量 reindex。

两件工程活：
1. 发现「刀口切断」：固定字数切 vs 按标题切，同一文档对比
2. 文档改版后：delete where source=… → 再切分 Embedding 写入（文件粒度替换）

本课不修改 03.03 / 03.04 旧文件；内存索引与 Milvus 两条路径都支持。
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.lessons.m02_03_embeddings import embed_texts
from app.lessons.m03_02_ingest import InMemoryIndex, IndexedChunk, build_index
from app.lessons.m03_03_splitters import (
    Chunk,
    compare_strategies,
    format_chunk_preview,
    split_by_heading,
)
from app.lessons.m03_04_ingest import chunks_from_file
from app.lessons.m03_04_milvus_store import (
    COLLECTION,
    get_milvus_client,
    ingest_chunks_to_milvus,
)


@dataclass
class BoundaryIssue:
    """发现的一切片边界问题（教学用诊断结果）。"""

    strategy: str
    chunk_id: int
    symptom: str
    preview: str


def diagnose_cut_boundary(
    text: str,
    *,
    source: str = "demo.md",
    fixed_size: int = 90,
    fixed_overlap: int = 10,
    keywords: tuple[str, ...] = ("7 个工作日", "| 质量问题", "步骤 4", "到账"),
) -> list[BoundaryIssue]:
    """对比 fixed / heading：若关键词被拆到半截或与表头分离，记一条症状。

    小白直觉：刀切在表格/步骤中间，检索就像只摸到半截绳子。
    """
    cmp = compare_strategies(
        text,
        source=source,
        fixed_size=fixed_size,
        fixed_overlap=fixed_overlap,
    )
    issues: list[BoundaryIssue] = []

    # 1) 表格行被切断：chunk 里只有半行「|」且没有表头
    for c in cmp.fixed:
        lines = [ln for ln in c.text.splitlines() if ln.strip().startswith("|")]
        if not lines:
            continue
        has_header = any("情形" in ln or "运费" in ln for ln in lines)
        has_orphan_row = any(
            ("质量问题" in ln or "错发" in ln) and "情形" not in ln for ln in lines
        )
        if has_orphan_row and not has_header:
            issues.append(
                BoundaryIssue(
                    strategy="fixed",
                    chunk_id=c.chunk_id,
                    symptom="表体与表头分离（或只拿到半截表行）",
                    preview=format_chunk_preview(c, max_len=100),
                )
            )

    # 2) 「7 个工作日」与「步骤 4」是否落在同一块（fixed 常拆开）
    for label, chunks in (("fixed", cmp.fixed), ("heading", cmp.heading)):
        hit_7 = [c for c in chunks if "7 个工作日" in c.text]
        hit_step4 = [c for c in chunks if "4." in c.text and "退款" in c.text]
        if hit_7 and hit_step4:
            same = {c.chunk_id for c in hit_7} & {c.chunk_id for c in hit_step4}
            if not same and label == "fixed":
                issues.append(
                    BoundaryIssue(
                        strategy=label,
                        chunk_id=hit_step4[0].chunk_id,
                        symptom="步骤 4 与『7 个工作日』被切到不同块",
                        preview=format_chunk_preview(hit_step4[0], max_len=100),
                    )
                )

    # 3) heading 应保持小节完整——若关键词整块缺失才报警
    for kw in keywords:
        if kw.startswith("|"):
            continue
        if any(kw in c.text for c in cmp.heading):
            continue
        # 关键词本身不在原文则跳过
        if kw not in text:
            continue
        issues.append(
            BoundaryIssue(
                strategy="heading",
                chunk_id=-1,
                symptom=f"按标题切后仍找不到关键词：{kw}",
                preview="",
            )
        )

    return issues


def count_by_source_memory(index: InMemoryIndex, source: str) -> int:
    """统计内存索引里某个 source 有多少块。"""
    return sum(1 for it in index.items if it.chunk.source == source)


def delete_by_source_memory(index: InMemoryIndex, source: str) -> int:
    """从内存索引删除某 source 的全部块，返回删除条数。"""
    before = len(index.items)
    index.items = [it for it in index.items if it.chunk.source != source]
    return before - len(index.items)


def upsert_chunks_memory(index: InMemoryIndex, chunks: list[Chunk]) -> int:
    """把新 chunk Embedding 后追加进内存索引（调用方应先 delete）。"""
    if not chunks:
        return 0
    # m03_02 Chunk 与 m03_03 Chunk 字段兼容：build_index 要的是带 text 的对象
    from app.lessons.m03_02_splitters import Chunk as Chunk02

    adapted = [
        Chunk02(
            text=c.text,
            chunk_id=c.chunk_id,
            source=c.source,
        )
        for c in chunks
    ]
    texts = [c.text for c in adapted]
    vectors = embed_texts(texts)
    for chunk, vec in zip(adapted, vectors):
        index.items.append(IndexedChunk(chunk=chunk, vector=vec))
    return len(adapted)


def reindex_file_memory(
    index: InMemoryIndex,
    path: Path,
    *,
    strategy: str = "heading",
) -> dict:
    """内存版增量：delete source → 再切分写入。

    返回 deleted / inserted / source，方便脚本打印与写笔记。
    """
    source = path.name
    deleted = delete_by_source_memory(index, source)
    chunks = chunks_from_file(path, strategy=strategy)
    # chunks_from_file 在 fixed 时返回的是 03.03 Chunk；heading 也是
    inserted = upsert_chunks_memory(index, chunks)
    return {
        "source": source,
        "deleted": deleted,
        "inserted": inserted,
        "remain": count_by_source_memory(index, source),
    }


def count_by_source_milvus(source: str) -> int:
    """Milvus 中某 source 的实体数（排障：删干净了没有）。"""
    client = get_milvus_client()
    safe = source.replace('"', '\\"')
    rows = client.query(
        collection_name=COLLECTION,
        filter=f'source == "{safe}"',
        output_fields=["chunk_id"],
        limit=16384,
    )
    return len(rows or [])


def delete_by_source_milvus(source: str) -> int:
    """按 source 删除 Milvus 实体，返回删除前统计到的条数。"""
    before = count_by_source_milvus(source)
    if before == 0:
        return 0
    client = get_milvus_client()
    safe = source.replace('"', '\\"')
    client.delete(collection_name=COLLECTION, filter=f'source == "{safe}"')
    return before


def reindex_file_milvus(path: Path, *, strategy: str = "heading") -> dict:
    """Milvus 版增量：先按 source 删旧，再 ingest 该文件。

    内部仍走 03.04 的 ingest_chunks_to_milvus(replace_sources=True)，
    本函数显式打印 deleted，方便对照「清旧 → 写新」。
    """
    source = path.name
    deleted = delete_by_source_milvus(source)
    chunks = chunks_from_file(path, strategy=strategy)
    # 已手动删过，这里 replace_sources=False 避免重复 delete
    inserted = ingest_chunks_to_milvus(chunks, replace_sources=False)
    remain = count_by_source_milvus(source)
    return {
        "source": source,
        "deleted": deleted,
        "inserted": inserted,
        "remain": remain,
    }


def write_policy_version(path: Path, *, days: int) -> None:
    """写出一版「退款到账」政策，供 reindex 前后对比（不改 samples/docs 原件）。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"""# 降噪耳机 Pro · 退款到账说明

## 适用范围

本说明适用于退货审核通过后的退款到账时效。

## 到账时效

审核通过后 **{days} 个工作日** 到账，节假日顺延。
到账渠道为原支付账户。

## 查询方式

可在「我的订单 → 退款详情」查看进度。
""",
        encoding="utf-8",
    )


def seed_index_from_dir(dir_path: Path) -> InMemoryIndex:
    """把目录下 md 全部 heading 切分后建成内存索引（演示起点）。"""
    paths = sorted(dir_path.glob("*.md"))
    if not paths:
        raise FileNotFoundError(f"目录无 md：{dir_path}")
    chunks: list[Chunk] = []
    for p in paths:
        chunks.extend(split_by_heading(p.read_text(encoding="utf-8"), source=p.name))
    # build_index 要 03.02 Chunk；字段兼容，直接构造
    from app.lessons.m03_02_splitters import Chunk as Chunk02

    adapted = [
        Chunk02(text=c.text, chunk_id=c.chunk_id, source=c.source) for c in chunks
    ]
    return build_index(adapted)
