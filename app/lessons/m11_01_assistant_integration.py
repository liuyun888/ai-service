# app/lessons/m11_01_assistant_integration.py
"""课次 11.01 · 业务助手集成：Harness + RAG + 只读 Tool 一条链路。

默认决策序（离线也可验收）：
1) 需要外部事实？→ RAG（search_docs）和/或 Tool（get_inventory）
2) 观察回灌后再生成
3) 回答钉上证据：文档 path / Tool 数字；禁止编造库存

数值以 Tool 为准；退货规则以文档为准。
"""

from __future__ import annotations

import os
import re
import time
from typing import Any

from app.harness.middleware.safety import check_tool_allowed, guard_output
from app.harness.shell import ensure_tenant
from app.mcp.tools_search import search_docs
from app.tools.inventory import get_inventory
from app.tools.knowledge import search_knowledge

# 可调：USE_CHAT=1 时预留真模型钩子；本课默认 0，走确定性编排
USE_CHAT = os.getenv("USE_CHAT", "0").strip() == "1"

# 验收话术（与正文一致）
DEMO_MESSAGE = "防水款还有吗？退货多久？"


def _guess_sku(text: str) -> str:
    """从话术猜 SKU；防水/黑 Pro → EARPHONE-PRO-BK。"""
    u = (text or "").upper()
    for key in ("EARPHONE-PRO-WH", "EARPHONE-PRO-BK", "CABLE-USB-C"):
        if key in u:
            return key
    t = text or ""
    if "白" in t:
        return "EARPHONE-PRO-WH"
    if "防水" in t or "黑" in t or "pro" in t.lower() or "货" in t:
        return "EARPHONE-PRO-BK"
    return "EARPHONE-PRO-BK"


def _wants_inventory(text: str) -> bool:
    t = text or ""
    keys = ("货", "库存", "还有", "现货", "有没有", "多少件", "stock", "防水")
    return any(k in t.lower() if k.isascii() else k in t for k in keys)


def _wants_policy(text: str) -> bool:
    t = text or ""
    keys = ("退货", "退换", "运费", "质保", "几天", "多久", "无理由", "政策")
    return any(k in t for k in keys)


def _call_tool_safe(name: str, invoke) -> dict[str, Any]:
    """Harness：白名单 → 调用 → 记 Observation。"""
    ok, reason = check_tool_allowed(name)
    if not ok:
        return {
            "tool": name,
            "allowed": False,
            "observation": reason,
            "error": reason,
        }
    try:
        obs = str(invoke())
    except Exception as exc:  # noqa: BLE001
        obs = f"error={type(exc).__name__}: {exc}"
    return {"tool": name, "allowed": True, "observation": obs}


def _parse_stock(obs: str) -> int | None:
    m = re.search(r"stock=(\d+)", obs or "")
    return int(m.group(1)) if m else None


