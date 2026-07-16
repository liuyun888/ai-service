# scripts/10_04_internal_auth_demo.py
"""10.04 ai-service 内部鉴权演示。

【本课（service 侧）】
1. 无 X-Internal-Token → 401
2. 有令牌无 X-Tenant-Id → 400
3. 合法头 → /v1/context/echo 回显租户
4. SSE done 事件带上 tenant / request_id

工作目录：必须在 ai-service/ 下。
BFF 侧见 ai-bff/scripts/10_04_auth_passthrough_demo.py。
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from app.lessons.m10_04_internal_auth import demo_suite  # noqa: E402

NOTE_PATH = ROOT / "notes" / "internal_auth_result.md"


def main() -> None:
    print("=" * 52, "CONFIG")
    print("ai-service 只验内部头；用户 JWT 止于 BFF")
    print("ROOT =", ROOT)

    suite = demo_suite()
    note: list[str] = ["# 10.04 ai-service 内部鉴权 · 实跑记录\n", ""]

    print("\n" + "=" * 52, "STEP 1 · 无内部令牌")
    m = suite["missing_token"]
    print(f"  status={m['status_code']} detail={m['detail']}")
    assert m["status_code"] == 401
    print("ASSERT: 401 unauthorized internal → PASS")
    note.append("## STEP 1\n")
    note.append(f"- 无令牌 → `{m['status_code']}`\n")

    print("\n" + "=" * 52, "STEP 2 · 缺租户头")
    t = suite["missing_tenant"]
    print(f"  status={t['status_code']} detail={t['detail']}")
    assert t["status_code"] == 400
    print("ASSERT: 400 missing tenant → PASS")
    note.append("## STEP 2\n")
    note.append(f"- 缺租户 → `{t['status_code']}`\n")

    print("\n" + "=" * 52, "STEP 3 · echo 回显")
    e = suite["echo"]
    print(f"  status={e['status_code']} body={e['body']}")
    assert e["status_code"] == 200
    assert e["body"]["tenant_id"] == "tenant-a"
    print("ASSERT: tenant + request_id 到达 → PASS")
    note.append("## STEP 3\n")
    note.append(f"- echo: `{e['body']}`\n")

    print("\n" + "=" * 52, "STEP 4 · SSE done 带上下文")
    s = suite["stream"]
    print(f"  done={s['done']}")
    assert s["done"].get("tenant_id") == "tenant-a"
    assert s["done"].get("request_id") == "req-demo-001"
    print("ASSERT: done 含租户与 request_id → PASS")
    note.append("## STEP 4\n")
    note.append(f"- done: `{s['done']}`\n")

    assert suite["ok"]
    NOTE_PATH.parent.mkdir(parents=True, exist_ok=True)
    NOTE_PATH.write_text("\n".join(note), encoding="utf-8")
    print("\n笔记已写入:", NOTE_PATH)
    print("SUMMARY: internal_auth（ai-service）验收通过")


if __name__ == "__main__":
    main()
