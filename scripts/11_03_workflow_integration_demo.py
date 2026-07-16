# scripts/11_03_workflow_integration_demo.py
"""11.03 多步工作流集成演示。

【本课要感受的三件事】
1. 低风险无人审 → status=completed + mock_return_created
2. 高风险 → waiting_human；resume approved → completed
3. HTTP start/resume + 结构化字段（不只一段话）

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

from fastapi.testclient import TestClient  # noqa: E402

from app.config import INTERNAL_TOKEN  # noqa: E402
from app.lessons.m11_03_workflow_integration import (  # noqa: E402
    demo_suite,
    reset_workflow_app_for_tests,
)
from app.main import app  # noqa: E402

NOTE_PATH = ROOT / "notes" / "workflow_integration_result.md"


def _headers(tenant: str = "demo") -> dict[str, str]:
    return {
        "X-Internal-Token": INTERNAL_TOKEN,
        "X-Tenant-Id": tenant,
        "X-User-Id": "u-wf",
        "X-Model-Id": "default",
        "X-Request-Id": "req-m11-03",
    }


def main() -> None:
    print("=" * 52, "CONFIG")
    print("工作流 = LangGraph + HITL；case_id=thread_id")
    print("ROOT =", ROOT)

    suite = demo_suite()
    note: list[str] = ["# 11.03 多步工作流集成 · 实跑记录\n", ""]

    print("\n" + "=" * 52, "STEP 0 · 角色与对照")
    for r in suite["roles"][:3]:
        print(f"  {r['role']} @ {r['node']}")
    print("  analogs:", [a["industry"] for a in suite["analogs"]])
    note.append("## 角色\n")
    for r in suite["roles"]:
        note.append(f"- {r['role']} (`{r['node']}`): {r['job']}")
    note.append("")

    print("\n" + "=" * 52, "STEP 1 · 低风险自动过")
    low = suite["low"]
    print(f"  status={low['status']} risk={low['risk_level']} action={low['action_result']}")
    print(f"  msg={low['user_message'][:80]}")
    assert low["status"] == "completed" and low["action_result"] == "mock_return_created"
    print("ASSERT: 低风险无人审完成 → PASS")
    note.append("## STEP 1 · 低风险\n")
    note.append(f"- `{low}`\n")

    print("\n" + "=" * 52, "STEP 2 · 高风险暂停")
    hi = suite["high_pause"]
    print(f"  status={hi['status']} risk={hi['risk_level']} interrupted={hi.get('interrupted')}")
    assert hi["status"] == "waiting_human"
    print("ASSERT: waiting_human → PASS")
    note.append("## STEP 2 · 高风险暂停\n")
    note.append(f"- status=`{hi['status']}`\n")

    print("\n" + "=" * 52, "STEP 3 · resume 批准")
    done = suite["high_approve"]
    print(f"  status={done['status']} action={done['action_result']}")
    assert done["status"] == "completed" and done["action_result"] == "mock_return_created"
    print("ASSERT: resume 后 completed → PASS")
    note.append("## STEP 3 · 批准\n")
    note.append(f"- `{done['status']}` / `{done['action_result']}`\n")

    print("\n" + "=" * 52, "STEP 4 · resume 驳回")
    rej = suite["high_reject"]
    print(f"  status={rej['status']} action={rej['action_result']}")
    assert rej["status"] == "rejected"
    print("ASSERT: rejected → PASS")
    note.append("## STEP 4 · 驳回\n")
    note.append(f"- `{rej['status']}`\n")

    print("\n" + "=" * 52, "STEP 5 · HTTP start/resume")
    reset_workflow_app_for_tests()
    client = TestClient(app)
    r1 = client.post(
        "/v1/workflows/return/start",
        headers=_headers(),
        json={"case_id": "R-http-low", "user_request": "七天无理由退货"},
    )
    b1 = r1.json()
    print(f"  low status={r1.status_code} body.status={b1.get('status')}")
    assert r1.status_code == 200 and b1.get("status") == "completed"

    r2 = client.post(
        "/v1/workflows/return/start",
        headers=_headers(),
        json={"case_id": "R-http-high", "user_request": "破损要全额退款"},
    )
    b2 = r2.json()
    print(f"  high status={b2.get('status')}")
    assert b2.get("status") == "waiting_human"

    r3 = client.post(
        "/v1/workflows/return/resume",
        headers=_headers(),
        json={
            "case_id": "R-http-high",
            "approved": True,
            "reviewer": "ops_http",
            "note": "ok",
        },
    )
    b3 = r3.json()
    print(f"  resume status={b3.get('status')} action={b3.get('action_result')}")
    assert b3.get("status") == "completed" and b3.get("action_result") == "mock_return_created"

    r401 = client.post(
        "/v1/workflows/return/start",
        json={"case_id": "x", "user_request": "hi"},
    )
    assert r401.status_code == 401
    print("ASSERT: HTTP 路径齐全 → PASS")
    note.append("## STEP 5 · HTTP\n")
    note.append(f"- low=`{b1.get('status')}` high=`{b2.get('status')}` resume=`{b3.get('status')}`")
    note.append(f"- 无令牌 → `{r401.status_code}`\n")

    print("\n" + "=" * 52, "STEP 6 · curl 提示")
    print("  uvicorn app.main:app --port 8091")
    print(
        "  # 高风险 start → resume\n"
        "  curl -s http://127.0.0.1:8091/v1/workflows/return/start \\\n"
        f"    -H 'X-Internal-Token: {INTERNAL_TOKEN}' -H 'X-Tenant-Id: demo' \\\n"
        "    -H 'Content-Type: application/json' \\\n"
        "    -d '{\"case_id\":\"R-curl\",\"user_request\":\"破损要全额退款\"}'"
    )
    note.append("## STEP 6 · curl\n")
    note.append(
        "```bash\n"
        "curl -s http://127.0.0.1:8091/v1/workflows/return/start \\\n"
        f"  -H 'X-Internal-Token: {INTERNAL_TOKEN}' -H 'X-Tenant-Id: demo' \\\n"
        "  -H 'Content-Type: application/json' \\\n"
        "  -d '{\"case_id\":\"R-curl\",\"user_request\":\"破损要全额退款\"}'\n"
        "curl -s http://127.0.0.1:8091/v1/workflows/return/resume \\\n"
        f"  -H 'X-Internal-Token: {INTERNAL_TOKEN}' -H 'X-Tenant-Id: demo' \\\n"
        "  -H 'Content-Type: application/json' \\\n"
        "  -d '{\"case_id\":\"R-curl\",\"approved\":true,\"reviewer\":\"ops_01\"}'\n"
        "```\n"
    )

    assert suite["ok"]
    NOTE_PATH.parent.mkdir(parents=True, exist_ok=True)
    NOTE_PATH.write_text("\n".join(note), encoding="utf-8")
    print("\n笔记已写入:", NOTE_PATH)
    print("SUMMARY: workflow_integration 验收通过")


if __name__ == "__main__":
    main()