def run_assistant_turn(
    message: str,
    *,
    tenant_id: str = "demo",
    session_id: str = "s1",
    use_chat: bool | None = None,
) -> dict[str, Any]:
    """跑一轮业务助手：鉴权租户 → RAG → 库存 Tool → 护栏后作答。

    参数:
        message: 用户话术
        tenant_id: 租户（须在 ALLOWED_TENANTS）
        session_id: 会话 id（本课仅回显，多轮留给 11.02）
        use_chat: 覆盖 USE_CHAT；True 时仍先走同一编排再可选润色（本课不强制真模型）

    返回:
        reply / evidence / trace / ok 等，供 API 与 demo 验收
    """
    _ = use_chat if use_chat is not None else USE_CHAT  # 预留：真模型润色
    t0 = time.perf_counter()
    text = (message or "").strip()
    trace: list[dict[str, Any]] = []
    evidence: dict[str, Any] = {
        "doc_paths": [],
        "doc_snippets": [],
        "tool_observations": [],
        "stock": None,
        "sku": None,
    }

    tenant_ok, tenant_msg = ensure_tenant(tenant_id)
    if not tenant_ok:
        return {
            "ok": False,
            "reply": tenant_msg,
            "session_id": session_id,
            "tenant_id": tenant_id,
            "evidence": evidence,
            "trace": [{"step": "auth", "detail": tenant_msg}],
            "elapsed_ms": int((time.perf_counter() - t0) * 1000),
        }

    need_inv = _wants_inventory(text)
    need_policy = _wants_policy(text)
    # 组合问默认两步都做
    if not need_inv and not need_policy:
        need_inv = True
        need_policy = True

    # ---- 1) RAG：先 VFS search_docs，再补 search_knowledge ----
    if need_policy:
        q_docs = "七天无理由" if ("退" in text or "无理由" in text or "多久" in text) else text
        row = _call_tool_safe("search_docs", lambda: search_docs(q_docs))
        trace.append({"step": "rag", **row})
        obs = row.get("observation") or ""
        if row.get("allowed") and not str(obs).startswith("error="):
            for line in str(obs).splitlines():
                if " :: " in line:
                    path, snip = line.split(" :: ", 1)
                    evidence["doc_paths"].append(path.strip())
                    evidence["doc_snippets"].append(snip.strip())
                    evidence["tool_observations"].append(line.strip())

        # 结构化条款（保证「退货多久」必有可读证据）
        row_k = _call_tool_safe(
            "search_knowledge",
            lambda: search_knowledge.invoke({"query": text or "退货几天"}),
        )
        trace.append({"step": "rag_fallback", **row_k})
        if row_k.get("allowed") and row_k.get("observation") not in (
            None,
            "not_found",
        ):
            evidence["tool_observations"].append(str(row_k["observation"]))
            if "[return_window]" in str(row_k["observation"]):
                evidence.setdefault("policy_ids", []).append("return_window")

    # ---- 2) 只读业务 Tool：库存 ----
    if need_inv:
        sku = _guess_sku(text)
        evidence["sku"] = sku
        row = _call_tool_safe(
            "get_inventory",
            lambda: get_inventory.invoke({"sku": sku}),
        )
        trace.append({"step": "tool", **row})
        obs = str(row.get("observation") or "")
        evidence["tool_observations"].append(obs)
        evidence["stock"] = _parse_stock(obs)

    # ---- 3) 生成：钉证据，禁止与 Observation 矛盾 ----
    parts: list[str] = []
    if evidence.get("sku") is not None and evidence.get("stock") is not None:
        stock = evidence["stock"]
        sku = evidence["sku"]
        if stock == 0:
            parts.append(
                f"库存（Tool）：SKU `{sku}` 当前 stock={stock}，暂无现货。"
                f"（证据：get_inventory → sku={sku}, stock={stock}）"
            )
        else:
            parts.append(
                f"库存（Tool）：防水款对应 `{sku}`，现货 stock={stock}。"
                f"（证据：get_inventory → sku={sku}, stock={stock}）"
            )
    elif need_inv:
        parts.append("库存（Tool）：未查到有效 stock，不能口头编造件数。")

    if evidence.get("doc_paths") or any(
        "return_window" in str(x) for x in evidence.get("tool_observations", [])
    ):
        path_hint = (
            next(
                (p for p in evidence["doc_paths"] if "return" in p.lower()),
                evidence["doc_paths"][0],
            )
            if evidence.get("doc_paths")
            else "policy:[return_window]"
        )
        # 从 knowledge observation 抽一句
        policy_line = next(
            (
                x
                for x in evidence.get("tool_observations", [])
                if "return_window" in str(x) or "7 天" in str(x) or "7天" in str(x)
            ),
            "自签收之日起 7 天内可申请无理由退货（以文档为准）。",
        )
        parts.append(
            f"退货规则（RAG）：{policy_line} "
            f"（证据路径/条目：`{path_hint}`；数值类以 Tool 为准，条款以文档为准。）"
        )
    elif need_policy:
        parts.append("退货规则（RAG）：未命中文档，请改问或转人工，禁止编造天数。")

    if not parts:
        parts.append("请说明要查的 SKU 或退货/政策问题。")

    reply = "\n".join(parts)
    guarded = guard_output(reply)
    if not guarded.ok:
        reply = guarded.text
        trace.append(
            {
                "step": "guard",
                "hit_pattern": guarded.hit_pattern,
                "detail": "输出护栏改写",
            }
        )

    # 验收：有库存数字 + 有文档/政策证据
    has_tool_num = evidence.get("stock") is not None
    has_doc = bool(evidence.get("doc_paths")) or any(
        "return_window" in str(x) for x in evidence.get("tool_observations", [])
    )
    ok = has_tool_num and has_doc and "stock=" in reply

    return {
        "ok": ok,
        "reply": reply,
        "session_id": session_id,
        "tenant_id": tenant_id,
        "evidence": evidence,
        "trace": trace,
        "decision_order": ["rag", "tool", "generate"],
        "elapsed_ms": int((time.perf_counter() - t0) * 1000),
    }


def demo_suite() -> dict[str, Any]:
    """11.01 验收套件。"""
    # 1) 组合问：库存 + 退货
    combo = run_assistant_turn(DEMO_MESSAGE, tenant_id="demo", session_id="s-demo")
    # 2) 坏租户
    bad = run_assistant_turn("还有货吗", tenant_id="evil", session_id="s-x")
    # 3) 写入类 Tool 名不在白名单（直接测 check）
    blocked_ok, blocked_reason = check_tool_allowed("create_refund")
    return {
        "combo": combo,
        "bad_tenant": bad,
        "write_tool_blocked": {
            "allowed": blocked_ok,
            "reason": blocked_reason,
        },
        "ok": (
            combo.get("ok") is True
            and combo["evidence"].get("stock") == 12
            and (
                bool(combo["evidence"].get("doc_paths"))
                or any(
                    "return_window" in str(x)
                    for x in combo["evidence"].get("tool_observations", [])
                )
            )
            and bad.get("ok") is False
            and blocked_ok is False
        ),
    }
