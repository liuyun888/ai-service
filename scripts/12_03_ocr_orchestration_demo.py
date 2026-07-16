# scripts/12_03_ocr_orchestration_demo.py
"""12.03 OCR/上游编排演示。

【本课要感受的三件事】
1. mock OCR → 抽取 → 校验 分阶段，可替换 OCR 供应商
2. 空文本 / 过短有明确 status，不硬调抽取
3. HTTP：POST /v1/extract/invoice + 内部头

工作目录：必须在 ai-service/ 下。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from fastapi.testclient import TestClient  # noqa: E402

from app.config import INTERNAL_TOKEN  # noqa: E402
from app.lessons.m12_03_ocr_orchestration import demo_suite, run_invoice_pipeline  # noqa: E402
from app.main import app  # noqa: E402

NOTE_PATH = ROOT / "notes" / "ocr_orchestration_result.md"


def _headers(tenant: str = "demo") -> dict[str, str]:
    return {
        "X-Internal-Token": INTERNAL_TOKEN,
        "X-Tenant-Id": tenant,
        "X-User-Id": "u-demo",
        "X-Request-Id": "req-12-03",
    }


def main() -> None:
    print("=" * 52, "12.03 OCR orchestration")

    print("\n" + "=" * 52, "STEP 1 · 离线流水线")
    suite = demo_suite()
    print(json.dumps(suite, ensure_ascii=False, indent=2))
    assert suite["ok"], suite
    print("ASSERT: ocr_ok + empty/short/missing/paste → PASS")

    print("\n" + "=" * 52, "STEP 2 · HTTP /v1/extract/invoice")
    client = TestClient(app)
    r = client.post(
        "/v1/extract/invoice",
        headers=_headers(),
        json={"source": "ocr_mock", "image_id": "img-1"},
    )
    print("status_code=", r.status_code, r.json())
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["data"]["invoice_no"] == "INV-2026-001"

    r401 = client.post(
        "/v1/extract/invoice",
        json={"source": "ocr_mock", "image_id": "img-1"},
    )
    assert r401.status_code == 401
    print("ASSERT: HTTP ok + 无令牌 401 → PASS")

    print("\n" + "=" * 52, "STEP 3 · 空 OCR")
    empty = run_invoice_pipeline(source="ocr_mock", image_id="img-empty")
    assert empty["status"] == "ocr_failed"
    print("empty status=", empty["status"], "errors=", empty["errors"])

    NOTE_PATH.parent.mkdir(parents=True, exist_ok=True)
    NOTE_PATH.write_text(
        "\n".join(
            [
                "# 12.03 OCR/上游编排 · 验收笔记",
                "",
                "## demo_suite",
                "```json",
                json.dumps(suite, ensure_ascii=False, indent=2),
                "```",
                "",
                "## HTTP",
                f"- `/v1/extract/invoice` ocr_mock img-1 → `{body['status']}`",
                f"- invoice_no=`{body['data']['invoice_no']}` amount=`{body['data']['amount']}`",
                "",
                "```bash",
                "curl -s http://127.0.0.1:8091/v1/extract/invoice \\",
                "  -H 'Content-Type: application/json' \\",
                "  -H 'X-Internal-Token: dev-internal-token' \\",
                "  -H 'X-Tenant-Id: demo' \\",
                "  -d '{\"source\":\"ocr_mock\",\"image_id\":\"img-1\"}'",
                "```",
                "",
                "SUMMARY: ocr_orchestration 验收通过",
                "",
            ]
        ),
        encoding="utf-8",
    )
    print("\nNOTE →", NOTE_PATH)
    print("SUMMARY: 12.03 验收通过")


if __name__ == "__main__":
    main()
