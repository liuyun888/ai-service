# app/lessons/m08_03_context_engineering.py
"""课次 08.03 · Context Engineering：预装对照 + 按需 list/search/read。

默认离线脚本轨迹即可验收；USE_CHAT=1 时走真模型 bind_tools。
"""

from __future__ import annotations

import os
from typing import Any

from app.harness.context.tools import CONTEXT_TOOLS, make_context_tools
from app.harness.context.vfs import DEFAULT_VFS, VirtualFS

# 主示例问句（与正文一致）
DEMO_QUESTION = "七天无理由是否包含已拆封？"

ONDEMAND_SYSTEM = """你是客服助手。知识在虚拟文件树里，不要编造政策。
规则：
1. 先 list_docs 或 search_docs，再 read_doc 相关片段；
2. 回答必须引用具体路径（如 manual/return_policy.md）；
3. 禁止把整本手册背进上下文——只用工具取回的片段。

当前可见目录（无正文）：
{tree}
"""


def compare_prompt_budgets(vfs: VirtualFS | None = None) -> dict[str, Any]:
    """对照：整本预装 vs 只塞目录树 的 Prompt 体积。

    返回:
        stuff_chars / tree_chars / ratio 等，方便打印断言
    """
    fs = vfs or DEFAULT_VFS
    tree = fs.tree_summary("")
    ondemand_prompt = ONDEMAND_SYSTEM.format(tree=tree) + "\n\n用户问：" + DEMO_QUESTION
    # 差做法：把 manual 全部正文硬塞
    stuffed_body = []
    for rel in fs.list_docs("manual"):
        stuffed_body.append(f"===== {rel} =====\n{(fs.root / rel).read_text(encoding='utf-8')}")
    stuffed_prompt = (
        "你是客服，以下是全部手册，请直接回答。\n\n"
        + "\n\n".join(stuffed_body)
        + "\n\n用户问："
        + DEMO_QUESTION
    )
    stuff_chars = len(stuffed_prompt)
    tree_chars = len(ondemand_prompt)
    return {
        "question": DEMO_QUESTION,
        "stuff_chars": stuff_chars,
        "tree_chars": tree_chars,
        "saved_chars": stuff_chars - tree_chars,
        "ratio_stuff_over_tree": round(stuff_chars / max(tree_chars, 1), 2),
        "tree_preview": tree,
        "manual_file_count": len(fs.list_docs("manual")),
    }


def run_scripted_ondemand(vfs: VirtualFS | None = None) -> dict[str, Any]:
    """离线脚本：模拟 Agent 轨迹 list → search → read → 作答。

    不调模型也能验收「按需加载」；轨迹字段与真 Agent 同构，方便对照。
    """
    fs = vfs or DEFAULT_VFS
    trace: list[dict[str, Any]] = []

    listed = fs.list_docs("manual")
    trace.append({"tool": "list_docs", "args": {"prefix": "manual"}, "observation": listed})

    hits = fs.search_docs("已拆封")
    trace.append(
        {
            "tool": "search_docs",
            "args": {"query": "已拆封"},
            "observation": hits,
        }
    )

    # 定位 return_policy，读前半段（含 §2.1）
    path = "manual/return_policy.md"
    chunk = fs.read_doc(path, offset=0, limit=900)
    trace.append(
        {
            "tool": "read_doc",
            "args": {"path": path, "offset": 0, "limit": 900},
            "observation": chunk[:400] + ("…" if len(chunk) > 400 else ""),
        }
    )

    reply = (
        "一般不支持七天无理由：外包装已拆、影响二次销售的，走质量问题退换。"
        "依据：`manual/return_policy.md` §2.1。"
        "若有功能故障，可按同文件第 3 章举证申请。"
    )
    # 启动 Prompt 只含目录（示范值）
    startup_chars = len(ONDEMAND_SYSTEM.format(tree=fs.tree_summary("")))
    # 实际进入窗口的工具结果字符（粗估）
    tool_payload_chars = sum(len(str(t["observation"])) for t in trace)

    return {
        "mode": "scripted",
        "question": DEMO_QUESTION,
        "reply": reply,
        "trace": trace,
        "cited_path": path,
        "startup_prompt_chars": startup_chars,
        "tool_payload_chars": tool_payload_chars,
        "tools_used": [t["tool"] for t in trace],
    }


