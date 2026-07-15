# app/lessons/m03_06_qa_chain.py
"""课次 03.06 · 上下文注入（Augment）+ 带引用的问答链。

本课在 03.02 的「把片段塞进 Prompt」基础上做三件教学向的升级：
1. 资料统一编号成 [1][2]…，方便模型写「根据[1]…」
2. 每条资料带上 source=文件名，方便文末列引用
3. 用 03.05 的统一 retrieve（可接内存或 Milvus），不改旧课文件

直觉：检索 = 找书签；Augment = 把书签贴进考卷；Generate = 只许照着考卷答题。
"""

from __future__ import annotations

from app.lessons.m03_02_ingest import InMemoryIndex
from app.lessons.m03_03_splitters import Chunk
from app.lessons.m03_04_milvus_store import MilvusIndex
from app.lessons.m03_05_retriever import retrieve
from app.llm.client import call_chat


def build_augmented_prompt(
    question: str,
    hits: list[tuple[Chunk, float]],
) -> str:
    """把检索片段拼成带约束、可引用的 Prompt。

    参数:
        question: 用户问题
        hits: retrieve 返回的 (Chunk, score) 列表；空列表时写「无检索结果」

    返回:
        可直接交给 Chat 的完整 Prompt 字符串
    """
    if not hits:
        body = "（无检索结果）"
    else:
        lines: list[str] = []
        for i, (chunk, _score) in enumerate(hits, start=1):
            # source 为空时用 unknown，避免模型瞎编文件名
            src = chunk.source or "unknown"
            lines.append(f"[{i}] (source={src}) {chunk.text}")
        body = "\n".join(lines)

    return (
        "你只能根据【资料】回答。\n"
        "资料不足时说「根据现有资料无法确定」，不要编造。\n"
        "回答末尾列出引用的 source（文件名即可）。\n\n"
        f"【资料】\n{body}\n\n"
        f"【问题】\n{question}"
    )


def answer(
    index: InMemoryIndex | MilvusIndex,
    question: str,
    *,
    top_k: int = 4,
    use_chat: bool = True,
    temperature: float = 0.1,
) -> dict:
    """最小 qa_chain：Retrieve → Augment → Generate。

    参数:
        index: 03.05 兼容的索引（内存或 Milvus）
        question: 用户问题
        top_k: 注入 Prompt 的片段数；越大越全也越吵（可对照 03.05）
        use_chat: False 时只拼 Prompt、不调模型（省费用/离线验收 Augment）
        temperature: Chat 温度；答事实题宜偏低

    返回:
        dict，含 question / hits / prompt / answer 四个字段，方便演示脚本打印
    """
    hits = retrieve(index, question, top_k=top_k)
    prompt = build_augmented_prompt(question, hits)
    if use_chat:
        text = call_chat(
            [{"role": "user", "content": prompt}],
            temperature=temperature,
        )
    else:
        text = "(skipped: use_chat=False)"

    return {
        "question": question,
        "hits": hits,
        "prompt": prompt,
        "answer": text,
    }


def hit_sources(hits: list[tuple[Chunk, float]]) -> list[str]:
    """从 hits 里抽出 source 列表（去空），供召回评测「topK 是否命中期望文件」。"""
    out: list[str] = []
    for chunk, _ in hits:
        if chunk.source:
            out.append(chunk.source)
    return out


def recall_hit(hits: list[tuple[Chunk, float]], expected_source: str) -> bool:
    """简化版召回@K：期望文件名是否出现在本次 topK 的任一 source 中。"""
    return expected_source in hit_sources(hits)
