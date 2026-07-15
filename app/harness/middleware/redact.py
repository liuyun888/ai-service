# app/harness/middleware/redact.py
"""课次 08.06 · PII 脱敏（after_tool / before 落盘 Trace）。"""

from __future__ import annotations

import re
from typing import Any

# 演示规则：身份证粗匹配、手机号
ID_CARD = re.compile(r"\b\d{17}[\dXx]\b")
PHONE = re.compile(r"\b1[3-9]\d{9}\b")


def redact_pii(text: str) -> str:
    """把明显 PII 换成占位符，避免 Trace 裸奔。"""
    out = text or ""
    out = ID_CARD.sub("[REDACTED_ID]", out)
    out = PHONE.sub("[REDACTED_PHONE]", out)
    return out


def redact_event(text: str) -> dict[str, Any]:
    redacted = redact_pii(text)
    return {
        "hook": "after_tool",
        "middleware": "PIIRedact",
        "changed": redacted != (text or ""),
        "text": redacted,
    }