def run_safety_checks(vfs: VirtualFS | None = None) -> dict[str, Any]:
    """路径穿越 / 密钥目录 / max_chars 截断 三连验收。"""
    fs = vfs or DEFAULT_VFS
    outside = fs.read_doc("../.env")
    secret = fs.read_doc("secrets/do_not_read.env")
    big = fs.read_doc("manual/return_policy.md", offset=0, limit=50_000, max_chars=200)
    return {
        "outside_blocked": str(outside).startswith("error="),
        "outside_msg": outside,
        "secret_blocked": str(secret).startswith("error="),
        "secret_msg": secret,
        "truncated_ok": "…[truncated" in big or len(big) < 800,
        "read_sample_head": big[:120],
        "max_chars": fs.max_chars,
    }


def run_ondemand_llm(
    question: str | None = None,
    *,
    vfs: VirtualFS | None = None,
    max_steps: int = 6,
) -> dict[str, Any]:
    """真模型：只给目录 + Tools，观察是否先 search/read。

    前提:
        环境变量 USE_CHAT=1，且 .env 已配置可用模型。
    """
    from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage

    from app.models.factory import get_chat_model

    fs = vfs or DEFAULT_VFS
    q = question or DEMO_QUESTION
    tools = make_context_tools(fs)
    catalog = {t.name: t for t in tools}
    model = get_chat_model(temperature=0.1).bind_tools(tools)
    messages: list[Any] = [
        SystemMessage(content=ONDEMAND_SYSTEM.format(tree=fs.tree_summary(""))),
        HumanMessage(content=q),
    ]
    trace: list[dict[str, Any]] = []

    for step in range(1, max_steps + 1):
        ai = model.invoke(messages)
        messages.append(ai)
        calls = getattr(ai, "tool_calls", None) or []
        if not calls:
            answer = str(ai.content or "").strip() or "(空回复)"
            return {
                "mode": "llm",
                "question": q,
                "reply": answer,
                "trace": trace,
                "tools_used": [t["tool"] for t in trace],
                "steps": step,
                "cited_ok": "manual/return_policy" in answer or "return_policy" in answer,
            }
        for tc in calls:
            name = tc.get("name") or ""
            args = tc.get("args") or {}
            tc_id = tc.get("id") or f"call_{step}_{name}"
            fn = catalog.get(name)
            try:
                obs = str(fn.invoke(args)) if fn else f"error: unknown tool {name}"
            except Exception as exc:  # noqa: BLE001
                obs = f"error: {type(exc).__name__}: {exc}"
            trace.append({"tool": name, "args": args, "observation": obs[:500]})
            messages.append(ToolMessage(content=obs, tool_call_id=tc_id))

    return {
        "mode": "llm",
        "question": q,
        "reply": "已达最大步数仍未结束。",
        "trace": trace,
        "tools_used": [t["tool"] for t in trace],
        "steps": max_steps,
        "cited_ok": False,
    }


def demo_suite(*, use_chat: bool | None = None) -> dict[str, Any]:
    """本课一键套件：预算对照 + 脚本轨迹 + 安全检查（+ 可选 LLM）。"""
    if use_chat is None:
        use_chat = os.getenv("USE_CHAT", "0").strip().lower() in {"1", "true", "yes", "on"}
    budget = compare_prompt_budgets()
    scripted = run_scripted_ondemand()
    safety = run_safety_checks()
    llm_result = run_ondemand_llm() if use_chat else None
    return {
        "use_chat": use_chat,
        "budget": budget,
        "scripted": scripted,
        "safety": safety,
        "llm": llm_result,
        "tool_names": [t.name for t in CONTEXT_TOOLS],
        "vfs_root": str(DEFAULT_VFS.root),
    }
