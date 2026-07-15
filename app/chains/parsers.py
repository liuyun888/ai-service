# app/chains/parsers.py
"""课次 05.04 · Output Parser：模型原文 → 结构化对象。

位置直觉：
  Prompt | Model | （Str 抽出文本）| Parser ← 你在这里
业务拿到的应是 Pydantic 对象，而不是「像 JSON 的一串字」。

本课两件事：
1. 严格路径：parse_recommend 失败就抛 ValidationError / JSONDecodeError
2. 温和路径：parse_with_retry / run_recommend_with_retry 把错误回喂再试
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from typing import TypeVar

from langchain_core.runnables import Runnable, RunnableLambda
from pydantic import BaseModel, ValidationError

from app.models.schemas import RecommendResult

# Markdown 代码围栏（三个反引号）；避免在注释/文档里直接写死导致炸版式
FENCE = "`" * 3

T = TypeVar("T", bound=BaseModel)


def strip_json_payload(text: str) -> str:
    """剥掉前后废话与 Markdown 围栏，尽量抽出 JSON 正文。

    模型常爱包一层 ```json ... ``` 或先说「好的如下：」——先洗干净再校验。
    """
    cleaned = text.strip()
    fence = re.search(
        rf"{re.escape(FENCE)}(?:json)?\s*([\s\S]*?){re.escape(FENCE)}",
        cleaned,
        re.IGNORECASE,
    )
    if fence:
        return fence.group(1).strip()
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start != -1 and end != -1 and end > start:
        return cleaned[start : end + 1]
    return cleaned


def parse_recommend(text: str) -> RecommendResult:
    """清洗 + Pydantic 校验 → RecommendResult。

    失败时抛出：
    - json.JSONDecodeError：根本不是合法 JSON
    - ValidationError：JSON 合法但字段/范围不合 Schema（如 score>1）
    """
    payload = strip_json_payload(text)
    return RecommendResult.model_validate_json(payload)


def parse_with_retry(
    raw: str,
    *,
    retry_raw: str | None = None,
    on_first_fail: Callable[[Exception], None] | None = None,
) -> RecommendResult:
    """先 parse；失败则用 retry_raw 再 parse（造数据 / 测试用）。

    真模型重试请用 run_recommend_with_retry（会把校验错误塞回 Prompt）。
    """
    try:
        return parse_recommend(raw)
    except (ValidationError, json.JSONDecodeError) as first_err:
        if on_first_fail:
            on_first_fail(first_err)
        if retry_raw is None:
            raise
        return parse_recommend(retry_raw)


def recommend_parser_runnable() -> Runnable:
    """可挂进 LCEL 的 Parser 节：str → RecommendResult。

    用法：prompt | model | StrOutputParser() | recommend_parser_runnable()
    """
    return RunnableLambda(parse_recommend)


def schema_hint_for_recommend() -> str:
    """给 Prompt 用的字段说明（避免手抄 Schema 对不齐）。"""
    return (
        '{\n'
        '  "items": [{"name": string, "reason": string, "score": number}],\n'
        '  "refuse": boolean,\n'
        '  "message": string\n'
        "}\n"
        "规则：score 必须是 0～1 的数字；信息不足时 items=[]、refuse=true、message 说明原因；最多 3 条 items。"
    )


def schema_hint_for_lc_template() -> str:
    """同上，但把 { } 转义成 {{ }}，才能放进 ChatPromptTemplate 当字面量。"""
    return schema_hint_for_recommend().replace("{", "{{").replace("}", "}}")


def build_recommend_user_prompt(pref: str, *, repair_error: str | None = None) -> str:
    """构造「只输出 JSON」的用户提示；repair_error 非空时进入修复轮。"""
    base = (
        "你是推荐助手。只输出一个 JSON 对象，不要 Markdown 围栏，不要解释。\n"
        f"字段必须严格符合：\n{schema_hint_for_recommend()}\n"
        f"用户偏好：{pref}\n"
    )
    if repair_error:
        return (
            f"{base}\n"
            f"你上次的输出无法通过校验，错误如下：\n{repair_error}\n"
            "请只输出修正后的完整 JSON 对象。"
        )
    return base


def run_recommend_with_retry(
    pref: str,
    *,
    invoke_llm: Callable[[str], str],
    max_attempts: int = 2,
) -> tuple[RecommendResult, list[str]]:
    """调模型拿原文 → 解析；失败则把错误回喂再试（最多 max_attempts 次）。

    参数：
        pref: 用户偏好文案
        invoke_llm: 传入完整 user prompt，返回模型原文
        max_attempts: 含首次，默认 2（即最多重试 1 次）

    返回：
        (结构化对象, 各轮原始文本列表) 便于写笔记对照
    """
    raws: list[str] = []
    last_err: Exception | None = None
    prompt = build_recommend_user_prompt(pref)

    for attempt in range(1, max_attempts + 1):
        raw = invoke_llm(prompt)
        raws.append(raw)
        try:
            return parse_recommend(raw), raws
        except (ValidationError, json.JSONDecodeError) as err:
            last_err = err
            if attempt >= max_attempts:
                break
            # 把校验错误塞回下一轮 Prompt
            prompt = build_recommend_user_prompt(pref, repair_error=str(err))

    assert last_err is not None
    raise last_err
