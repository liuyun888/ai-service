# app/chains/hello_chain.py
"""课次 05.01 · 最小 LCEL 链：Prompt | Model | Parser。

直觉：
- LangChain = 积木箱（模板、模型、解析器都有统一接口）
- Runnable = 每一块积木都能 invoke
- LCEL = 用 | 把积木接成水管，数据从左流到右

05.02 起：真模型统一走 app.models.factory.get_chat_model()；
本文件的 make_chat_model 仅作薄封装，方便旧演示脚本 import。
"""

from __future__ import annotations

from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable

# 系统规则：解释概念时不要编造具体业务数字（和专栏 Grounding 气质一致）
HELLO_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "你是技术老师。用不超过 3 句话解释主题，口语化、准确。"
            "不要编造具体业务数字、条款或未给出的事实。",
        ),
        ("human", "主题：{topic}"),
    ]
)


def make_chat_model(*, temperature: float = 0.2) -> BaseChatModel:
    """向后兼容入口：内部委托多模型工厂（读 DEFAULT_LLM）。

    新代码请直接：from app.models.factory import get_chat_model
    """
    from app.models.factory import get_chat_model

    return get_chat_model(temperature=temperature)


def make_offline_model() -> Runnable:
    """离线演示模型：不调网，根据主题返回固定说明（省费用、CI 可跑）。

    仍是 Runnable，所以能接到同一条 LCEL 水管上——这就是「积木可换」。
    """
    from langchain_core.messages import AIMessage, BaseMessage
    from langchain_core.runnables import RunnableLambda

    def _topic_from(messages: Any) -> str:
        # LCEL 里 Prompt 之后常见 ChatPromptValue，需先 to_messages()
        if hasattr(messages, "to_messages"):
            messages = messages.to_messages()
        if isinstance(messages, list):
            for m in reversed(messages):
                if isinstance(m, BaseMessage) and m.type == "human":
                    return str(m.content)
                if isinstance(m, dict) and m.get("role") in {"user", "human"}:
                    return str(m.get("content", ""))
        return str(messages)

    def _reply(messages: Any) -> AIMessage:
        raw = _topic_from(messages)
        # 模板里是「主题：xxx」
        topic = raw.split("主题：", 1)[-1].strip() if "主题：" in raw else raw.strip()
        if "退货" in topic or "时效" in topic:
            text = (
                f"「{topic or '退货时效'}」一般指买家签收后还能申请退货的期限。"
                "具体天数以商家公示政策为准，本演示不编造数字。"
                "超时通常只能走质量问题等特殊通道。"
            )
        else:
            text = (
                f"「{topic or 'RAG'}」在本专栏语境里指检索增强生成："
                "先从你管控的知识库检索相关片段，再让大模型按资料组织回答，减少瞎编。"
                "它解决的是「模型参数里没有你们私有最新文档」的问题。"
            )
        return AIMessage(content=text)

    return RunnableLambda(_reply)


def build_hello_chain(model: Runnable) -> Runnable:
    """组装最小链：填模板 → 调模型 → 抽成纯字符串。"""
    return HELLO_PROMPT | model | StrOutputParser()


def run_hello(
    topic: str,
    *,
    use_chat: bool = True,
    temperature: float = 0.2,
) -> str:
    """一键跑通：按开关选真模型或离线模型，再 invoke。"""
    model: Runnable = make_chat_model(temperature=temperature) if use_chat else make_offline_model()
    chain = build_hello_chain(model)
    return chain.invoke({"topic": topic})
