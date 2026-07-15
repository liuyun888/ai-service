# app/lessons/m04_04_ingest_service.py
"""课次 04.04 · 上游触发 ingest 的业务层（同步）。

上游（管理端 / curl）→ POST /rag/ingest → 本模块：
  1. 校验租户与正文
  2. 落盘到 inbox（模拟「对象存储上传完成」）
  3. 按 (tenant_id, source) 删旧块再写入（幂等 = 04.02 reindex 心智）
  4. 返回 deleted / inserted，供对接方观测

默认内存 TenantIndex（复用 04.03），不依赖本机 Milvus，方便先把接头打通。
"""

from __future__ import annotations

import os
import re
from pathlib import Path

from app.lessons.m02_03_embeddings import default_embedding_model, embed_texts
from app.lessons.m03_03_splitters import split_by_heading
from app.lessons.m04_03_tenant_store import (
    TENANT_FIELD,
    TenantChunk,
    TenantIndex,
    TenantIndexedChunk,
    retrieve_for_tenant,
)

# 上传落盘目录（模拟对象存储落地后再回调）
INBOX_ROOT = Path(__file__).resolve().parents[2] / "samples" / "ingest_inbox"

# 进程内共享索引：API 与演示脚本、检索验收共用同一份
_STORE: TenantIndex | None = None


def get_ingest_token() -> str:
    """鉴权口令：生产应换正式 JWT；本课用环境变量即可。"""
    return os.getenv("INGEST_TOKEN", "dev-ingest-token").strip()


def get_store() -> TenantIndex:
    """懒加载进程内索引。"""
    global _STORE
    if _STORE is None:
        _STORE = TenantIndex(items=[], model=default_embedding_model())
    return _STORE


def reset_store() -> None:
    """测试/演示前清空，避免多次跑脚本脏数据干扰断言。"""
    global _STORE
    _STORE = TenantIndex(items=[], model=default_embedding_model())


def _safe_source_name(source: str) -> str:
    """防止路径穿越：只允许文件名，禁止目录分隔符。"""
    name = (source or "").strip()
    if not name or "/" in name or "\\" in name or ".." in name:
        raise ValueError("source 必须是单独文件名，例如 return_policy.md")
    if not re.match(r"^[\w.\-]+\.(md|txt)$", name, flags=re.UNICODE):
        raise ValueError("source 仅允许 md/txt 文件名（字母数字._-）")
    return name


def inbox_path(tenant_id: str, source: str) -> Path:
    """租户隔离的落盘路径：samples/ingest_inbox/{tenant_id}/{source}。"""
    tid = (tenant_id or "").strip()
    if not tid:
        raise ValueError(f"{TENANT_FIELD} required")
    safe_tid = re.sub(r"[^\w\-]", "_", tid)
    return INBOX_ROOT / safe_tid / _safe_source_name(source)


def delete_by_source_tenant(
    index: TenantIndex,
    *,
    source: str,
    tenant_id: str,
) -> int:
    """按幂等键 (tenant_id, source) 删除旧块。"""
    src = _safe_source_name(source)
    tid = (tenant_id or "").strip()
    before = len(index.items)
    index.items = [
        it
        for it in index.items
        if not (it.chunk.source == src and it.chunk.tenant_id == tid)
    ]
    return before - len(index.items)


def count_by_source_tenant(
    index: TenantIndex,
    *,
    source: str,
    tenant_id: str,
) -> int:
    src = _safe_source_name(source)
    tid = (tenant_id or "").strip()
    return sum(
        1
        for it in index.items
        if it.chunk.source == src and it.chunk.tenant_id == tid
    )


def ingest_text(
    *,
    source: str,
    tenant_id: str,
    text: str,
    strategy: str = "heading",
) -> dict:
    """同步 ingest：落盘 → 删旧 → 切分 Embedding → 写入共享索引。

    返回:
        ok / deleted / inserted / remain / path / tenant_id / source
    """
    tid = (tenant_id or "").strip()
    if not tid:
        raise ValueError(f"{TENANT_FIELD} required")
    body = (text or "").strip()
    if not body:
        raise ValueError("text required for this lesson（file_url 下节再接）")
    if strategy not in {"heading", "fixed"}:
        raise ValueError("strategy 仅支持 heading | fixed")

    src = _safe_source_name(source)
    path = inbox_path(tid, src)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body if body.endswith("\n") else body + "\n", encoding="utf-8")

    # 切分：本课默认 heading；fixed 走 03.02 再包一层 TenantChunk
    if strategy == "heading":
        parts = split_by_heading(path.read_text(encoding="utf-8"), source=src)
        chunks = [
            TenantChunk(
                text=p.text,
                chunk_id=p.chunk_id,
                source=src,
                tenant_id=tid,
                section=p.section,
            )
            for p in parts
        ]
    else:
        from app.lessons.m03_02_splitters import split_fixed

        parts = split_fixed(path.read_text(encoding="utf-8"), source=src)
        chunks = [
            TenantChunk(
                text=p.text,
                chunk_id=p.chunk_id,
                source=src,
                tenant_id=tid,
                section="",
            )
            for p in parts
        ]

    if not chunks:
        raise ValueError("切分结果为空：请检查正文是否过短")

    index = get_store()
    deleted = delete_by_source_tenant(index, source=src, tenant_id=tid)
    vectors = embed_texts([c.text for c in chunks])
    for chunk, vec in zip(chunks, vectors):
        index.items.append(TenantIndexedChunk(chunk=chunk, vector=vec))
    remain = count_by_source_tenant(index, source=src, tenant_id=tid)

    return {
        "ok": True,
        "deleted": deleted,
        "inserted": len(chunks),
        "remain": remain,
        "source": src,
        "tenant_id": tid,
        "path": str(path),
        "strategy": strategy,
    }


def search_after_ingest(
    query: str,
    *,
    tenant_id: str,
    top_k: int = 3,
) -> list[tuple[TenantChunk, float]]:
    """ingest 后验收用检索（强制租户，复用 04.03）。"""
    return retrieve_for_tenant(get_store(), query, tenant_id=tenant_id, top_k=top_k)
