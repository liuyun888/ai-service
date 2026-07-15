# scripts/08_06_middleware_eval_demo.py
"""08.06 Middleware、压缩与评估演示（M08 收束）。

【本课要感受的三件事】
1. 中间件链：Authz / PIIRedact / TokenLog / CommitmentGuard 钩子生效
2. Compaction：长对话降字符，保留 system 硬约束与路径指针
3. 可回放 Trace JSON + 里程碑自检 + 护栏单测

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

from app.lessons.m08_06_middleware_eval import demo_suite  # noqa: E402
from tests.test_harness import run_all as run_unit_tests  # noqa: E402

NOTE_PATH = ROOT / "notes" / "middleware_eval_result.md"


def main() -> None:
    print("=" * 52, "CONFIG")
    print("Middleware 挂钩子；Compaction 管寿命；Trace 留证据")
    print("ROOT =", ROOT)

    suite = demo_suite(notes_dir=ROOT / "notes")
    note: list[str] = [
        "# 08.06 Middleware / Compaction / Trace · 实跑记录\n",
        "",
    ]

    # ---- STEP 1 · 承诺拦截 ----
    print("\n" + "=" * 52, "STEP 1 · CommitmentGuard + TokenLog + PII")
    c = suite["commitment"]
    print(f"  user: {c['user']}")
    print(f"  draft: {c['draft']}")
    print(f"  final: {c['final'][:80]}")
    print(f"  hooks: {c['hooks']}")
    print(
        f"  guard_triggered={c['guard_triggered']} token_logged={c['token_logged']} "
        f"pii_redacted={c['pii_redacted']}"
    )
    assert c["guard_triggered"]
    assert c["token_logged"]
    assert c["pii_redacted"]
    assert "绝对承诺" in c["final"]
    assert "13800138000" not in c["ctx"].tool_observation
    print("ASSERT: 护栏拦截 + Token 记录 + PII 脱敏 → PASS")
    note.append("## STEP 1 · 合规链路\n")
    note.append(f"- draft → final: {c['final']}")
    note.append(f"- hooks: `{c['hooks']}`\n")

    # ---- STEP 2 · Authz ----
    print("\n" + "=" * 52, "STEP 2 · before_tool Authz")
    a = suite["authz"]
    print(f"  allowed={a['allowed']} detail={a['detail']}")
    assert a["allowed"] is False
    assert "hitl" in (a["detail"] or "") or "refund" in (a["detail"] or "")
    print("ASSERT: 高风险 Tool 被拒 → PASS")
    note.append("## STEP 2 · Authz\n")
    note.append(f"- {a['detail']}\n")

    # ---- STEP 3 · Compaction ----
    print("\n" + "=" * 52, "STEP 3 · Compaction")
    k = suite["compaction"]
    print(
        f"  msgs {k['message_count_before']}→{k['message_count_after']} | "
        f"chars {k['before_chars']}→{k['after_chars']} saved={k['saved_chars']}"
    )
    print(f"  pointers: {k['pointers'][:5]}")
    print(f"  summary: {k['summary'][:100]}")
    assert k["compacted"]
    assert k["after_chars"] < k["before_chars"]
    assert k["kept_system"]
    assert k["pointers"]
    print("ASSERT: 压缩降 token 且保留硬约束/指针 → PASS")
    note.append("## STEP 3 · Compaction\n")
    note.append(
        f"- before={k['before_chars']} after={k['after_chars']} pointers={k['pointers']}\n"
    )

    # ---- STEP 4 · Trace ----
    print("\n" + "=" * 52, "STEP 4 · Trace JSON")
    tp = Path(suite["trace_path"])
    print(f"  path: {tp}")
    assert tp.is_file()
    text = tp.read_text(encoding="utf-8")
    assert "CommitmentGuard" in text
    assert "13800138000" not in text
    print("ASSERT: 可打开且已脱敏的 Trace → PASS")
    note.append("## STEP 4 · Trace\n")
    note.append(f"- `{tp}`\n")

    # ---- STEP 5 · 单测 ----
    print("\n" + "=" * 52, "STEP 5 · tests/test_harness.py")
    run_unit_tests()
    assert suite["unit_guard"]["pass_safe"] and suite["unit_guard"]["block_risk"]
    print("ASSERT: 护栏单测套件 → PASS")
    note.append("## STEP 5 · 单测\n\n- run_all ok\n")

    # ---- STEP 6 · 里程碑 ----
    print("\n" + "=" * 52, "STEP 6 · M08 里程碑自检")
    m = suite["milestone"]
    for row in m["rows"]:
        mark = "OK" if row["exists"] else "MISS"
        print(f"  [{mark}] {row['id']} {row['capability']}")
    print(f"  ready {m['ready_count']}/{m['total']}")
    assert m["ok"]
    print("ASSERT: M08 六课关键落点齐全 → PASS")
    note.append("## STEP 6 · 里程碑\n")
    for row in m["rows"]:
        note.append(f"- [{'x' if row['exists'] else ' '}] {row['id']} {row['capability']}")
    note.append("")

    NOTE_PATH.parent.mkdir(parents=True, exist_ok=True)
    NOTE_PATH.write_text("\n".join(note), encoding="utf-8")
    print("\n笔记已写入:", NOTE_PATH)
    print("SUMMARY: middleware_eval 验收通过（M08 里程碑可勾选）")


if __name__ == "__main__":
    main()
