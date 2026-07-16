# app/chains/extract_validate.py
"""课次 12.02 · 抽取结果校验 + 有限重试。

顺序铁律：先 validate，再业务写入。
失败：短错误回灌 → 最多 max_retries 次 → 仍失败则 need_human。
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from pydantic import ValidationError

from app.chains.parsers import strip_json_payload
from app.models.schemas import InvoiceExtract

# 可调：默认最多再试 2 次（共 3 轮）；改大易烧钱，改 0 则只验一轮
DEFAULT_MAX_RETRIES = 2


def format_validation_errors(err: ValidationError | list | str) -> str:
    """把校验错误压成短文本，方便回灌模型（不要整段堆栈）。"""
    if isinstance(err, str):
        return err
    if isinstance(err, ValidationError):
        rows = err.errors()
    else:
        rows = list(err or [])
    parts: list[str] = []
    for row in rows:
        if not isinstance(row, dict):
            parts.append(str(row))
            continue
        loc = ".".join(str(x) for x in (row.get("loc") or ()))
        msg = str(row.get("msg") or "invalid")
        parts.append(f"{loc}: {msg}" if loc else msg)
    return "; ".join(parts) if parts else "validation failed"


def validate_invoice(data: dict[str, Any]) -> tuple[bool, dict[str, Any] | str]:
    """校验抽取 dict。

    返回:
        (True, 可 JSON 化的 dict) 或 (False, 短错误字符串)
    """
    try:
        obj = InvoiceExtract.model_validate(data)
    except ValidationError as e:
        return False, format_validation_errors(e)
    # mode=json：date → "yyyy-MM-dd" 字符串，方便写笔记/API
    return True, obj.model_dump(mode="json")


def parse_invoice_payload(raw: str | dict[str, Any]) -> dict[str, Any]:
    """原文或 dict → dict；带围栏的 JSON 会先剥离。"""
    if isinstance(raw, dict):
        return raw
    payload = strip_json_payload(str(raw or ""))
    data = json.loads(payload)
    if not isinstance(data, dict):
        raise json.JSONDecodeError("root must be object", payload, 0)
    return data


def save_invoice_to_business_db(data: dict[str, Any]) -> dict[str, Any]:
    """业务写入桩：仅校验通过后才允许调用。

    本课不接真库；用内存回显证明「先校验再写入」顺序。
    """
    ok, detail = validate_invoice(data)
    if not ok:
        # 铁律：非法值不得入库
        raise RuntimeError(f"拒绝写入业务库：{detail}")
    return {"saved": True, "record": detail}


def extract_with_retry(
    text: str,
    call_extract: Callable[..., dict[str, Any] | str],
    *,
    max_retries: int = DEFAULT_MAX_RETRIES,
) -> dict[str, Any]:
    """抽取 → 校验 →（失败则带 hint 重试）→ ok 或 need_human。

    参数:
        text: 原始票据文本（传给 call_extract）
        call_extract: (text, repair_hint=None|str) → dict 或 JSON 字符串
        max_retries: 失败后再试几次（不含首轮）

    返回:
        status: ok | need_human | bad_json
        data / last_error / attempts / wrote_db（ok 时才 True）
    """
    hint: str | None = None
    last_error = ""
    last_data: dict[str, Any] | None = None
    attempts = 0
    # 总轮数 = 1 + max_retries
    for _ in range(max(0, int(max_retries)) + 1):
        attempts += 1
        try:
            raw = call_extract(text, repair_hint=hint)
            data = parse_invoice_payload(raw)
        except (json.JSONDecodeError, TypeError, ValueError) as e:
            last_error = f"bad_json: {e}"
            hint = f"上次不是合法 JSON：{e}。请只输出完整 JSON 对象。"
            continue
        last_data = data
        ok, detail = validate_invoice(data)
        if ok:
            # 仅此处允许「写入」；前面任何失败都不会走到
            written = save_invoice_to_business_db(detail)  # type: ignore[arg-type]
            return {
                "status": "ok",
                "data": detail,
                "attempts": attempts,
                "wrote_db": True,
                "saved": written,
                "last_error": "",
            }
        last_error = str(detail)
        hint = f"校验失败请只修这些字段：{detail}"
    return {
        "status": "need_human",
        "data": last_data,
        "attempts": attempts,
        "wrote_db": False,
        "last_error": last_error,
    }


# —— 离线演示用的假抽取器（不调网）——

BAD_AMOUNT_PAYLOAD = {
    "invoice_no": "24442000001234567890",
    "date": "2026-03-15",
    "amount": "12.00元",  # 非法：带单位
    "seller_name": "示例科技有限公司",
}

GOOD_PAYLOAD = {
    "invoice_no": "24442000001234567890",
    "date": "2026-03-15",
    "amount": 12.0,
    "seller_name": "示例科技有限公司",
}


def make_flaky_extractor(
    *,
    fail_times: int = 1,
    always_bad: bool = False,
) -> Callable[..., dict[str, Any]]:
    """前 fail_times 次返回非法 amount；之后返回合格 JSON。

    always_bad=True 时永远非法 → 走 need_human。
    """
    state = {"n": 0}

    def _call(text: str, repair_hint: str | None = None) -> dict[str, Any]:
        _ = text  # 演示不读文本；真链路会把 hint 拼进 Prompt
        state["n"] += 1
        if always_bad or state["n"] <= fail_times:
            # 有 hint 时仍返回坏数据（模拟修不好）或按 fail_times 控制
            return dict(BAD_AMOUNT_PAYLOAD)
        return dict(GOOD_PAYLOAD)

    return _call
