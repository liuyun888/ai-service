# app/api/workflows.py
"""课次 11.03 · 退货工作流 HTTP：start / resume。

须带内部头；case_id 同时作为 LangGraph thread_id。
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.lessons.m11_03_workflow_integration import (
    resume_return_workflow,
    start_return_workflow,
)
from app.security.internal_auth import InternalContext, require_internal_context

router = APIRouter(prefix="/v1/workflows", tags=["workflows"])
logger = logging.getLogger("ai-service.workflows")


class ReturnStartIn(BaseModel):
    """启动退货工作流。"""

    case_id: str = Field(..., description="案件 id（= thread_id）")
    user_request: str = Field(..., description="用户退货诉求")


class ReturnResumeIn(BaseModel):
    """人工审批后续跑。"""

    case_id: str = Field(..., description="与 start 相同的 case_id")
    approved: bool = Field(..., description="是否批准执行")
    reviewer: str = Field(default="ops_01", description="审核人")
    note: str = Field(default="", description="审核备注")


class WorkflowOut(BaseModel):
    """结构化结果（对齐正文契约）。"""

    ok: bool = True
    case_id: str = ""
    status: str = ""
    risk_level: str = ""
    evidence: list[str] = Field(default_factory=list)
    action_result: str = ""
    user_message: str = ""
    decision: str = ""
    interrupted: bool = False
    interrupt: Any = None
    tenant_id: str = ""
    role_handoff: list[str] = Field(default_factory=list)
    path: list[str] = Field(default_factory=list)
    error: str = ""


def _to_out(view: dict[str, Any]) -> WorkflowOut:
    return WorkflowOut(
        ok=bool(view.get("ok", True)),
        case_id=str(view.get("case_id") or ""),
        status=str(view.get("status") or ""),
        risk_level=str(view.get("risk_level") or ""),
        evidence=list(view.get("evidence") or []),
        action_result=str(view.get("action_result") or ""),
        user_message=str(view.get("user_message") or ""),
        decision=str(view.get("decision") or ""),
        interrupted=bool(view.get("interrupted")),
        interrupt=view.get("interrupt"),
        tenant_id=str(view.get("tenant_id") or ""),
        role_handoff=list(view.get("role_handoff") or []),
        path=list(view.get("path") or []),
        error=str(view.get("error") or ""),
    )


@router.post("/return/start", response_model=WorkflowOut)
def return_start(
    body: ReturnStartIn,
    ctx: InternalContext = Depends(require_internal_context),
) -> WorkflowOut:
    """启动：低风险自动完成；高风险 waiting_human。"""
    logger.info(
        "workflow_start case=%s tenant=%s", body.case_id, ctx.tenant_id
    )
    view = start_return_workflow(
        body.case_id,
        body.user_request,
        tenant_id=ctx.tenant_id,
    )
    return _to_out(view)


@router.post("/return/resume", response_model=WorkflowOut)
def return_resume(
    body: ReturnResumeIn,
    ctx: InternalContext = Depends(require_internal_context),
) -> WorkflowOut:
    """resume：approved=true/false 后续跑至终态。"""
    logger.info(
        "workflow_resume case=%s approved=%s tenant=%s",
        body.case_id,
        body.approved,
        ctx.tenant_id,
    )
    view = resume_return_workflow(
        body.case_id,
        approved=body.approved,
        reviewer=body.reviewer,
        note=body.note,
        tenant_id=ctx.tenant_id,
    )
    return _to_out(view)
