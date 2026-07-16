# app/api/extract.py
"""课次 12.03 · 抽取 API：POST /v1/extract/invoice。

输入：paste 文本 或 ocr_mock + image_id。
输出：校验后的结构化结果；失败带 status（ocr_failed / need_human）。
须带内部头（与 10.04 一致）。
"""

from __future__ import annotations

import logging
from typing import Any, Literal, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.lessons.m12_03_ocr_orchestration import run_invoice_pipeline
from app.security.internal_auth import InternalContext, require_internal_context

router = APIRouter(prefix="/v1/extract", tags=["extract"])
logger = logging.getLogger("ai-service.extract")


class ExtractInvoiceIn(BaseModel):
    """抽取入参。"""

    source: Literal["ocr_mock", "paste"] = Field(
        default="paste",
        description="文本来源：ocr_mock 走 mock OCR；paste 直传 text",
    )
    text: Optional[str] = Field(default=None, description="已有文本时直传")
    image_id: Optional[str] = Field(
        default=None,
        description="ocr_mock 时必填，如 img-1",
    )
    use_chat: bool = Field(
        default=False,
        description="是否真模型抽取；对接：调试开关，默认离线",
    )


class ExtractInvoiceOut(BaseModel):
    """抽取出参。"""

    status: str = Field(description="ok | need_human | ocr_failed")
    data: Optional[dict[str, Any]] = None
    errors: list[str] = Field(default_factory=list)
    ocr: Optional[dict[str, Any]] = None
    wrote_db: bool = False
    attempts: Optional[int] = None
    trace: list[dict[str, Any]] = Field(default_factory=list)
    tenant_id: str = ""
    request_id: str = ""


@router.post("/invoice", response_model=ExtractInvoiceOut)
def extract_invoice_api(
    body: ExtractInvoiceIn,
    ctx: InternalContext = Depends(require_internal_context),
) -> ExtractInvoiceOut:
    """OCR/粘贴 → 抽取 → 校验编排入口。"""
    logger.info(
        "extract_invoice source=%s image_id=%s tenant=%s",
        body.source,
        body.image_id,
        ctx.tenant_id,
    )
    out = run_invoice_pipeline(
        source=body.source,
        text=body.text,
        image_id=body.image_id,
        use_chat=body.use_chat,
    )
    return ExtractInvoiceOut(
        status=str(out.get("status") or "need_human"),
        data=out.get("data"),
        errors=list(out.get("errors") or []),
        ocr=out.get("ocr"),
        wrote_db=bool(out.get("wrote_db")),
        attempts=out.get("attempts"),
        trace=list(out.get("trace") or []),
        tenant_id=ctx.tenant_id,
        request_id=ctx.request_id,
    )
