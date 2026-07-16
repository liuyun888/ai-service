# scripts/12_02_validate_retry_demo.py
"""12.02 校验与失败重试演示。

【本课要感受的三件事】
1. Pydantic Schema 拦住非法 amount/date
2. 短错误回灌，有限次重试后可修好
3. 仍失败 → need_human；校验前绝不写库

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

from app.chains.extract_validate import (  # noqa: E402
    BAD_AMOUNT_PAYLOAD,
    extract_with_retry,
    make_flaky_extractor,
    validate_invoice,
)
from app.lessons.m12_02_validate_retry import demo_suite  # noqa: E402
from app.models.schemas import InvoiceExtract  # noqa: E402

NOTE_PATH = ROOT / "notes" / "validate_retry_result.md"


def main() -> None:
    print("=" * 52, "12.02 validate + retry")
    print("\n" + "=" * 52, "STEP 0 · Schema 字段")
    print("InvoiceExtract=", list(InvoiceExtract.model_fields.keys()))

    print("\n" + "=" * 52, "STEP 1 · 非法 amount 被拒")
    ok, detail = validate_invoice(dict(BAD_AMOUNT_PAYLOAD))
    print("ok=", ok, "error=", detail)
    assert ok is False

    print("\n" + "=" * 52, "STEP 2 · 重试后通过并写入桩")
    out = extract_with_retry(
        "demo",
        make_flaky_extractor(fail_times=1),
        max_retries=2,
    )
    print(json.dumps(out, ensure_ascii=False, indent=2, default=str))
    assert out["status"] == "ok" and out["wrote_db"] is True

    print("\n" + "=" * 52, "STEP 3 · 修不好 → need_human")
    human = extract_with_retry(
        "demo",
        make_flaky_extractor(always_bad=True),
        max_retries=2,
    )
    print(
        "status=",
        human["status"],
        "attempts=",
        human["attempts"],
        "wrote_db=",
        human["wrote_db"],
    )
    assert human["status"] == "need_human" and human["wrote_db"] is False

    print("\n" + "=" * 52, "STEP 4 · demo_suite")
    suite = demo_suite()
    assert suite["ok"], suite
    print("ASSERT: 拒收 + 重试通过 + need_human + 写库阻断 → PASS")

    NOTE_PATH.parent.mkdir(parents=True, exist_ok=True)
    NOTE_PATH.write_text(
        "\n".join(
            [
                "# 12.02 校验与失败重试 · 验收笔记",
                "",
                "## 非法样例",
                "```json",
                json.dumps(BAD_AMOUNT_PAYLOAD, ensure_ascii=False, indent=2),
                "```",
                f"error: `{suite['reject_error']}`",
                "",
                "## 重试修复",
                "```json",
                json.dumps(suite["repaired"], ensure_ascii=False, indent=2),
                "```",
                "",
                "## need_human",
                "```json",
                json.dumps(suite["need_human"], ensure_ascii=False, indent=2),
                "```",
                "",
                f"write_blocked_on_bad={suite['write_blocked_on_bad']}",
                "",
                "SUMMARY: validate_retry 验收通过",
                "",
            ]
        ),
        encoding="utf-8",
    )
    print("\nNOTE →", NOTE_PATH)
    print("SUMMARY: 12.02 验收通过")


if __name__ == "__main__":
    main()
