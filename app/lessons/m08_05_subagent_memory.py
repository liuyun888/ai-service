# app/lessons/m08_05_subagent_memory.py
"""课次 08.05 · 子 Agent 委派 + Memory Store 主示例。

流程：父 todos → research_agent → writer_agent → memory_get 偏好 → 润色定稿。
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from app.harness.context.vfs import DEFAULT_VFS, VirtualFS
from app.harness.memory.store import DEFAULT_MEMORY, MemoryStore
from app.harness.skills.registry import list_skills, load_brief
from app.harness.subagent import (
    DelegateBudget,
    polish_with_pref,
    run_subagent,
)

DEMO_GOAL = "写一份退货体验改进草案"
PREF_KEY = "user:demo:pref"
DEFAULT_PREF = "条目制；少形容词；避免绝对承诺"
# 父闲聊里放探针：子上下文若串味会被检测
PARENT_CHAT_PROBE = "闲聊污染探针：用户说想听笑话，与退货无关"


def research_handler(brief: str, attachments: dict[str, Any]) -> dict[str, Any]:
    """research_agent：只读 VFS，产出 Top3 JSON。"""
    _ = brief
    vfs: VirtualFS = attachments.get("vfs") or DEFAULT_VFS
    complaints = vfs.read_doc("case/complaints_week.md", offset=0, limit=900)
    policy = vfs.read_doc("manual/return_policy.md", offset=0, limit=500)
    tops = re.findall(r"\*\*(.+?)\*\*", complaints)
    if len(tops) < 3:
        tops = ["已拆封口径冲突", "退款时限不清", "破损误判无理由"]
    problems = []
    for title in tops[:3]:
        path = "case/complaints_week.md"
        evidence = title
        if "拆封" in title or "无理由" in title:
            path = "manual/return_policy.md"
            evidence = "政策：已拆封通常不支持无理由→质量问题通道"
        problems.append({"title": title, "evidence": evidence, "path": path})
    return {
        "summary": f"Top3 问题已提取（policy_len={len(policy)}）",
        "problems": problems,
    }


def writer_handler(brief: str, attachments: dict[str, Any]) -> dict[str, Any]:
    """writer_agent：只看 JSON，不读全库。"""
    _ = brief
    problems = attachments.get("problems") or []
    lines = ["# 退货体验改进草案（子 Agent 写作）", ""]
    for i, p in enumerate(problems, 1):
        title = p.get("title", "")
        lines.append(f"{i}. 问题：{title}")
        lines.append(f"   - 动作：针对「{title}」统一话术与流程卡")
        lines.append("   - 度量：相关投诉周环比下降")
        lines.append(f"   - 证据路径：{p.get('path', '')}")
    lines.append("")
    lines.append("依据来自 research JSON；未额外检索全库。")
    # 故意塞一个会被偏好滤掉的坏词，供润色演示
    lines.append("（草稿语气：非常完美的方案，保证全额一定赔付——应交父级按偏好删掉）")
    draft = "\n".join(lines)
    return {"summary": "大纲已写", "draft": draft}


def seed_preference(store: MemoryStore | None = None, *, tenant_id: str = "demo") -> str:
    """写入用户偏好（仅明确授权内容）。"""
    mem = store or DEFAULT_MEMORY
    mem.put(PREF_KEY, DEFAULT_PREF, tenant_id=tenant_id, source="user_explicit")
    return DEFAULT_PREF


def run_parent_pipeline(
    *,
    store: MemoryStore | None = None,
    vfs: VirtualFS | None = None,
    tenant_id: str = "demo",
) -> dict[str, Any]:
    """父 Agent 编排：委派 research → writer → 读记忆润色。"""
    mem = store or DEFAULT_MEMORY
    fs = vfs or DEFAULT_VFS
    budget = DelegateBudget(max_depth=1, max_children=4)
    parent_messages = [
        {"role": "user", "content": PARENT_CHAT_PROBE},
        {"role": "assistant", "content": "好的我们先聊笑话…"},
    ]
    todos = [
        "写 todos / 定验收",
        "task(research_agent)",
        "task(writer_agent)",
        "memory_get 偏好并润色",
        "输出最终稿",
    ]
    trajectory: list[dict[str, Any]] = [{"event": "write_todos", "todos": todos}]

    # 确保有偏好（幂等）
    if mem.get(PREF_KEY, tenant_id=tenant_id) is None:
        seed_preference(mem, tenant_id=tenant_id)

    research = run_subagent(
        "research_agent",
        attachments={"vfs": fs},
        parent_messages=parent_messages,
        depth=0,
        budget=budget,
        handler=research_handler,
    )
    trajectory.append(
        {
            "event": "task",
            "skill": "research_agent",
            "ok": research.ok,
            "child_message_count": research.child_message_count,
            "summary": research.summary,
            "problems": research.data.get("problems"),
            "leak": research.error == "leak_detected",
        }
    )

    writer = run_subagent(
        "writer_agent",
        attachments={"problems": research.data.get("problems") or []},
        parent_messages=parent_messages,
        depth=0,
        budget=budget,
        handler=writer_handler,
    )
    trajectory.append(
        {
            "event": "task",
            "skill": "writer_agent",
            "ok": writer.ok,
            "child_message_count": writer.child_message_count,
            "summary": writer.summary,
            "leak": writer.error == "leak_detected",
        }
    )

    pref = mem.get(PREF_KEY, tenant_id=tenant_id)
    trajectory.append(
        {
            "event": "memory_get",
            "key": PREF_KEY,
            "value": pref,
            "labeled": "来自记忆",
        }
    )

    draft = str((writer.data or {}).get("draft") or "")
    final = polish_with_pref(draft, pref)
    # 存一份项目记忆（case 级）
    mem.put(
        "case:return-ux:summary",
        final[:400],
        tenant_id=tenant_id,
        source="confirmed",
    )
    trajectory.append({"event": "finish", "final_chars": len(final)})

    return {
        "goal": DEMO_GOAL,
        "todos": todos,
        "research": {
            "ok": research.ok,
            "problems": research.data.get("problems"),
            "child_message_count": research.child_message_count,
            "error": research.error,
        },
        "writer": {
            "ok": writer.ok,
            "child_message_count": writer.child_message_count,
            "error": writer.error,
        },
        "pref": pref,
        "final": final,
        "trajectory": trajectory,
        "budget": {
            "children_used": budget.children_used,
            "max_children": budget.max_children,
            "max_depth": budget.max_depth,
        },
        "isolation_ok": (
            research.error != "leak_detected"
            and writer.error != "leak_detected"
            and research.child_message_count <= 2
            and writer.child_message_count <= 2
        ),
        "nested_blocked": _try_nested_delegate(budget),
        "tenant_note": "生产必须按 tenant_id 隔离；本课 get/put 已带租户作用域",
    }


def _try_nested_delegate(budget: DelegateBudget) -> dict[str, Any]:
    """演示：depth 已到上限时再委派应失败。"""
    # 模拟子内部 depth=1 再调
    res = run_subagent(
        "research_agent",
        depth=1,
        budget=budget,
        handler=research_handler,
        attachments={},
    )
    return {"ok": res.ok, "error": res.error}


def demo_memory_persist(path: Path) -> dict[str, Any]:
    """跨「两次构造」仍能 get（文件持久化）。"""
    if path.exists():
        path.unlink()
    a = MemoryStore(persist_path=path)
    a.put(PREF_KEY, DEFAULT_PREF, tenant_id="demo", source="user_explicit")
    b = MemoryStore(persist_path=path)
    got = b.get(PREF_KEY, tenant_id="demo")
    other = b.get(PREF_KEY, tenant_id="other-tenant")
    return {
        "path": str(path),
        "got": got,
        "other_tenant_miss": other is None,
        "audit_ops": [x["op"] for x in b.audit],
    }


def demo_tenant_isolation() -> dict[str, Any]:
    """同 key 不同租户互不可见。"""
    mem = MemoryStore()
    mem.put(PREF_KEY, "租户A偏好", tenant_id="A", source="user_explicit")
    mem.put(PREF_KEY, "租户B偏好", tenant_id="B", source="user_explicit")
    return {
        "A": mem.get(PREF_KEY, tenant_id="A"),
        "B": mem.get(PREF_KEY, tenant_id="B"),
        "A_cannot_see_B_value": mem.get(PREF_KEY, tenant_id="A") != "租户B偏好",
    }


def demo_suite(*, notes_dir: Path | None = None) -> dict[str, Any]:
    """本课一键套件。"""
    root = notes_dir or Path(__file__).resolve().parents[2] / "notes"
    persist = root / "memory_store_demo.json"
    pipeline = run_parent_pipeline()
    return {
        "skills": list_skills(),
        "brief_research_head": load_brief("research_agent")[:120],
        "pipeline": pipeline,
        "persist": demo_memory_persist(persist),
        "tenant": demo_tenant_isolation(),
        "pref_key": PREF_KEY,
    }
