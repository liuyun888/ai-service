# app/lessons/m12_02_validate_retry.py
"""课次 12.02 · 校验与失败重试：离线验收套件。"""

from __future__ import annotations

from typing import Any

from app.chains.extract_validate import (
    BAD_AMOUNT_PAYLOAD,
    GOOD_PAYLOAD,
    extract_with_retry,
    make_flaky_extractor,
    save_invoice_to_business_db,
    validate_invoice,
)


def demo_suite() -> dict[str, Any]:
    """非法拒收 → 重试通过 → need_human → 写入顺序。"""
    # 1) 非法 amount 被拒
    ok_bad, err = validate_invoice(dict(BAD_AMOUNT_PAYLOAD))
    # 2) 合法通过
    ok_good, good = validate_invoice(dict(GOOD_PAYLOAD))
    # 3) 先失败再成功（1 次坏 + 1 次好，max_retries=2）
    repaired = extract_with_retry(
        "样例文本",
        make_flaky_extractor(fail_times=1),
        max_retries=2,
    )
    # 4) 一直坏 → need_human，且未写入
    human = extract_with_retry(
        "样例文本",
        make_flaky_extractor(always_bad=True),
        max_retries=2,
    )
    # 5) 未校验直接写会被桩拒绝
    write_blocked = False
    try:
        save_invoice_to_business_db(dict(BAD_AMOUNT_PAYLOAD))
    except RuntimeError:
        write_blocked = True

    ok = (
        ok_bad is False
        and isinstance(err, str)
        and "amount" in err
        and ok_good is True
        and isinstance(good, dict)
        and float(good.get("amount") or -1) == 12.0
        and repaired.get("status") == "ok"
        and repaired.get("wrote_db") is True
        and repaired.get("attempts") == 2
        and human.get("status") == "need_human"
        and human.get("wrote_db") is False
        and human.get("attempts") == 3  # 1 + max_retries=2
        and write_blocked
    )
    return {
        "ok": ok,
        "reject_error": err,
        "good": good,
        "repaired": {
            "status": repaired.get("status"),
            "attempts": repaired.get("attempts"),
            "wrote_db": repaired.get("wrote_db"),
            "amount": (repaired.get("data") or {}).get("amount"),
        },
        "need_human": {
            "status": human.get("status"),
            "attempts": human.get("attempts"),
            "wrote_db": human.get("wrote_db"),
            "last_error": human.get("last_error"),
        },
        "write_blocked_on_bad": write_blocked,
    }
