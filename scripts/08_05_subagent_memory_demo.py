# scripts/08_05_subagent_memory_demo.py
"""08.05 子 Agent 与长期记忆演示。

【本课要感受的三件事】
1. 父委派 research / writer，子上下文隔离（不吃父闲聊）
2. Memory put/get 跨两次构造仍在；租户隔离
3. 最终稿按「来自记忆」的偏好润色，且深度限制防套娃

工作目录：必须在 ai-service/ 下。
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from app.lessons.m08_05_subagent_memory import (  # noqa: E402
    DEFAULT_PREF,
    PARENT_CHAT_PROBE,
    demo_suite,
)

NOTE_PATH = ROOT / "notes" / "subagent_memory_result.md"


def main() -> None:
    print("=" * 52, "CONFIG")
    print("子 Agent = 隔离 brief；Memory = 跨会话抽屉")
    print("ROOT =", ROOT)

    suite = demo_suite(notes_dir=ROOT / "notes")
    pipe = suite["pipeline"]
    note: list[str] = [
        "# 08.05 子 Agent 与长期记忆 · 实跑记录\n",
        "",
        f"- goal: {pipe['goal']}",
        f"- skills: {suite['skills']}",
        "",
    ]

    # ---- STEP 1 · brief 模板 ----
    print("\n" + "=" * 52, "STEP 1 · Skill / brief 模板")
    print("  skills:", suite["skills"])
    print("  research brief head:", suite["brief_research_head"].replace("\n", " ")[:100])
    assert set(suite["skills"]) >= {"research_agent", "writer_agent"}
    assert "输出" in suite["brief_research_head"] or "JSON" in suite["brief_research_head"]
    print("ASSERT: brief 独立文件且含 schema → PASS")
    note.append("## STEP 1 · skills\n")
    note.append(f"- `{suite['skills']}`\n")

    # ---- STEP 2 · 委派 + 隔离 ----
    print("\n" + "=" * 52, "STEP 2 · 父委派 research → writer")
    print(f"  parent probe (不应泄漏): {PARENT_CHAT_PROBE[:40]}…")
    print(f"  research.ok={pipe['research']['ok']} msgs={pipe['research']['child_message_count']}")
    print(f"  problems: {json_preview(pipe['research']['problems'])}")
    print(f"  writer.ok={pipe['writer']['ok']} msgs={pipe['writer']['child_message_count']}")
    print(f"  isolation_ok={pipe['isolation_ok']}")
    assert pipe["research"]["ok"] and pipe["writer"]["ok"]
    assert len(pipe["research"]["problems"] or []) == 3
    assert pipe["isolation_ok"]
    assert PARENT_CHAT_PROBE not in pipe["final"]
    print("ASSERT: 结构化回收 + 上下文未串味 → PASS")
    note.append("## STEP 2 · 委派\n")
    note.append(f"- problems: `{pipe['research']['problems']}`")
    note.append(f"- isolation_ok: {pipe['isolation_ok']}\n")

    # ---- STEP 3 · 防套娃 ----
    print("\n" + "=" * 52, "STEP 3 · 深度限制（防套娃）")
    nested = pipe["nested_blocked"]
    print(f"  nested attempt ok={nested['ok']} error={nested['error']}")
    print(f"  budget: {pipe['budget']}")
    assert nested["ok"] is False
    assert "depth" in (nested.get("error") or "")
    print("ASSERT: 子再开子被拒 → PASS")
    note.append("## STEP 3 · 防套娃\n")
    note.append(f"- `{nested}`\n")

    # ---- STEP 4 · Memory 持久化 ----
    print("\n" + "=" * 52, "STEP 4 · Memory put/get 持久化")
    p = suite["persist"]
    print(f"  path={p['path']}")
    print(f"  got={p['got']!r}")
    print(f"  other_tenant_miss={p['other_tenant_miss']}")
    assert p["got"] == DEFAULT_PREF
    assert p["other_tenant_miss"] is True
    print("ASSERT: 第二次构造仍能 get；跨租户 miss → PASS")
    note.append("## STEP 4 · Memory 文件\n")
    note.append(f"- got: {p['got']}")
    note.append(f"- path: `{p['path']}`\n")

    # ---- STEP 5 · 租户隔离说明 ----
    print("\n" + "=" * 52, "STEP 5 · 租户隔离")
    t = suite["tenant"]
    print(f"  A={t['A']!r} B={t['B']!r}")
    assert t["A"] == "租户A偏好" and t["B"] == "租户B偏好"
    assert t["A_cannot_see_B_value"]
    print("  生产要求:", pipe["tenant_note"])
    print("ASSERT: 同 key 不同 tenant 互不可见 → PASS")
    note.append("## STEP 5 · 租户\n")
    note.append(f"- {t}")
    note.append(f"- {pipe['tenant_note']}\n")

    # ---- STEP 6 · 偏好润色 ----
    print("\n" + "=" * 52, "STEP 6 · 记忆偏好润色最终稿")
    print(f"  pref: {pipe['pref']}")
    print("  final head:")
    print("  ", pipe["final"][:180].replace("\n", "\n   "))
    assert pipe["pref"]
    assert "来自记忆" in pipe["final"] or "记忆偏好" in pipe["final"]
    assert "保证全额" not in pipe["final"] or "已按偏好去掉" in pipe["final"]
    print("ASSERT: 最终稿标明记忆偏好 → PASS")
    note.append("## STEP 6 · 最终稿\n")
    note.append("```")
    note.append(pipe["final"][:1200])
    note.append("```\n")

    NOTE_PATH.parent.mkdir(parents=True, exist_ok=True)
    NOTE_PATH.write_text("\n".join(note), encoding="utf-8")
    print("\n笔记已写入:", NOTE_PATH)
    print("SUMMARY: subagent_memory 验收通过")


def json_preview(obj: object) -> str:
    import json

    return json.dumps(obj, ensure_ascii=False)[:160]


if __name__ == "__main__":
    main()
