# app/lessons/m12_01_regex_llm_extract.py
"""课次 12.01 · 正则与 LLM 抽取：离线可验收的演示套件。"""

from __future__ import annotations

import json
from typing import Any

from app.chains.extract import (
    SAMPLE_INVOICE,
    SCHEMA_KEYS,
    extract_invoice,
    regex_invoice_no,
    why_field_strategy,
)
from app.chains.parsers import strip_json_payload


def demo_suite() -> dict[str, Any]:
    """跑完整验收：正则、合并覆盖、至少 3 字段、围栏剥离、策略说明。"""
    no = regex_invoice_no(SAMPLE_INVOICE)
    out = extract_invoice(SAMPLE_INVOICE, use_chat=False)
    fields = out["fields"]
    llm_raw = out["llm_raw"]

    fenced = (
        '好的如下：\n```json\n'
        '{"invoice_no":"x","date":null,"amount":1,"seller_name":null}\n'
        "```\n"
    )
    cleaned = strip_json_payload(fenced)
    parsed = json.loads(cleaned)
    strategy = why_field_strategy()

    filled = [k for k in SCHEMA_KEYS if fields.get(k) not in (None, "")]
    ok = (
        bool(no)
        and no == "24442000001234567890"
        and fields.get("invoice_no") == no
        and llm_raw.get("invoice_no") != no  # 模拟侧曾幻觉，合并后被覆盖
        and fields.get("date") == "2026-03-15"
        and float(fields.get("amount") or 0) == 1280.0
        and "示例科技" in str(fields.get("seller_name") or "")
        and len(filled) >= 3
        and parsed.get("amount") == 1
        and set(strategy.keys()) >= set(SCHEMA_KEYS)
    )
    return {
        "ok": ok,
        "regex_no": no,
        "fields": fields,
        "llm_hallucinated_no": llm_raw.get("invoice_no"),
        "merged_no": fields.get("invoice_no"),
        "filled_keys": filled,
        "fence_cleaned_ok": parsed.get("amount") == 1,
        "strategy": strategy,
        "source": out.get("source"),
    }
