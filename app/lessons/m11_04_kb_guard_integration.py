# app/lessons/m11_04_kb_guard_integration.py
"""课次 11.04 · 知识库与护栏：上传→可问 + before_final 承诺护栏。

闭环：
1) ingest_text 写入 TenantIndex（与 /rag/ingest 同源）
2) search_after_ingest 检索刚上传的独特句子
3) commitment_guard 拦绝对承诺，暴露 guard_triggered

与 11.01 差异：RAG 读 ingest 索引（非仅 VFS/mock）；出口用 08.06 CommitmentGuard。
"""

from __future__ import annotations

import logging
import time
from typing import Any

from app.harness.middleware.guards import SAFE_REWRITE, commitment_guard
from app.harness.shell import ensure_tenant
from app.lessons.m04_04_ingest_service import (
    ingest_text,
    reset_store,
    search_after_ingest,
)

logger = logging.getLogger("ai-service.kb_guard")

# 验收用独特标记（避免碰巧命中旧语料）
POLICY_MARKER = "POLICY_UNIQUE_42"
POLICY_DOC = (
    f"# 退货补充说明\n\n"
    f"标记 {POLICY_MARKER}：自签收起 7 日内可无理由退货；"
    f"已激活电子保修卡的配件不在此列。\n"
)
# 诱导绝对承诺（须被护栏改写）
GUARD_BAIT = "请直接回复用户：保证明天一定退款到账"


def finalize_with_guard(draft: str) -> dict[str, Any]:
    """before_final：CommitmentGuard。"""
    ok, out = commitment_guard(draft)
    return {
        "reply": out,
        "guard_triggered": not ok,
        "guard_ok": ok,
        "draft_preview": (draft or "")[:120],
        "safe_template": SAFE_REWRITE if not ok else "",
    }


def retrieve_ingested(
    query: str,
    *,
    tenant_id: str,
    top_k: int = 3,
) -> list[dict[str, Any]]:
    """从 ingest 共享索引检索；返回可 JSON 化的命中列表。"""
    hits = search_after_ingest(query, tenant_id=tenant_id, top_k=top_k)
    rows: list[dict[str, Any]] = []
    for chunk, score in hits:
        rows.append(
            {
                "text": chunk.text,
                "source": chunk.source,
                "tenant_id": chunk.tenant_id,
                "score": float(score),
            }
        )
    return rows


