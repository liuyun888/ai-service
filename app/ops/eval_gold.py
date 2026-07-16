# app/ops/eval_gold.py
"""课次 13.02 · 最小金标抽检（离线、可扩）。

先定 20 条也不晚；本课用几条硬断言证明「改 Harness 前后可对比」。
"""

from __future__ import annotations

from typing import Any

from app.chains.extract_validate import validate_invoice
from app.harness.middleware.guards import commitment_guard
from app.harness.middleware.redact import redact_pii


def run_gold_checks() -> dict[str, Any]:
    """跑一小撮金标：护栏、脱敏、抽取校验。"""
    cases: list[dict[str, Any]] = []

    # 1) 护栏：绝对承诺必须拦
    ok, out = commitment_guard("保证明天一定退款到账")
    cases.append(
        {
            "id": "guard_commitment",
            "pass": ok is False and "绝对承诺" in out,
            "expect": "blocked",
        }
    )

    # 2) 护栏：正常物流话术放行
    ok2, _ = commitment_guard("当前物流显示已发货")
    cases.append({"id": "guard_safe", "pass": ok2 is True, "expect": "pass"})

    # 3) PII 脱敏
    red = redact_pii("联系手机 13800138000")
    cases.append(
        {
            "id": "pii_phone",
            "pass": "13800138000" not in red and "REDACTED" in red,
            "expect": "redacted",
        }
    )

    # 4) 抽取：合法金额通过
    v_ok, detail = validate_invoice(
        {
            "invoice_no": "INV-2026-001",
            "date": "2026-07-01",
            "amount": 128.5,
            "seller_name": "Acme",
        }
    )
    cases.append(
        {
            "id": "extract_ok",
            "pass": v_ok is True and isinstance(detail, dict),
            "expect": "ok",
        }
    )

    # 5) 抽取：非法金额拒绝
    v_bad, err = validate_invoice(
        {
            "invoice_no": "INV-2026-001",
            "date": "2026-07-01",
            "amount": "12.00元",
            "seller_name": "Acme",
        }
    )
    cases.append(
        {
            "id": "extract_bad_amount",
            "pass": v_bad is False and "amount" in str(err),
            "expect": "reject",
        }
    )

    passed = sum(1 for c in cases if c["pass"])
    return {
        "total": len(cases),
        "passed": passed,
        "pass_rate": round(passed / max(1, len(cases)), 4),
        "cases": cases,
        "ok": passed == len(cases),
    }
