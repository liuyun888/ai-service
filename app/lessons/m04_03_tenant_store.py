# app/lessons/m04_03_tenant_store.py
"""课次 04.03 · 多库隔离（tenant metadata 过滤 + Collection 命名约定）。

本课落地三件事（教学向最小实现）：
1. 入库时每条 chunk 带 tenant_id
2. 检索必须传 tenant_id；缺省直接报错（禁止默认同查全库）
3. 对照「漏过滤」会串库——隔离发生在检索层，不是 Prompt 里写「请忽略别家」

硬隔离提示：生产可用 collection_for_tenant() 给每租户单独 Collection；
本课默认用「同库 + 强制 metadata 过滤」验证互不串库，零额外 Milvus 运维成本。

不修改 m03_05_retriever.py。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from app.lessons.m02_03_embeddings import cosine, default_embedding_model, embed_texts
from app.lessons.m03_03_splitters import split_by_heading

# 字段名只在这一处定义，入库与查询必须用同一个常量（防「约定漂移」）
TENANT_FIELD = "tenant_id"


@dataclass
class TenantChunk:
    """带租户标签的检索单元。

    tenant_id 与 source 一起构成「这块知识属于谁、来自哪份文件」。
    """

    text: str
    chunk_id: int
    source: str
    tenant_id: str
    section: str = ""


@dataclass
class TenantIndexedChunk:
    chunk: TenantChunk
    vector: list[float]


@dataclass
class TenantIndex:
    """教学用内存多租户索引：物理上一个 list，逻辑上靠 tenant_id 过滤。"""

    items: list[TenantIndexedChunk] = field(default_factory=list)
    model: str = ""


def collection_for_tenant(tenant_id: str) -> str:
    """硬隔离命名约定：每租户一个 Collection（本课演示脚本默认不用，仅作对照）。

    例：tenant_a → kb_tenant_a
    """
    tid = (tenant_id or "").strip()
    if not tid:
        raise ValueError(f"{TENANT_FIELD} required for collection naming")
    safe = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in tid)
    return f"kb_{safe}"


def _require_tenant_id(tenant_id: str | None) -> str:
    """默认拒绝：空租户绝不查全库。"""
    tid = (tenant_id or "").strip()
    if not tid:
        raise ValueError(f"{TENANT_FIELD} required；禁止无租户查全库")
    return tid


def load_tenant_markdown_dir(
    root: Path,
    *,
    tenant_id: str,
) -> list[TenantChunk]:
    """读取某租户目录下全部 .md，按标题切分并打上 tenant_id。"""
    tid = _require_tenant_id(tenant_id)
    if not root.is_dir():
        raise FileNotFoundError(f"租户目录不存在：{root}")

    chunks: list[TenantChunk] = []
    for path in sorted(root.glob("*.md")):
        parts = split_by_heading(path.read_text(encoding="utf-8"), source=path.name)
        for p in parts:
            chunks.append(
                TenantChunk(
                    text=p.text,
                    chunk_id=p.chunk_id,
                    source=path.name,
                    tenant_id=tid,
                    section=p.section,
                )
            )
    if not chunks:
        raise ValueError(f"租户 {tid} 目录无可用 chunk：{root}")
    return chunks


def build_tenant_index(chunks: list[TenantChunk]) -> TenantIndex:
    """对带租户标签的 chunk 做真实 Embedding。"""
    if not chunks:
        raise ValueError("chunks 不能为空")
    for c in chunks:
        _require_tenant_id(c.tenant_id)

    vectors = embed_texts([c.text for c in chunks])
    items = [
        TenantIndexedChunk(chunk=c, vector=v) for c, v in zip(chunks, vectors)
    ]
    return TenantIndex(items=items, model=default_embedding_model())


def build_index_from_tenant_roots(tenant_dirs: dict[str, Path]) -> TenantIndex:
    """一次建好多租户混存索引（模拟「同 Collection + metadata」）。

    参数:
        tenant_dirs: {tenant_id: 该租户文档目录}
    """
    all_chunks: list[TenantChunk] = []
    for tid, path in sorted(tenant_dirs.items()):
        all_chunks.extend(load_tenant_markdown_dir(path, tenant_id=tid))
    return build_tenant_index(all_chunks)


def count_by_tenant(index: TenantIndex, tenant_id: str) -> int:
    tid = _require_tenant_id(tenant_id)
    return sum(1 for it in index.items if it.chunk.tenant_id == tid)


def retrieve_for_tenant(
    index: TenantIndex,
    query: str,
    *,
    tenant_id: str,
    top_k: int = 4,
) -> list[tuple[TenantChunk, float]]:
    """租户隔离检索：先强制 tenant_id，再在该租户子集里算余弦 topK。

    抛出:
        ValueError: 未提供 tenant_id（安全默认）
    """
    tid = _require_tenant_id(tenant_id)
    if top_k <= 0:
        raise ValueError("top_k 必须为正数")

    # 关键：过滤发生在算相似度之前/之中，不是进 Prompt 之后
    pool = [it for it in index.items if it.chunk.tenant_id == tid]
    if not pool:
        return []

    q_vec = embed_texts([query])[0]
    scored: list[tuple[TenantChunk, float]] = []
    for item in pool:
        scored.append((item.chunk, cosine(q_vec, item.vector)))
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:top_k]


def retrieve_without_tenant_filter(
    index: TenantIndex,
    query: str,
    *,
    top_k: int = 4,
) -> list[tuple[TenantChunk, float]]:
    """【反面教材】漏写租户过滤 = 查全库，极易串库。

    生产代码不应暴露此函数；演示脚本用来对照「为什么默认拒绝」。
    """
    if top_k <= 0:
        raise ValueError("top_k 必须为正数")
    if not index.items:
        return []

    q_vec = embed_texts([query])[0]
    scored = [
        (it.chunk, cosine(q_vec, it.vector)) for it in index.items
    ]
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:top_k]


def format_tenant_hit(chunk: TenantChunk, score: float, *, max_len: int = 72) -> str:
    """一行预览：分数 / 租户 / 来源 / 正文片段。"""
    section = f"[{chunk.section}] " if chunk.section else ""
    preview = chunk.text[:max_len].replace("\n", " ")
    suffix = "..." if len(chunk.text) > max_len else ""
    return (
        f"{score:.4f}  {TENANT_FIELD}={chunk.tenant_id}  "
        f"source={chunk.source}  chunk {chunk.chunk_id}  "
        f"{section}{preview}{suffix}"
    )
