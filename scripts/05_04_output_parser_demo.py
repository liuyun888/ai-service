# scripts/05_04_output_parser_demo.py
"""05.04 Output Parser 演示。

【本课要感受的三件事】
1. Parser 在链尾：原文 → RecommendResult，不合格就显式失败
2. 造数据可单独验收 Parser（不花 Chat 费）
3. 真模型失败时可把 ValidationError 回喂再试 1 次

工作目录：必须在 ai-service/ 下执行。
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from app.chains.parsers import (  # noqa: E402
    FENCE,
    parse_recommend,
    parse_with_retry,
    recommend_parser_runnable,
)
from app.chains.recommend_chain import (  # noqa: E402
    build_recommend_chain,
    run_recommend,
)
from app.models.factory import describe_provider, get_chat_model  # noqa: E402
from app.models.schemas import RecommendResult  # noqa: E402

# ======================== 可调开关 ========================

USE_CHAT = os.getenv("USE_CHAT", "0").strip().lower() in {"1", "true", "yes", "on"}
USER_PREF = os.getenv(
    "RECOMMEND_PREF",
    "预算 1000 内，通勤地铁降噪，续航尽量长",
)
NOTE_PATH = ROOT / "notes" / "output_parser_result.md"

MOCK_OK = """{
  "items": [
    {"name": "城际降噪 Pro", "reason": "降噪标注通勤级且在预算内", "score": 0.88},
    {"name": "轻听 Air", "reason": "更便宜但降噪偏弱", "score": 0.62}
  ],
  "refuse": false,
  "message": ""
}"""

MOCK_WITH_FENCE = (
    "好的，如下：\n"
    f"{FENCE}json\n"
    "{\n"
    '  "items": [\n'
    '    {"name": "城际降噪 Pro", "reason": "续航更长更适合通勤", "score": 0.9}\n'
    "  ],\n"
    '  "refuse": false,\n'
    '  "message": ""\n'
    "}\n"
    f"{FENCE}\n"
)

MOCK_BAD = """{
  "items": [
    {"name": "神秘耳机", "reason": "超值", "score": 1.5}
  ],
  "refuse": false,
  "message": ""
}"""

MOCK_RETRY_FIXED = """{
  "items": [
    {"name": "城际降噪 Pro", "reason": "匹配通勤降噪与预算", "score": 0.85}
  ],
  "refuse": false,
  "message": ""
}"""


def main() -> None:
    print("=" * 52, "CONFIG")
    print("USE_CHAT:", USE_CHAT)
    print("pref:", USER_PREF)
    print("provider:", describe_provider())
    print("cwd 提示: 应在 ai-service；本脚本 ROOT =", ROOT)

    note: list[str] = [
        "# 05.04 Output Parser · 实跑记录\n",
        f"- USE_CHAT: `{USE_CHAT}`",
        f"- pref: {USER_PREF}",
        f"- provider: `{describe_provider().get('provider')}`",
        "",
    ]

    # ---- STEP 1 · Parser 单独跑：成功 / 剥围栏 ----
    print("\n" + "=" * 52, "STEP 1 · 造数据成功解析")
    ok = parse_recommend(MOCK_OK)
    assert isinstance(ok, RecommendResult)
    assert len(ok.items) == 2
    print("PARSED:", ok.model_dump())
    fenced = parse_recommend(MOCK_WITH_FENCE)
    assert fenced.items[0].score <= 1
    print("FENCED PARSED:", fenced.model_dump())
    print("ASSERT: 合格 JSON + 围栏清洗 → PASS")
    note.append("## STEP 1 · 成功\n")
    note.append(f"```json\n{ok.model_dump_json(indent=2)}\n```\n")

    # ---- STEP 2 · 失败路径可见 ----
    print("\n" + "=" * 52, "STEP 2 · score 超界应报 ValidationError")
    try:
        parse_recommend(MOCK_BAD)
        raise AssertionError("score=1.5 应失败")
    except ValidationError as exc:
        print("caught:", str(exc)[:240])
        print("ASSERT: 失败路径可见 → PASS")
        note.append("## STEP 2 · 失败可见\n")
        note.append(f"```text\n{exc}\n```\n")

    # ---- STEP 3 · 失败后用重试原文修好 ----
    print("\n" + "=" * 52, "STEP 3 · 失败 → 重试造数据")
    logs: list[str] = []

    def _log(err: Exception) -> None:
        msg = f"首次校验失败：{err}"
        print(msg[:240])
        logs.append(msg)

    fixed = parse_with_retry(
        MOCK_BAD,
        retry_raw=MOCK_RETRY_FIXED,
        on_first_fail=_log,
    )
    assert fixed.items[0].score <= 1
    print("RETRY PARSED:", fixed.model_dump())
    print("ASSERT: 重试后通过 → PASS")
    note.append("## STEP 3 · 重试\n")
    note.append(f"```json\n{fixed.model_dump_json(indent=2)}\n```\n")

    # ---- STEP 4 · LCEL 挂上 Parser 节 ----
    print("\n" + "=" * 52, "STEP 4 · LCEL：Str → recommend_parser_runnable")
    obj = recommend_parser_runnable().invoke(MOCK_OK)
    assert obj.items
    print("runnable:", type(obj).__name__, obj.model_dump())
    print("ASSERT: Parser 可作 Runnable → PASS")
    note.append("## STEP 4 · Runnable Parser\n")
    note.append(f"- type: `{type(obj).__name__}`\n")

    # ---- STEP 5 · 真模型或离线一键 ----
    print("\n" + "=" * 52, "STEP 5 · run_recommend")
    if USE_CHAT:
        result = run_recommend(USER_PREF, use_chat=True, with_retry=True)
        print("LLM PARSED:", result.model_dump())
        assert isinstance(result, RecommendResult)
        # 再测：无重试整链（可能偶发失败，允许捕获）
        try:
            chain = build_recommend_chain(get_chat_model(temperature=0.1))
            once = chain.invoke({"pref": USER_PREF})
            print("chain once:", once.model_dump())
        except (ValidationError, json.JSONDecodeError) as err:
            print("chain once failed (expected sometimes):", str(err)[:200])
        note.append("## STEP 5 · 真模型\n")
        note.append(f"```json\n{result.model_dump_json(indent=2)}\n```\n")
    else:
        result = run_recommend(USER_PREF, use_chat=False)
        print("OFFLINE PARSED:", result.model_dump())
        note.append("## STEP 5 · 离线 run_recommend\n")
        note.append(f"```json\n{result.model_dump_json(indent=2)}\n```\n")
    print("ASSERT: run_recommend → RecommendResult → PASS")

    note.append("## 结论\n")
    note.append("- Parser 在模型之后、业务之前；失败要可见，不要静默 None。")
    note.append("- 造数据可单独验收 Schema；真模型用校验错误回喂修复。")
    note.append("- LCEL：`prompt | model | StrOutputParser | pydantic_parser`。")
    note.append("")

    NOTE_PATH.parent.mkdir(parents=True, exist_ok=True)
    NOTE_PATH.write_text("\n".join(note), encoding="utf-8")
    print(f"\n笔记已写入: {NOTE_PATH}")
    print("SUMMARY: output_parser 验收通过")


if __name__ == "__main__":
    main()
