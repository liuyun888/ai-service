# scripts/13_02_observability_cost_demo.py
"""13.02 可观测、评估与成本调优演示。

【本课要感受的三件事】
1. 导出可回放 Trace（tmp/trace-final.json）
2. 写出成本/调优笔记（先 Harness 再换模）
3. 金标抽检 + Harness/抽取单测可跑

工作目录：必须在 ai-service/ 下。
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from app.lessons.m13_02_observability_cost import demo_suite  # noqa: E402

NOTE_PATH = ROOT / "notes" / "observability_cost_result.md"


def run_unit_tests() -> dict:
    """跑 Harness + 抽取校验单测（不依赖 pytest）。"""
    results = []
    for script in ("tests/test_harness.py", "tests/test_extract_validate.py"):
        p = subprocess.run(
            [sys.executable, str(ROOT / script)],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        results.append(
            {
                "script": script,
                "ok": p.returncode == 0,
                "stdout_tail": (p.stdout or "")[-200:],
                "stderr_tail": (p.stderr or "")[-200:],
            }
        )
    return {"ok": all(r["ok"] for r in results), "results": results}


def main() -> None:
    print("=" * 52, "13.02 observability + cost")

    print("\n" + "=" * 52, "STEP 1 · Trace + 金标 + 成本笔记")
    suite = demo_suite()
    print(json.dumps({k: suite[k] for k in suite if k != "mantra"}, ensure_ascii=False, indent=2))
    print("mantra=", suite["mantra"])
    assert suite["ok"], suite
    assert Path(suite["trace_path"]).is_file()
    assert Path(suite["note_path"]).is_file()
    print("ASSERT: trace-final + cost note + gold → PASS")

    print("\n" + "=" * 52, "STEP 2 · 单测")
    tests = run_unit_tests()
    print(json.dumps(tests, ensure_ascii=False, indent=2))
    assert tests["ok"], tests
    print("ASSERT: test_harness + test_extract_validate → PASS")

    NOTE_PATH.parent.mkdir(parents=True, exist_ok=True)
    NOTE_PATH.write_text(
        "\n".join(
            [
                "# 13.02 可观测与成本 · 验收笔记",
                "",
                f"- Trace：`{suite['trace_path']}`（trace_id=`{suite['trace_id']}`）",
                f"- 成本笔记：`{suite['note_path']}`",
                f"- 金标：`{suite['gold']}`",
                f"- 专栏自检：`{suite['checklist']}`",
                f"- 单测：`{tests['ok']}`",
                "",
                "迭代口诀：先 Harness → 再数据 → 后模型",
                "",
                "SUMMARY: observability_cost 验收通过",
                "",
            ]
        ),
        encoding="utf-8",
    )
    print("\nNOTE →", NOTE_PATH)
    print("SUMMARY: 13.02 验收通过（专栏收官课）")


if __name__ == "__main__":
    main()
