# app/lessons/m04_01_qa_chain.py
"""课次 04.01 · 拒答闸门（Grounding 的工程落地）。

本课在 03.06 的 Augment + Generate 前面加一道「硬分流」：
  检索为空 / top1 分数 < min_score → 直接返回拒答模板，根本不调 Chat。

为什么要代码短路，不能只靠 Prompt「不要编造」？
  模型越强，无据时越会「圆」；Prompt 是软约束，闸门是硬分支。

规则：不修改 m03_06_qa_chain.py，本文件只新增、向下 import。
"""

from __future__ import annotations

from app.lessons.m03_02_ingest import InMemoryIndex
from app.lessons.m03_03_splitters import Chunk
from app.lessons.m03_04_milvus_store import MilvusIndex
from app.lessons.m03_05_retriever import retrieve
from app.lessons.m03_06_qa_chain import build_augmented_prompt
from app.llm.client import call_chat

# 拒答话术要短、稳、可产品化——避免跟用户辩论或半真半假「编圆」
REFUSE_TEXT = (
    "根据当前知识库资料，我无法确定这一点。"
    "你可以换个问法，或补充文档后再问。"
    "我不会编造具体数字、条款或承诺。"
)

# 默认阈值：用演示脚本打印的分数分布再调；不是宇宙常数。
# 对本课 bge-small-zh + samples/docs：库内题 top1 常 ≥0.66，
# 「月球仓发货」这类半沾边离谱题约 0.56——故起点取 0.58（宁可略严）。
DEFAULT_MIN_SCORE = 0.58


def top1_score(hits: list[tuple[Chunk, float]]) -> float | None:
    """取出 top1 相似度；无命中时返回 None。"""
    if not hits:
        return None
    return hits[0][1]


def should_refuse(
    hits: list[tuple[Chunk, float]],
    *,
    min_score: float = DEFAULT_MIN_SCORE,
) -> bool:
    """判断要不要拒答（短路，不调模型）。

    触发条件（满足其一即拒）：
    1. hits 为空 —— 库里完全没有邻居
    2. top1.score < min_score —— 「最像的也不够像」
    """
    if not hits:
        return True
    score = hits[0][1]
    return score < min_score


def answer_with_gate(
    index: InMemoryIndex | MilvusIndex,
    question: str,
    *,
    top_k: int = 4,
    min_score: float = DEFAULT_MIN_SCORE,
    use_chat: bool = True,
    temperature: float = 0.1,
) -> dict:
    """带拒答闸门的 qa_chain：Retrieve → 闸门 →（通过才）Augment → Generate。

    参数:
        index: 内存或 Milvus 索引
        question: 用户问题
        top_k: 检索条数
        min_score: top1 最低分；越高越「惜答」（易误拒），越低越「滥答」（易幻觉）
        use_chat: False 时仍走闸门与 Augment，但不调 Chat（省费用看分流）
        temperature: 仅在真正 Generate 时生效

    返回:
        dict，多了 refused / reason / top1_score / min_score，方便演示脚本和笔记
    """
    hits = retrieve(index, question, top_k=top_k)
    score = top1_score(hits)

    if should_refuse(hits, min_score=min_score):
        if not hits:
            reason = "empty_hits"
        else:
            reason = f"top1_score={score:.4f} < min_score={min_score}"
        return {
            "question": question,
            "hits": hits,
            "prompt": "",
            "answer": REFUSE_TEXT,
            "refused": True,
            "reason": reason,
            "top1_score": score,
            "min_score": min_score,
        }

    # 只有通过闸门，才拼 Prompt、才花钱调模型
    prompt = build_augmented_prompt(question, hits)
    if use_chat:
        text = call_chat(
            [{"role": "user", "content": prompt}],
            temperature=temperature,
        )
    else:
        text = "(skipped: use_chat=False；已通过闸门，本会调用 Chat)"

    return {
        "question": question,
        "hits": hits,
        "prompt": prompt,
        "answer": text,
        "refused": False,
        "reason": "passed_gate",
        "top1_score": score,
        "min_score": min_score,
    }
