# app/chains/extract.py
"""课次 12.01 · 正则 +（LLM / 离线模拟）抽取：文本 → Schema 字段。

直觉：
- 发票号码格式固定 → 正则更稳、可审计
- 日期/销方/金额写法常飘 → Prompt + Schema（或本课离线模拟）
- 合并时：强格式字段以正则为准，禁止 LLM 覆盖号码

默认 USE_CHAT=0：不调网也能验收「正则钉死 + 其余字段进 JSON」。
设 USE_CHAT=1 且配置好模型时，才走真 LLM 抽其余字段。
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

from app.chains.parsers import strip_json_payload

# 可调：1=真模型抽字段；0=离线脚本化（专栏默认验收）
USE_CHAT = os.getenv("USE_CHAT", "0").strip().lower() in {"1", "true", "yes", "on"}

# 样例发票文本（验收用；含「发票号码 / 开票日期 / 价税合计 / 销售方」）
SAMPLE_INVOICE = """
电子发票（普通发票）

发票号码：24442000001234567890
开票日期：2026年3月15日
销售方名称：示例科技有限公司
购买方名称：学员演示账号

项目 金额
咨询服务费 1280.00

价税合计（小写）：￥1280.00
价税合计（大写）：壹仟贰佰捌拾圆整
""".strip()

# 强格式：发票号码（以规则为准）
INVOICE_NO_RE = re.compile(r"发票号码[:：\s]*([0-9A-Za-z-]{8,})")

# Schema 键顺序（文档与 Prompt 对齐）
SCHEMA_KEYS = ("invoice_no", "date", "amount", "seller_name")

SCHEMA_HINT = (
    "只输出一个 JSON 对象，不要 Markdown 围栏，不要解释。\n"
    "键必须为：invoice_no, date, amount, seller_name。\n"
    "date 用 yyyy-MM-dd；amount 为数字（不要货币符号）；\n"
    "看不到的字段填 null；禁止编造文本中没有的值。"
)

# Prompt 文件（可选；真模型时优先读盘，缺文件则用内置 SCHEMA_HINT）
_PROMPT_FILE = Path(__file__).resolve().parents[1] / "prompts" / "extract_json.md"


def regex_invoice_no(text: str) -> str | None:
    """用正则抽发票号码；抽不到返回 None。"""
    m = INVOICE_NO_RE.search(text or "")
    return m.group(1) if m else None


def build_extract_prompt(text: str) -> str:
    """拼抽取 Prompt：Schema 约束 + 用户文本。"""
    body = (text or "").strip()
    if _PROMPT_FILE.is_file():
        tpl = _PROMPT_FILE.read_text(encoding="utf-8")
        # 简易占位：与 prompts/extract_json.md 约定一致
        return (
            tpl.replace("{{schema_hint}}", SCHEMA_HINT)
            .replace("{{user_text}}", body)
        )
    return f"{SCHEMA_HINT}\n\n文本：\n{body}"


def merge_results(
    regex_no: str | None,
    llm_obj: dict[str, Any],
) -> dict[str, Any]:
    """合并：号码以正则为准；其余键保留 LLM/模拟结果。"""
    out: dict[str, Any] = {k: llm_obj.get(k) for k in SCHEMA_KEYS}
    # 补全 LLM 多吐的键，方便调试，但不覆盖 Schema 主字段逻辑
    for k, v in (llm_obj or {}).items():
        if k not in out:
            out[k] = v
    if regex_no:
        out["invoice_no"] = regex_no
    return out


def _parse_json_obj(raw: str) -> dict[str, Any]:
    """剥围栏后解析为 dict；失败抛 JSONDecodeError。"""
    payload = strip_json_payload(raw or "")
    data = json.loads(payload)
    if not isinstance(data, dict):
        raise json.JSONDecodeError("root must be object", payload, 0)
    return data


def _cn_date_to_iso(text: str) -> str | None:
    """把「2026年3月15日」这类写法收成 yyyy-MM-dd（离线模拟用）。"""
    m = re.search(r"(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日", text or "")
    if not m:
        # 已是 ISO
        m2 = re.search(r"(20\d{2})-(\d{2})-(\d{2})", text or "")
        if m2:
            return f"{m2.group(1)}-{m2.group(2)}-{m2.group(3)}"
        return None
    y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
    return f"{y:04d}-{mo:02d}-{d:02d}"


def _scripted_llm_extract(text: str) -> dict[str, Any]:
    """离线「假装 LLM」：用宽松规则抽日期/金额/销方。

    故意给一个错误的 invoice_no，好让 merge 演示「正则覆盖 LLM」。
    真业务里 LLM 也可能幻觉号码——这正是规则要钉死的点。
    """
    t = text or ""
    date = _cn_date_to_iso(t)
    amount: float | None = None
    # 价税合计优先；其次裸金额
    m_amt = re.search(
        r"价税合计[^0-9￥¥]*[￥¥]?\s*([0-9]+(?:\.[0-9]+)?)",
        t,
    )
    if not m_amt:
        m_amt = re.search(r"[￥¥]\s*([0-9]+(?:\.[0-9]+)?)", t)
    if m_amt:
        amount = float(m_amt.group(1))
    seller: str | None = None
    m_seller = re.search(r"销售方(?:名称)?[:：\s]*([^\n\r]+)", t)
    if m_seller:
        seller = m_seller.group(1).strip()
    return {
        "invoice_no": "LLM-HALLUCINATED-000",  # 将被正则覆盖
        "date": date,
        "amount": amount,
        "seller_name": seller,
    }


def llm_extract_fields(text: str, *, use_chat: bool | None = None) -> dict[str, Any]:
    """抽 Schema 字段：真模型或离线模拟。

    参数:
        text: 票据文本
        use_chat: 覆盖环境变量 USE_CHAT
    """
    chat = USE_CHAT if use_chat is None else bool(use_chat)
    if not chat:
        return _scripted_llm_extract(text)

    from langchain_core.messages import HumanMessage, SystemMessage

    from app.models.factory import get_chat_model

    model = get_chat_model(temperature=0)
    prompt = build_extract_prompt(text)
    # system 再钉一次「纯 JSON」
    msgs = [
        SystemMessage(content="你是信息抽取助手。只输出合法 JSON 对象。"),
        HumanMessage(content=prompt),
    ]
    resp = model.invoke(msgs)
    raw = getattr(resp, "content", None) or str(resp)
    return _parse_json_obj(str(raw))


def extract_invoice(
    text: str,
    *,
    use_chat: bool | None = None,
) -> dict[str, Any]:
    """完整一轮：正则号码 + LLM/模拟其余字段 + 合并。

    返回:
        fields: 合并后的 Schema 字典
        regex_invoice_no / llm_raw / source / prompt_preview
    """
    body = (text or "").strip()
    regex_no = regex_invoice_no(body)
    llm_obj = llm_extract_fields(body, use_chat=use_chat)
    merged = merge_results(regex_no, llm_obj)
    chat = USE_CHAT if use_chat is None else bool(use_chat)
    return {
        "fields": merged,
        "regex_invoice_no": regex_no,
        "llm_raw": llm_obj,
        "source": "llm" if chat else "scripted",
        "prompt_preview": build_extract_prompt(body)[:240],
        "schema_keys": list(SCHEMA_KEYS),
    }


def why_field_strategy() -> dict[str, str]:
    """验收口述：每个字段为何用正则或 LLM。"""
    return {
        "invoice_no": "固定长数字串，正则稳定可审计；禁止 LLM 覆盖",
        "date": "写法多变（年月日/斜杠），适合 LLM 或宽松解析后再校验",
        "amount": "常带货币符号与中文大写，适合 LLM 归一成 number",
        "seller_name": "专名、换行、别名多，适合 LLM；仍禁止编造",
    }
