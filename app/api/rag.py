# app/api/rag.py
"""课次 04.04 · RAG ingest HTTP 接头。

管理端上传完成 → 回调本路由 → 同步写入向量索引。
安全：必须带 X-Ingest-Token（与 .env 中 INGEST_TOKEN 一致）。
"""

from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from app.lessons.m04_04_ingest_service import (
    get_ingest_token,
    ingest_text,
    search_after_ingest,
)
from app.lessons.m04_03_tenant_store import format_tenant_hit

router = APIRouter(prefix="/rag", tags=["rag"])


class IngestRequest(BaseModel):
    """上游回调 body。

    本课必填 text；file_url 留到接对象存储后再开。
    """

    source: str = Field(..., description="文件名，如 return_policy.md；对接：管理端上传后的逻辑名")
    tenant_id: str = Field(..., min_length=1, description="租户 ID；对接：当前登录租户")
    text: str | None = Field(None, description="文档正文；对接：上传后读出的文本")
    strategy: str = Field("heading", description="切分策略 heading|fixed")


class IngestResponse(BaseModel):
    ok: bool
    deleted: int
    inserted: int
    remain: int
    source: str
    tenant_id: str
    path: str
    strategy: str


class SearchResponse(BaseModel):
    tenant_id: str
    query: str
    hits: list[str]


def _check_token(x_ingest_token: str | None) -> None:
    expected = get_ingest_token()
    if not x_ingest_token or x_ingest_token.strip() != expected:
        raise HTTPException(status_code=401, detail="invalid or missing X-Ingest-Token")


@router.post("/ingest", response_model=IngestResponse)
def ingest(
    req: IngestRequest,
    x_ingest_token: str | None = Header(default=None, alias="X-Ingest-Token"),
) -> IngestResponse:
    """文档变更触发向量化（同步）。

    需求点：管理端/对象存储回调 —— 上传完成后通知 ai-service 入库。
    """
    _check_token(x_ingest_token)
    try:
        result = ingest_text(
            source=req.source,
            tenant_id=req.tenant_id,
            text=req.text or "",
            strategy=req.strategy,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return IngestResponse(**result)


@router.get("/search", response_model=SearchResponse)
def search(
    query: str,
    tenant_id: str,
    top_k: int = 3,
    x_ingest_token: str | None = Header(default=None, alias="X-Ingest-Token"),
) -> SearchResponse:
    """ingest 后冒烟检索（仍要租户 + 鉴权，避免裸奔）。

    需求点：验收「上传后能否搜到新政策」；生产可换正式问答链。
    """
    _check_token(x_ingest_token)
    if not query.strip():
        raise HTTPException(status_code=400, detail="query required")
    try:
        hits = search_after_ingest(query, tenant_id=tenant_id, top_k=top_k)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return SearchResponse(
        tenant_id=tenant_id,
        query=query,
        hits=[format_tenant_hit(c, s) for c, s in hits],
    )
