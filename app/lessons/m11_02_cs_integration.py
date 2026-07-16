# app/lessons/m11_02_cs_integration.py
"""课次 11.02 · 对话客服：Loop + 会话记忆 + 转人工（配置驱动）。

与 11.01 助手差异：投诉/情绪升级权重更高；必须能 handoff + summary。
默认离线脚本化验收，不依赖真模型。
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from app.harness.middleware.safety import (
    SafetyContext,
    build_handoff_summary,
    check_tool_allowed,
    guard_output,
)
from app.harness.shell import ensure_tenant
from app.lessons.m06_04_single_agent import SESSION_STORE, SessionStore
from app.mcp.tools_search import search_docs
from app.tools.inventory import get_order_status
from app.tools.knowledge import search_knowledge

# 配置文件路径（相对 ai-service 根：app/agents/cs_config.yaml）
DEFAULT_CS_CONFIG = Path(__file__).resolve().parents[1] / "agents" / "cs_config.yaml"

DEMO_SHIP = "我的订单 SF123456 到哪了"
DEMO_HANDOFF = "你们太坑了要投诉转人工"


def load_cs_config(path: Path | None = None) -> dict[str, Any]:
    """读取 yaml；缺文件时给内置默认，保证演示可跑。"""
    p = path or DEFAULT_CS_CONFIG
    if p.is_file():
        data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        if isinstance(data, dict):
            return data
    return {
        "name": "customer_service",
        "max_steps": 6,
        "tools": ["get_order_status", "search_docs", "search_knowledge"],
        "handoff_rules": {
            "keywords": ["投诉", "律师", "举报", "转人工"],
            "on_tool_fail_times": 2,
        },
        "system_prompt": "你是客服助手。",
    }


def check_handoff_rules(
    user_text: str,
    *,
    tool_fails: int = 0,
    keywords: list[str] | None = None,
    on_tool_fail_times: int = 2,
) -> tuple[bool, str]:
    """纯规则：是否转人工。返回 (should_handoff, reason码)。

    reason 对齐正文协议：user_requested | complaint | tool_fail
    """
    text = user_text or ""
    kws = keywords or ["投诉", "转人工"]
    for kw in kws:
        if kw and kw in text:
            if kw in ("投诉", "举报", "曝光", "律师"):
                return True, "complaint"
            return True, "user_requested"
    if tool_fails >= max(1, int(on_tool_fail_times)):
        return True, "tool_fail"
    return False, ""


def _extract_tracking(text: str, fallback: str = "") -> str:
    """从话术抠运单号；会话里可记住。"""
    m = re.search(r"\b([A-Z]{2}\d{6,})\b", (text or "").upper())
    if m:
        return m.group(1)
    for key in ("SF123456", "YT998877"):
        if key in (text or "").upper():
            return key
    return fallback


def _wants_shipment(text: str) -> bool:
    t = text or ""
    return any(k in t for k in ("到哪", "物流", "运单", "订单", "快递", "发货"))


def _wants_policy(text: str) -> bool:
    t = text or ""
    return any(k in t for k in ("退货", "运费", "质保", "政策", "营业时间", "几点"))


def _tool_allowed_in_config(name: str, tools: list[str]) -> bool:
    return name in tools


def run_cs_turn(
    message: str,
    *,
    tenant_id: str = "demo",
    session_id: str = "s1",
    config: dict[str, Any] | None = None,
    store: SessionStore | None = None,
    tool_fails: int = 0,
) -> dict[str, Any]:
    """跑一轮客服：先闸门 handoff，再 FAQ Tool，再护栏。

    会话记忆：SessionState.sku 槽位复用为「已确认运单号」时写入 messages 旁路——
    本课在 session.messages 之外用简单属性：把 tracking 记在 session.sku 字段
    （教学够用；生产应单独 tracking 槽）。
    """
    cfg = config or load_cs_config()
    store = store or SESSION_STORE
    session = store.get(session_id)
    text = (message or "").strip()
    tools_cfg = list(cfg.get("tools") or [])
    rules = dict(cfg.get("handoff_rules") or {})
    keywords = list(rules.get("keywords") or [])
    fail_times = int(rules.get("on_tool_fail_times") or 2)

    tenant_ok, tenant_msg = ensure_tenant(tenant_id)
    if not tenant_ok:
        return {
            "ok": False,
            "action": "error",
            "reply": tenant_msg,
            "reason": "forbidden_tenant",
            "summary": "",
            "session_id": session_id,
            "tenant_id": tenant_id,
            "trace": [],
        }

    # ---- 闸门：投诉 / 要人工（优先于自动答）----
    need_ho, reason = check_handoff_rules(
        text,
        tool_fails=tool_fails,
        keywords=keywords,
        on_tool_fail_times=fail_times,
    )
    if need_ho:
        ctx = SafetyContext(
            user_text=text,
            session_id=session_id,
            tool_fails=tool_fails,
            trace=[],
        )
        # 带上会话里已查过的运单，避免用户重讲
        if session.sku:
            ctx.trace.append(
                {
                    "tool": "session_memory",
                    "observation": f"remembered_tracking={session.sku}",
                }
            )
        summary = build_handoff_summary(ctx)
        reply = (
            "正在为你转接人工客服，请稍候。"
            f"\n\n【转人工摘要】\n{summary}"
        )
        return {
            "ok": True,
            "action": "handoff",
            "reason": reason,
            "summary": summary,
            "reply": reply,
            "session_id": session_id,
            "tenant_id": tenant_id,
            "trace": list(ctx.trace),
            "session_tracking": session.sku,
        }

    trace: list[dict[str, Any]] = []
    parts: list[str] = []

    # 记忆：抠运单号写入会话槽
    tracking = _extract_tracking(text, session.sku)
    if tracking:
        session.sku = tracking

    # ---- FAQ：物流 ----
    if _wants_shipment(text) or (session.sku and "哪" in text):
        no = tracking or session.sku or "SF123456"
        session.sku = no
        tool_name = "get_order_status"
        if not _tool_allowed_in_config(tool_name, tools_cfg):
            tool_name = "get_shipment"
        allowed, why = check_tool_allowed(tool_name)
        if not allowed:
            obs = why
        else:
            obs = str(get_order_status.invoke({"tracking_no": no}))
        trace.append({"tool": tool_name, "args": {"tracking_no": no}, "observation": obs})
        if obs.startswith("error=") or obs == "not_found":
            parts.append(f"物流查询未成功（{obs}）。请核对运单号，或转人工。")
        else:
            parts.append(f"物流状态（Tool）：{obs}。以上来自查询，非估算。")

    # ---- FAQ：政策 ----
    if _wants_policy(text):
        for tool_name, inv in (
            ("search_docs", lambda: search_docs(text)),
            ("search_knowledge", lambda: search_knowledge.invoke({"query": text})),
        ):
            if not _tool_allowed_in_config(tool_name, tools_cfg):
                continue
            allowed, why = check_tool_allowed(tool_name)
            if not allowed:
                continue
            obs = str(inv())
            if str(obs).startswith("error=") or obs == "not_found":
                continue
            trace.append({"tool": tool_name, "args": {"query": text}, "observation": obs[:200]})
            parts.append(f"政策说明（RAG）：{obs[:180]}")
            break

    if not parts:
        parts.append(
            "我可以帮你查物流（请给运单号）或解释售后政策。"
            "若要投诉/转人工，请直接说明，我会提交摘要。"
        )

    draft = "\n".join(parts)
    guarded = guard_output(draft)
    reply = guarded.text if guarded.ok else guarded.text

    return {
        "ok": True,
        "action": "reply",
        "reason": "",
        "summary": "",
        "reply": reply,
        "session_id": session_id,
        "tenant_id": tenant_id,
        "trace": trace,
        "session_tracking": session.sku,
        "config_name": cfg.get("name"),
    }


def demo_suite() -> dict[str, Any]:
    """11.02 验收套件。"""
    cfg = load_cs_config()
    store = SessionStore()  # 独立仓库，避免污染全局

    # 1) 物流自动答
    ship = run_cs_turn(DEMO_SHIP, session_id="cs-ship", store=store, config=cfg)
    # 2) 同会话记忆：只说「到哪了」应仍能用 SF123456
    follow = run_cs_turn("到哪了", session_id="cs-ship", store=store, config=cfg)
    # 3) 投诉转人工
    ho = run_cs_turn(DEMO_HANDOFF, session_id="cs-ho", store=store, config=cfg)
    # 4) 规则函数：工具连败
    fail_ho, fail_reason = check_handoff_rules(
        "查一下",
        tool_fails=2,
        keywords=list(cfg["handoff_rules"]["keywords"]),
        on_tool_fail_times=int(cfg["handoff_rules"]["on_tool_fail_times"]),
    )
    ok = (
        ship.get("action") == "reply"
        and "转运" in (ship.get("reply") or "")
        and ship.get("session_tracking") == "SF123456"
        and follow.get("action") == "reply"
        and follow.get("session_tracking") == "SF123456"
        and ho.get("action") == "handoff"
        and bool(ho.get("summary"))
        and ho.get("reason") in ("complaint", "user_requested")
        and fail_ho is True
        and fail_reason == "tool_fail"
        and DEFAULT_CS_CONFIG.is_file()
    )
    return {
        "config_path": str(DEFAULT_CS_CONFIG),
        "config_name": cfg.get("name"),
        "ship": ship,
        "follow": follow,
        "handoff": ho,
        "tool_fail_rule": {"handoff": fail_ho, "reason": fail_reason},
        "ok": ok,
    }
