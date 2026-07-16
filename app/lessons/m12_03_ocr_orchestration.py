# app/lessons/m12_03_ocr_orchestration.py
"""课次 12.03 · OCR/上游 → 抽取 → 校验 编排（非 OCR 算法）。

边界：
1) 先拿文本（paste 或 mock OCR）
2) 质量门：空/过短 → 不调用抽取
3) 抽取 + 12.02 有限重试校验
4) 仅 ok 时标记可写入（本课不真入库，回显 wrote_db）
"""

from __future__ import annotations

from typing import Any

from app.chains.extract import extract_invoice
from app.chains.extract_validate import extract_with_retry
from app.ocr.mock_ocr import MIN_TEXT_LEN, mock_ocr


def run_invoice_pipeline(
    *,
    source: str = "paste",
    text: str | None = None,
    image_id: str | None = None,
    use_chat: bool = False,
    max_retries: int = 2,
) -> dict[str, Any]:
    """跑通一条发票抽取编排。

    参数:
        source: ocr_mock | paste
        text: paste 时直传文本
        image_id: ocr_mock 时必填
        use_chat: 是否真模型抽取（默认 False 离线）
        max_retries: 校验重试次数上限

    返回 status: ok | need_human | ocr_failed
    """
    trace: list[dict[str, Any]] = []
    ocr_meta: dict[str, Any] | None = None
    src = (source or "paste").strip().lower()

    # —— 1) 取文本 ——
    if src == "ocr_mock":
        if not (image_id or "").strip():
            return {
                "status": "ocr_failed",
                "data": None,
                "errors": ["missing image_id"],
                "ocr": None,
                "wrote_db": False,
                "trace": [{"step": "ocr", "detail": "missing image_id"}],
            }
        ocr_meta = mock_ocr(image_id or "")
        trace.append({"step": "ocr", "ok": ocr_meta.get("ok"), "image_id": image_id})
        if not ocr_meta.get("ok"):
            return {
                "status": "ocr_failed",
                "data": None,
                "errors": [str(ocr_meta.get("error") or "ocr_failed")],
                "ocr": ocr_meta,
                "wrote_db": False,
                "trace": trace,
            }
        body = str(ocr_meta.get("text") or "")
        # 空文本：识别「成功」但无字 → 仍算 ocr_failed，不调抽取
        if not body.strip():
            return {
                "status": "ocr_failed",
                "data": None,
                "errors": ["empty_text"],
                "ocr": ocr_meta,
                "wrote_db": False,
                "trace": trace + [{"step": "quality_gate", "detail": "empty_text"}],
            }
    else:
        body = text or ""
        trace.append({"step": "paste", "len": len(body)})

    # —— 2) 质量门 ——
    if len(body.strip()) < MIN_TEXT_LEN:
        return {
            "status": "need_human",
            "data": None,
            "errors": ["text too short"],
            "ocr": ocr_meta,
            "wrote_db": False,
            "trace": trace + [{"step": "quality_gate", "detail": "text too short"}],
        }

    # —— 3) 抽取 + 校验重试 ——
    def call_extract(t: str, repair_hint: str | None = None) -> dict[str, Any]:
        """把 12.01 抽取接到 12.02 重试环。

        repair_hint 非空时：离线路径若 amount 曾非法，可再跑一遍抽取；
        真模型路径会把 hint 交给上层（本课默认 use_chat=False）。
        """
        _ = repair_hint
        out = extract_invoice(t, use_chat=use_chat)
        return dict(out.get("fields") or {})

    result = extract_with_retry(
        body,
        call_extract,
        max_retries=max_retries,
    )
    trace.append(
        {
            "step": "extract_validate",
            "status": result.get("status"),
            "attempts": result.get("attempts"),
        }
    )

    status = str(result.get("status") or "need_human")
    errors: list[str] = []
    if status != "ok" and result.get("last_error"):
        errors.append(str(result["last_error"]))

    return {
        "status": status,
        "data": result.get("data"),
        "errors": errors,
        "ocr": ocr_meta,
        "wrote_db": bool(result.get("wrote_db")),
        "attempts": result.get("attempts"),
        "trace": trace,
        "text_preview": body[:120],
    }


def demo_suite() -> dict[str, Any]:
    """离线验收：OCR 成功 / 空 / 短 / paste / 缺 image_id。"""
    ok_path = run_invoice_pipeline(source="ocr_mock", image_id="img-1")
    empty = run_invoice_pipeline(source="ocr_mock", image_id="img-empty")
    short = run_invoice_pipeline(source="ocr_mock", image_id="img-short")
    missing = run_invoice_pipeline(source="ocr_mock", image_id="")
    from app.ocr.mock_ocr import OCR_OK_TEXT

    paste = run_invoice_pipeline(source="paste", text=OCR_OK_TEXT)

    ok = (
        ok_path.get("status") == "ok"
        and ok_path.get("data", {}).get("invoice_no") == "INV-2026-001"
        and float(ok_path.get("data", {}).get("amount") or 0) == 128.5
        and empty.get("status") == "ocr_failed"
        and short.get("status") == "need_human"
        and missing.get("status") == "ocr_failed"
        and paste.get("status") == "ok"
        and ok_path.get("wrote_db") is True
        and empty.get("wrote_db") is False
    )
    return {
        "ok": ok,
        "ocr_ok": {
            "status": ok_path.get("status"),
            "invoice_no": (ok_path.get("data") or {}).get("invoice_no"),
            "amount": (ok_path.get("data") or {}).get("amount"),
        },
        "empty": empty.get("status"),
        "short": short.get("status"),
        "missing": missing.get("status"),
        "paste": paste.get("status"),
    }
