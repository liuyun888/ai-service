# app/lessons/m03_02_qa_chain.py
"""课次 03.02 · Augment + Generate（RAG 在线后两步）。

本文件为 03.02 课件原文，后续课次请勿修改。
"""

from __future__ import annotations

from app.llm.client import call_chat
from app.lessons.m03_02_ingest import InMemoryIndex
from app.lessons.m03_02_retriever import retrieve
from app.lessons.m03_02_splitters import Chunk


def augment(question: str, hits: list[tuple[Chunk, float]]) -> str:
    """把检索到的 chunk 拼成带约束的 Prompt（Augment 步）。"""
    if not hits:
        return (
            "你是客服助手。知识库未检索到任何片段。\n"
            f"问题：{question}\n"
            "请明确回答：资料中没有相关信息，无法作答。"
        )

    blocks: list[str] = []
    for chunk, score in hits:
        src = chunk.source or "unknown"
        blocks.append(
            f"[来源:{src} chunk_id={chunk.chunk_id} score={score:.4f}]\n{chunk.text}"
        )
    ctx = "\n---\n".join(blocks)

    return (
        "你是客服助手。\n"
        "规则：\n"
        "1. 只根据下列「检索片段」回答，禁止编造片段中没有的事实。\n"
        "2. 若片段不足以回答，必须明确说「资料中没有相关信息」。\n"
        "3. 回答时尽量引用片段中的关键数字或条款。\n\n"
        f"检索片段：\n{ctx}\n\n"
        f"问题：{question}\n"
    )


def generate(prompt: str, *, temperature: float = 0.1) -> str:
    """Generate 步：把 Augment 后的 Prompt 交给 Chat 模型。"""
    return call_chat([{"role": "user", "content": prompt}], temperature=temperature)


def run_rag(
    index: InMemoryIndex,
    question: str,
    *,
    top_k: int = 2,
    use_chat: bool = True,
) -> dict:
    """在线三步一条龙：Retrieve → Augment → Generate。"""
    hits = retrieve(index, question, top_k=top_k)
    prompt = augment(question, hits)
    answer = generate(prompt) if use_chat else "(skipped: use_chat=False)"

    return {
        "question": question,
        "hits": hits,
        "prompt": prompt,
        "answer": answer,
    }
