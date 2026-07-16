# scripts/12_01_regex_llm_extract_demo.py
"""12.01 正则与 LLM 抽取演示。

【本课要感受的三件事】
1. Schema 先行：只产出 invoice_no/date/amount/seller_name
2. 强格式字段（发票号码）用正则钉死，可覆盖 LLM 幻觉
3. 离线也能跑；USE_CHAT=1 才走真模型

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

from app.chains.extract import (  # noqa: E402
    SAMPLE_INVOICE,
    build_extract_prompt,
    extract_invoice,
)
from app.lessons.m12_01_regex_llm_extract import demo_suite  # noqa: E402

NOTE_PATH = ROOT / "notes" / "regex_llm_extract_result.md"


def main() -> None:
    print("=" * 52, "12.01 regex + LLM extract")
    print("\n" + "=" * 52, "STEP 0 · 样例文本预览")
    print(SAMPLE_INVOICE[:180], "…")

    print("\n" + "=" * 52, "STEP 1 · Prompt 预览（含禁止编造）")
    prompt = build_extract_prompt(SAMPLE_INVOICE)
    assert "禁止编造" in prompt or "null" in prompt.lower()
    print(prompt[:280], "…")

    print("\n" + "=" * 52, "STEP 2 · 离线抽取（正则 + 模拟 LLM）")
    out = extract_invoice(SAMPLE_INVOICE, use_chat=False)
    print(json.dumps(out["fields"], ensure_ascii=False, indent=2))
    print("source=", out["source"], "regex_no=", out["regex_invoice_no"])

    print("\n" + "=" * 52, "STEP 3 · demo_suite 验收")
    suite = demo_suite()
    print("filled_keys=", suite["filled_keys"])
    print("llm_hallucinated_no=", suite["llm_hallucinated_no"], "→ merged=", suite["merged_no"])
    print("strategy=", json.dumps(suite["strategy"], ensure_ascii=False, indent=2))
    assert suite["ok"], suite
    print("ASSERT: ≥3 字段 + 正则覆盖幻觉号码 + 围栏可剥 → PASS")

    NOTE_PATH.parent.mkdir(parents=True, exist_ok=True)
    NOTE_PATH.write_text(
        "\n".join(
            [
                "# 12.01 正则与 LLM 抽取 · 验收笔记",
                "",
                "## 样例字段",
                "```json",
                json.dumps(suite["fields"], ensure_ascii=False, indent=2),
                "```",
                "",
                f"- regex 覆盖前 LLM 号码: `{suite['llm_hallucinated_no']}`",
                f"- 合并后号码: `{suite['merged_no']}`",
                f"- filled_keys: `{suite['filled_keys']}`",
                "",
                "## 字段策略",
                "```json",
                json.dumps(suite["strategy"], ensure_ascii=False, indent=2),
                "```",
                "",
                "SUMMARY: regex_llm_extract 验收通过",
                "",
            ]
        ),
        encoding="utf-8",
    )
    print("\nNOTE →", NOTE_PATH)
    print("SUMMARY: 12.01 验收通过")


if __name__ == "__main__":
    main()
