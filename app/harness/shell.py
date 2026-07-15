# app/harness/shell.py
"""课次 08.01 · 最小 Harness 外壳：同一问答，裸奔 vs 拴挽具。

心智：Agent ≈ Model + Harness
- Model/Tool：真正检索与生成（本课用规则模板代替 Chat，聚焦外壳差异）
- Framework：本课未强制上图；只说明位置
- Harness：租户鉴权、Tool 白名单、输出护栏、截断、Trace

答案内容可以相近，可运营性完全不同。
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from app.harness.context.truncate import truncate_text
from app.harness.middleware.safety import (
    TOOL_WHITELIST,
    check_tool_allowed,
    guard_output,
)
from app.tools.knowledge import search_knowledge

# ---------------------------------------------------------------------------
# 演示用「合法租户」；生产应由网关/JWT 注入，不信任模型乱填
# ---------------------------------------------------------------------------
ALLOWED_TENANTS = frozenset({"demo", "tenant-a", "tenant-b"})


@dataclass
class TraceEvent:
    """一条可观测事件（简化版 Trace）。"""

    name: str
    detail: str
    ts: float = field(default_factory=time.time)


def layer_map() -> list[dict[str, str]]:
    """三层职责对照表（笔记/口述用）。"""
    return [
        {
            "layer": "Model",
            "duty": "推理、选 Tool、生成文本",
            "example": "Chat 模型；本课用模板代替",
            "not": "不负责限流/租户鉴权",
        },
        {
            "layer": "Framework",
            "duty": "图、Chain、消息协议、Tool 绑定",
            "example": "LangGraph / LangChain",
            "not": "不等于已经有运营外壳",
        },
        {
            "layer": "Harness",
            "duty": "中间件、上下文策略、安全门、观测",
            "example": "app/harness/（鉴权、护栏、Trace、截断）",
            "not": "不塞具体业务 if-else 全文",
        },
    ]


def gap_audit_template() -> list[dict[str, str]]:
    """「现有 Agent 缺口」表：能力现在在哪、是否应上移 Harness。"""
    return [
        {
            "capability": "max_steps",
            "now_layer": "Framework/Loop（M06 run_tao_loop / agent max_steps）",
            "move_to_harness": "可：统一默认值与超限兜底话术",
        },
        {
            "capability": "Tool 白名单",
            "now_layer": "Harness middleware/safety.py（06.06 已落）",
            "move_to_harness": "已在 Harness",
        },
        {
            "capability": "日志/Trace",
            "now_layer": "脚本 print / 部分笔记",
            "move_to_harness": "是：统一 Trace 事件结构",
        },
        {
            "capability": "上下文截断",
            "now_layer": "分散或缺失",
            "move_to_harness": "是：context/truncate（本课示意）",
        },
        {
            "capability": "输出承诺护栏",
            "now_layer": "Harness guard_output",
            "move_to_harness": "已在 Harness",
        },
        {
            "capability": "租户鉴权",
            "now_layer": "本课 shell.ensure_tenant",
            "move_to_harness": "是：调用前钩子",
        },
    ]


def ensure_tenant(tenant_id: str) -> tuple[bool, str]:
    """调用前钩子：租户是否允许访问。"""
    tid = (tenant_id or "").strip()
    if not tid:
        return False, "error=missing_tenant; hint=请传 tenant_id"
    if tid not in ALLOWED_TENANTS:
        return False, f"error=forbidden_tenant; hint={tid!r} 不在允许列表"
    return True, "ok"


def answer_from_docs(query: str, docs_text: str) -> str:
    """「模型位」占位：不调 Chat，用模板拼答案（聚焦外壳差异）。"""
    if not docs_text or docs_text == "not_found":
        return f"未检索到与「{query}」相关的政策，请换个问法或转人工。"
    return f"根据政策：{docs_text}（以上来自检索 Observation，非估算。）"


def run_bare_model_tool(query: str) -> dict[str, Any]:
    """仅 Model+Tool（Demo 裸奔）：直调检索 → 拼答案，无鉴权/无 Trace/无护栏。"""
    obs = str(search_knowledge.invoke({"query": query}))
    # 故意演示：若有人把危险承诺拼进草稿，裸奔会直接发出
    draft = answer_from_docs(query, obs)
    return {
        "mode": "bare",
        "query": query,
        "observation": obs,
        "reply": draft,
        "trace": [],
        "guard_ok": None,
        "tenant_ok": None,
        "lesson": "能答一次；缺鉴权/观测/护栏",
    }


def run_with_harness(
    query: str,
    *,
    tenant_id: str = "demo",
    inject_promise: bool = False,
    fat_context: str = "",
) -> dict[str, Any]:
    """加 Harness：鉴权 → 白名单 → 截断 → Tool → 护栏 → Trace。

    参数:
        inject_promise: True 时在草稿末尾拼「保证明天」——护栏应拦住
        fat_context: 附加超长上下文，触发截断示意
    """
    trace: list[TraceEvent] = []

    # 1) 调用前：租户
    ok, reason = ensure_tenant(tenant_id)
    trace.append(TraceEvent("auth.tenant", reason))
    if not ok:
        return {
            "mode": "harness",
            "query": query,
            "reply": "无权访问：租户校验失败。",
            "trace": [{"name": e.name, "detail": e.detail} for e in trace],
            "guard_ok": True,
            "tenant_ok": False,
            "truncated": False,
            "lesson": "Harness 在 Model 前挡住非法租户",
        }

    # 2) 上下文截断（示意）
    ctx_raw = fat_context or query
    cut = truncate_text(ctx_raw)
    trace.append(
        TraceEvent(
            "context.truncate",
            f"truncated={cut['truncated']}; len={cut['original_len']}",
        )
    )

    # 3) Tool 白名单
    allowed, allow_reason = check_tool_allowed("search_knowledge")
    trace.append(TraceEvent("tool.whitelist", allow_reason))
    if not allowed:
        return {
            "mode": "harness",
            "query": query,
            "reply": "工具未授权。",
            "trace": [{"name": e.name, "detail": e.detail} for e in trace],
            "tenant_ok": True,
            "guard_ok": True,
            "truncated": bool(cut["truncated"]),
            "lesson": "白名单拒绝未知/高风险 Tool",
        }

    # 4) 真正干活（Model/Tool 层）
    obs = str(search_knowledge.invoke({"query": str(cut["text"])}))
    trace.append(TraceEvent("tool.search_knowledge", obs[:160]))
    draft = answer_from_docs(query, obs)
    if inject_promise:
        draft = draft + " 我们保证明天一定办妥。"

    # 5) 调用后：输出护栏
    guarded = guard_output(draft)
    trace.append(
        TraceEvent(
            "guard.output",
            f"ok={guarded.ok}; hit={guarded.hit_pattern or '-'}",
        )
    )

    return {
        "mode": "harness",
        "query": query,
        "observation": obs,
        "reply": guarded.text,
        "draft_before_guard": draft,
        "trace": [{"name": e.name, "detail": e.detail} for e in trace],
        "tenant_ok": True,
        "guard_ok": guarded.ok,
        "truncated": bool(cut["truncated"]),
        "whitelist": sorted(TOOL_WHITELIST),
        "lesson": "答案可类似；鉴权/截断/护栏/Trace 已挂上",
    }


def contrast_return_policy(query: str = "退货要几天？") -> dict[str, Any]:
    """主示例：同一问句两套外壳。"""
    bare = run_bare_model_tool(query)
    harness = run_with_harness(query, tenant_id="demo")
    harness_bad_tenant = run_with_harness(query, tenant_id="evil-corp")
    harness_promise = run_with_harness(query, inject_promise=True)
    return {
        "bare": bare,
        "harness": harness,
        "harness_bad_tenant": harness_bad_tenant,
        "harness_promise_blocked": harness_promise,
    }