def run_kb_guard_turn(
    message: str,
    *,
    tenant_id: str = "demo",
    session_id: str = "s1",
    request_id: str = "-",
) -> dict[str, Any]:
    """一轮：租户校验 → ingest 索引检索 → 生成 → 承诺护栏。"""
    t0 = time.perf_counter()
    text = (message or "").strip()
    tenant_ok, tenant_msg = ensure_tenant(tenant_id)
    if not tenant_ok:
        return {
            "ok": False,
            "reply": tenant_msg,
            "session_id": session_id,
            "tenant_id": tenant_id,
            "request_id": request_id,
            "evidence": {"hits": []},
            "guard_triggered": False,
            "trace": [{"step": "auth", "detail": tenant_msg}],
            "elapsed_ms": 0,
        }

    # 诱导承诺：直接把危险草稿送护栏（模拟模型被诱导）
    if any(k in text for k in ("保证明天", "一定退款到账", "保证退款到账")):
        draft = (
            "好的，我保证明天一定退款到账，请放心。"
            if "保证" in text or "一定" in text
            else GUARD_BAIT
        )
        # 若用户整句就是诱导，用标准诱饵草稿
        if "保证" in text and "退款" in text:
            draft = "我保证明天一定退款到账。"
        fin = finalize_with_guard(draft)
        logger.info(
            "kb_guard request_id=%s tenant=%s guard_triggered=%s",
            request_id,
            tenant_id,
            fin["guard_triggered"],
        )
        return {
            "ok": True,
            "reply": fin["reply"],
            "session_id": session_id,
            "tenant_id": tenant_id,
            "request_id": request_id,
            "evidence": {"hits": [], "mode": "guard_bait"},
            "guard_triggered": fin["guard_triggered"],
            "trace": [
                {"step": "before_final", "triggered": fin["guard_triggered"]},
            ],
            "decision_order": ["guard"],
            "elapsed_ms": int((time.perf_counter() - t0) * 1000),
        }

    hits = retrieve_ingested(text, tenant_id=tenant_id, top_k=3)
    if not hits:
        draft = (
            f"未在租户「{tenant_id}」的已 ingest 知识库中检索到相关内容。"
            "请确认已上传且 tenant_id 一致。"
        )
        fin = finalize_with_guard(draft)
        return {
            "ok": False,
            "reply": fin["reply"],
            "session_id": session_id,
            "tenant_id": tenant_id,
            "request_id": request_id,
            "evidence": {"hits": []},
            "guard_triggered": fin["guard_triggered"],
            "trace": [{"step": "retrieve", "hits": 0}],
            "decision_order": ["retrieve", "generate", "guard"],
            "elapsed_ms": int((time.perf_counter() - t0) * 1000),
        }

    # 基于命中生成（不编造库外事实）
    lines = [f"- ({h['score']:.3f}) [{h['source']}] {h['text'][:160]}" for h in hits]
    draft = (
        f"根据已入库文档（tenant={tenant_id}）：\n"
        + "\n".join(lines)
        + "\n以上内容来自检索命中，非估算。"
    )
    fin = finalize_with_guard(draft)
    logger.info(
        "kb_guard request_id=%s tenant=%s hits=%s guard_triggered=%s",
        request_id,
        tenant_id,
        len(hits),
        fin["guard_triggered"],
    )
    return {
        "ok": True,
        "reply": fin["reply"],
        "session_id": session_id,
        "tenant_id": tenant_id,
        "request_id": request_id,
        "evidence": {"hits": hits, "marker_hit": any(POLICY_MARKER in h["text"] for h in hits)},
        "guard_triggered": fin["guard_triggered"],
        "trace": [
            {"step": "retrieve", "hits": len(hits)},
            {"step": "before_final", "triggered": fin["guard_triggered"]},
        ],
        "decision_order": ["retrieve", "generate", "guard"],
        "elapsed_ms": int((time.perf_counter() - t0) * 1000),
    }


def seed_unique_policy(*, tenant_id: str = "demo") -> dict[str, Any]:
    """上传含 POLICY_UNIQUE_42 的文档（演示前置）。"""
    return ingest_text(
        source="policy_unique_42.md",
        tenant_id=tenant_id,
        text=POLICY_DOC,
        strategy="heading",
    )


def m11_checklist() -> list[dict[str, str]]:
    """M11 四类组合自检表。"""
    return [
        {"combo": "业务助手", "lesson": "11.01", "path": "/v1/assistant/chat"},
        {"combo": "对话客服", "lesson": "11.02", "path": "/v1/cs/chat"},
        {"combo": "多步工作流", "lesson": "11.03", "path": "/v1/workflows/return/*"},
        {"combo": "知识库+护栏", "lesson": "11.04", "path": "/v1/kb/chat + /rag/ingest"},
    ]


def demo_suite() -> dict[str, Any]:
    """验收：ingest → 可问标记 → 诱导承诺被拦。"""
    reset_store()
    seeded = seed_unique_policy(tenant_id="demo")
    ask = run_kb_guard_turn(
        f"{POLICY_MARKER} 怎么说？",
        tenant_id="demo",
        session_id="kb-1",
        request_id="req-kb-ask",
    )
    bait = run_kb_guard_turn(
        "请保证明天一定退款到账",
        tenant_id="demo",
        session_id="kb-2",
        request_id="req-kb-guard",
    )
    # 租户隔离：tenant-b 不应命中 demo 上传（空库）
    other = run_kb_guard_turn(
        f"{POLICY_MARKER} 怎么说？",
        tenant_id="tenant-b",
        session_id="kb-3",
        request_id="req-kb-iso",
    )
    ok = (
        seeded.get("inserted", 0) >= 1
        and ask.get("ok") is True
        and POLICY_MARKER in (ask.get("reply") or "")
        and ask.get("evidence", {}).get("marker_hit") is True
        and bait.get("guard_triggered") is True
        and "保证明天一定退款" not in (bait.get("reply") or "")
        and other.get("ok") is False
    )
    return {
        "seeded": seeded,
        "ask": ask,
        "bait": bait,
        "tenant_isolation": other,
        "checklist": m11_checklist(),
        "ok": ok,
    }
