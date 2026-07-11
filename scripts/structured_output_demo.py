"""结构化输出：造数据练校验；可选再接真实大模型。"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.models.schemas import RecommendResult

# —— 开关：False=只跑造数据；True=再调一次真实模型（需 .env）——
USE_REAL_LLM = False

USER_PREF = "预算 1000 内，通勤地铁降噪，续航尽量长"

# 三个反引号；不要在源码里直接写死围栏，以免嵌进 Markdown 时炸版式
FENCE = "`" * 3


# ---------- 造数据：假装这是模型返回的字符串 ----------
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

# 假装「重试后」模型改对了（生产里是把 ValidationError 回喂再调一次）
MOCK_RETRY_FIXED = """{
  "items": [
    {"name": "城际降噪 Pro", "reason": "匹配通勤降噪与预算", "score": 0.85}
  ],
  "refuse": false,
  "message": ""
}"""


def strip_json_payload(text: str) -> str:
    """剥掉前后废话与 Markdown 代码围栏，抽出 JSON 正文。"""
    cleaned = text.strip()
    # 匹配围栏包裹的 JSON（FENCE 即三个反引号）
    fence = re.search(
        rf"{re.escape(FENCE)}(?:json)?\s*([\s\S]*?){re.escape(FENCE)}",
        cleaned,
        re.IGNORECASE,
    )
    if fence:
        return fence.group(1).strip()
    # 没有围栏时，尝试截取第一个 { 到最后一个 }
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start != -1 and end != -1 and end > start:
        return cleaned[start : end + 1]
    return cleaned


def parse_recommend(text: str) -> RecommendResult:
    """清洗后用 Pydantic 校验；失败抛 ValidationError。"""
    payload = strip_json_payload(text)
    return RecommendResult.model_validate_json(payload)


def parse_with_retry(raw: str, retry_raw: str | None = None) -> RecommendResult:
    """先解析；失败则用 retry_raw（造数据）或真实二次生成。"""
    try:
        return parse_recommend(raw)
    except (ValidationError, json.JSONDecodeError) as first_err:
        print("首次校验失败：", first_err)
        if retry_raw is None:
            raise
        print("使用重试结果再校验…")
        return parse_recommend(retry_raw)


def demo_mock() -> None:
    """不调模型：三份造数据走通成功 / 剥围栏 / 失败重试。"""
    cases = [
        ("合格 JSON", MOCK_OK, None),
        ("带围栏+废话", MOCK_WITH_FENCE, None),
        ("score 超界 → 重试", MOCK_BAD, MOCK_RETRY_FIXED),
    ]
    lines: list[str] = ["# 结构化输出造数据演示\n"]
    for title, raw, retry in cases:
        print("=" * 40, title)
        print("RAW:\n", raw[:200], "..." if len(raw) > 200 else "")
        result = parse_with_retry(raw, retry_raw=retry)
        print("PARSED:", result.model_dump())
        body = result.model_dump_json(indent=2)
        lines.append(f"## {title}\n\n{FENCE}json\n{body}\n{FENCE}\n")

    out = ROOT / "notes" / "structured_output_mock.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"\n造数据结果已写入：{out}")


def build_recommend_prompt(pref: str) -> str:
    """真实调用时用的 Prompt：字段名与 Schema 对齐。"""
    return f"""你是推荐助手。只输出一个 JSON 对象，不要 Markdown，不要解释。
字段必须严格符合：
{{
  "items": [{{"name": string, "reason": string, "score": number}}],
  "refuse": boolean,
  "message": string
}}
规则：
- score 必须是 0～1 的数字（不要字符串）
- 若信息不足无法推荐：items 为空数组，refuse=true，message 说明原因
- 最多 3 条 items

用户偏好：{pref}
"""


def demo_real_llm() -> None:
    """可选：接真实模型；失败则把校验错误塞进 Prompt 再试一次。"""
    from app.llm.client import call_chat

    prompt = build_recommend_prompt(USER_PREF)
    raw1 = call_chat([{"role": "user", "content": prompt}], temperature=0.2)
    print("=" * 40, "real_llm 首次")
    print(raw1)
    try:
        result = parse_recommend(raw1)
    except (ValidationError, json.JSONDecodeError) as err:
        retry_prompt = (
            f"{prompt}\n\n你上次的输出无法通过校验，错误如下：\n{err}\n"
            "请只输出修正后的完整 JSON。"
        )
        raw2 = call_chat([{"role": "user", "content": retry_prompt}], temperature=0.1)
        print("=" * 40, "real_llm 重试")
        print(raw2)
        result = parse_recommend(raw2)

    out = ROOT / "notes" / "structured_output_llm.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    body = result.model_dump_json(indent=2)
    out.write_text(
        f"## 用户偏好\n\n{USER_PREF}\n\n## 结果\n\n{FENCE}json\n{body}\n{FENCE}\n",
        encoding="utf-8",
    )
    print("PARSED:", result.model_dump())
    print(f"已写入：{out}")


def main() -> None:
    demo_mock()
    if USE_REAL_LLM:
        demo_real_llm()
    else:
        print("\n提示：造数据已跑通。若要接真模型，把 USE_REAL_LLM = True 后重跑。")


if __name__ == "__main__":
    main()