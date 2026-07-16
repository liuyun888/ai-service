# scripts/11_01_assistant_integration_demo.py
"""11.01 业务助手集成演示。

【本课要感受的三件事】
1. 决策序：先 RAG、再只读 Tool、最后作答（钉证据）
2. Harness：租户鉴权 + Tool 白名单（禁止写入类）
3. HTTP：POST /v1/assistant/chat + 内部头

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
from app.lessons.m11_01_assistant_integration import (  # noqa: E402
    DEMO_MESSAGE,
    demo_suite,
)
from app.main import app  # noqa: E402

NOTE_PATH = ROOT / "notes" / "assistant_integration_result.md"


def _headers(tenant: str = "demo") -> dict[str, str]:
    return {
        "X-Internal-Token": INTERNAL_TOKEN,
        "X-Tenant-Id": tenant,
        "X-User-Id": "u-demo",
        "X-Model-Id": "default",
        "X-Request-Id": "req-m11-01",
    }


def main() -> None:
    print("=" * 52, "CONFIG")
    print("助手 = Harness + RAG + 只读 Tool；端口联调默认 8091")
    print("ROOT =", ROOT)

    suite = demo_suite()
    note: list[str] = ["# 11.01 业务助手集成 · 实跑记录\n", ""]

    print("\n" + "=" * 52, "STEP 1 · 组合问（库存+退货）")
    c = suite["combo"]
    print("  Q:", DEMO_MESSAGE)
    print("  reply:\n ", c["reply"].replace("\n", "\n  "))
    print("  stock=", c["evidence"].get("stock"), "paths=", c["evidence"].get("doc_paths"))
    assert c["ok"]
    assert c["evidence"].get("stock") == 12
    print("ASSERT: Tool 数字 + 文档证据 → PASS")
    note.append("## STEP 1 · 组合问\n")
    note.append(f"- Q: `{DEMO_MESSAGE}`")
    note.append(f"- reply:\n\n```\n{c['reply']}\n```\n")
    note.append(f"- evidence: `{c['evidence']}`\n")

    print("\n" + "=" * 52, "STEP 2 · 坏租户被 Harness 拦住")
    b = suite["bad_tenant"]
    print(f"  ok={b['ok']} reply={b['reply'][:80]}")
    assert b["ok"] is False
    print("ASSERT: 非法租户失败 → PASS")
    note.append("## STEP 2 · 租户\n")
    note.append(f"- `{b['reply']}`\n")

    print("\n" + "=" * 52, "STEP 3 · 写入 Tool 不在白名单")
    w = suite["write_tool_blocked"]
    print(f"  create_refund allowed={w['allowed']} reason={w['reason'][:80]}")
    assert w["allowed"] is False
    print("ASSERT: 助手默认只读 → PASS")
    note.append("## STEP 3 · 只读\n")
    note.append(f"- `{w['reason']}`\n")

    print("\n" + "=" * 52, "STEP 4 · HTTP /v1/assistant/chat")
    client = TestClient(app)
    r = client.post(
        "/v1/assistant/chat",
        headers=_headers("demo"),
        json={"message": DEMO_MESSAGE, "session_id": "s1"},
    )
    print(f"  status={r.status_code}")
    body = r.json()
    print(f"  ok={body.get('ok')} stock={body.get('evidence', {}).get('stock')}")
    assert r.status_code == 200 and body.get("ok") is True
    assert "stock=12" in (body.get("reply") or "")
    # 无内部令牌应 401
    r401 = client.post(
        "/v1/assistant/chat",
        json={"message": "hi", "session_id": "s1"},
    )
    assert r401.status_code == 401
    print("ASSERT: HTTP 200 + 无令牌 401 → PASS")
    note.append("## STEP 4 · HTTP\n")
    note.append(f"- status=200 ok=`{body.get('ok')}`")
    note.append(f"- 无令牌 → `{r401.status_code}`\n")

    print("\n" + "=" * 52, "STEP 5 · curl 提示")
    print("  # 终端：uvicorn app.main:app --port 8091")
    print(
        "  curl -s http://127.0.0.1:8091/v1/assistant/chat "
        "-H 'Content-Type: application/json' "
        f"-H 'X-Internal-Token: {INTERNAL_TOKEN}' "
        "-H 'X-Tenant-Id: demo' "
        "-d '{\"message\":\"防水款还有吗？退货多久？\",\"session_id\":\"s1\"}'"
    )
    note.append("## STEP 5 · curl\n")
    note.append(
        "```bash\n"
        "curl -s http://127.0.0.1:8091/v1/assistant/chat \\\n"
        "  -H 'Content-Type: application/json' \\\n"
        f"  -H 'X-Internal-Token: {INTERNAL_TOKEN}' \\\n"
        "  -H 'X-Tenant-Id: demo' \\\n"
        "  -d '{\"message\":\"防水款还有吗？退货多久？\",\"session_id\":\"s1\"}'\n"
        "```\n"
    )

    assert suite["ok"]
    NOTE_PATH.parent.mkdir(parents=True, exist_ok=True)
    NOTE_PATH.write_text("\n".join(note), encoding="utf-8")
    print("\n笔记已写入:", NOTE_PATH)
    print("SUMMARY: assistant_integration 验收通过")


if __name__ == "__main__":
    main()
