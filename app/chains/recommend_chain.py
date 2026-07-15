# app/chains/recommend_chain.py
"""课次 05.04 · 推荐链：Prompt | Model | Str | Parser → RecommendResult。

与 hello_chain 同构，只是链尾从「纯文本」换成「结构化对象」。
"""

from __future__ import annotations

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable

from app.chains.parsers import (
    recommend_parser_runnable,
    run_recommend_with_retry,
    schema_hint_for_lc_template,
)
from app.models.schemas import RecommendResult

# 消息级模板：system 稳住「只输出 JSON」；human 带偏好
# 注意：Schema 说明里的花括号必须转义，否则 LC 会当成模板变量
RECOMMEND_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "你是推荐助手。只输出一个 JSON 对象，不要 Markdown 围栏，不要解释。\n"
            f"字段必须严格符合：\n{schema_hint_for_lc_template()}",
        ),
        ("human", "用户偏好：{pref}"),
    ]
)


def build_recommend_chain(model: Runnable) -> Runnable:
    """组装：模板 → 模型 → 抽字符串 → Pydantic Parser。"""
    return (
        RECOMMEND_PROMPT
        | model
        | StrOutputParser()
        | recommend_parser_runnable()
    )


def run_recommend(
    pref: str,
    *,
    use_chat: bool = True,
    with_retry: bool = True,
    temperature: float = 0.2,
) -> RecommendResult:
    """一键推荐；真模型默认带 1 次修复重试。

    use_chat=False 时不调网：返回一份合格造数据（便于离线验收 Parser）。
    """
    if not use_chat:
        from app.chains.parsers import parse_recommend

        # 离线：直接给出合格 JSON，证明 Parser / Schema 可独立跑
        mock = """{
          "items": [
            {"name": "城际降噪 Pro", "reason": "匹配通勤降噪与预算", "score": 0.88},
            {"name": "轻听 Air", "reason": "更便宜但降噪偏弱", "score": 0.62}
          ],
          "refuse": false,
          "message": ""
        }"""
        return parse_recommend(mock)

    from app.models.factory import get_chat_model
    from langchain_core.messages import HumanMessage, SystemMessage

    model = get_chat_model(temperature=temperature)

    if not with_retry:
        return build_recommend_chain(model).invoke({"pref": pref})

    def _invoke(user_prompt: str) -> str:
        # 重试轮用整段 user prompt（含错误信息）；system 仍压「只输出 JSON」
        msgs = [
            SystemMessage(
                content=(
                    "你是推荐助手。只输出一个 JSON 对象，不要 Markdown 围栏，不要解释。"
                )
            ),
            HumanMessage(content=user_prompt),
        ]
        ai = model.invoke(msgs)
        return str(getattr(ai, "content", ai))

    obj, _raws = run_recommend_with_retry(pref, invoke_llm=_invoke, max_attempts=2)
    return obj
