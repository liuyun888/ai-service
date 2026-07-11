# scripts/embed_vs_chat_demo.py
"""02.04 真实对比：Chat 冒充检索 vs Embedding 召回后再 Chat。

【你要看懂的一件事】
- 错误：把知识库全部段落塞进 Chat，让它「自己找相关的」→ 贵、慢、库一大就崩
- 正确：先用 Embedding 算相似度，只取 topK 段，再交给 Chat 生成回答

依赖：
- Embedding：app.models.embeddings（默认 local 真模型）
- Chat：app.llm.client.call_chat（需 .env 里 OPENAI_* 可用）
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

# 把 ai-service 根目录加入模块搜索路径，才能 import app.*
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from app.llm.client import call_chat, default_model  # noqa: E402
from app.models.embeddings import (  # noqa: E402
    cosine,
    default_embedding_model,
    embed_texts,
)

# ======================== 可调开关 ========================

# False：只跑 Embedding 召回与断言，不调对话（省费用 / 没 Key 也能验收召回）
# True ：PATH A / PATH B 都会真实调用 Chat
USE_CHAT = True

# PATH A 重复次数：同一问题多跑几轮，观察答案措辞是否漂移
CHAT_REPEATS = 2

# 用户问题（语义上接近 P1/P2 续航，远离 P4 食堂）
QUESTION = "降噪耳机电池能用多久？"

# 迷你知识库：故意把「相关续航」和「无关食堂」混在一起
PARAS = [
    "P1｜城际降噪 Pro：开启降噪后续航约 28 小时，蓝牙 5.2，参考价 999 元。",
    "P2｜轻听 Air：轻度降噪，续航约 18 小时，参考价 799 元。",
    "P3｜退换货：签收后 7 日内可无理由退货，耳机需配件齐全。",
    "P4｜食堂本周菜单：周一红烧肉，周二番茄牛腩，与耳机无关。",
    "P5｜保修：非人为损坏 12 个月质保，需提供购买凭证。",
]


def approx_chars(*parts: str) -> int:
    """粗算字符量，用来感受「塞全库」有多贵。

    注意：这不是精确 token 数（精确请用 tiktoken，见 02.05）。
    这里只做量级对比：全库字符 vs topK 字符。
    """
    return sum(len(p) for p in parts)


def path_chat_as_retriever(paras: list[str], question: str) -> str:
    """错误用法：把全部段落塞进 Chat，让模型兼职「搜索引擎」。

    5 段时也许还能答对；变成 200 段就会：贵、慢、易截断、不可复现。
    """
    joined = "\n".join(paras)
    prompt = (
        "下面有若干知识库段落。请只根据这些段落，回答用户问题；"
        "并在开头列出你认为相关的段落编号（如 P1,P2）。\n\n"
        f"段落：\n{joined}\n\n"
        f"用户问题：{question}\n"
    )
    # temperature 略高：更容易看到多轮之间的措辞漂移
    return call_chat([{"role": "user", "content": prompt}], temperature=0.7)


def path_embed_then_chat(
    paras: list[str], question: str, *, top_k: int = 2, use_chat: bool = True
) -> tuple[list[tuple[str, float]], str]:
    """正确用法：Embedding 取 topK →（可选）再 Chat 总结。

    步骤拆开讲：
    1. embed_texts([问题, 段1, 段2, ...]) 得到一组向量
    2. 用余弦相似度比较「问题向量」和「每段向量」
    3. 分数高的排前面，取前 top_k 段作为上下文
    4. 只把这几段 + 问题发给 Chat（检索与生成分工）

    :return: ([(段落, 分数), ...], 模型回答或仅召回说明)
    """
    vectors = embed_texts([question, *paras])
    q_vec = vectors[0]  # 问题向量
    p_vecs = vectors[1:]  # 各段落向量，与 paras 一一对应

    # 每段算一个相似度，再按分数从高到低排序
    ranked = sorted(
        ((paras[i], cosine(q_vec, p_vecs[i])) for i in range(len(paras))),
        key=lambda x: x[1],
        reverse=True,
    )
    top = ranked[:top_k]
    ctx = "\n".join(t for t, _ in top)  # 只拼接 topK 文本

    if not use_chat:
        return top, f"（未调 Chat）仅召回：\n{ctx}"

    prompt = (
        "仅根据下列检索到的片段回答用户问题，不要编造片段外信息。"
        "若片段不足以回答，请明确说不知道。\n\n"
        f"片段：\n{ctx}\n\n"
        f"用户问题：{question}\n"
    )
    # temperature 偏低：生成更稳，方便对照检索质量
    answer = call_chat([{"role": "user", "content": prompt}], temperature=0.2)
    return top, answer


def main() -> None:
    """先跑错误路径，再跑正确路径，最后断言 + 写笔记。"""
    use_chat = USE_CHAT
    print("=" * 40, "CONFIG")
    print("embedding:", default_embedding_model())
    print("chat_model:", default_model() if use_chat else "(skipped)")
    print("USE_CHAT:", use_chat)
    print("question:", QUESTION)
    print("paras:", len(PARAS))

    note: list[str] = [
        "# Embedding vs Chat 实跑对比\n\n",
        f"- 问题：{QUESTION}\n",
        f"- Embedding：`{default_embedding_model()}`\n",
        f"- Chat：`{default_model() if use_chat else 'skipped'}`\n",
        f"- 段落数：{len(PARAS)}\n\n",
    ]

    # ---------- 路径 A：Chat 冒充检索（塞全库）----------
    print("\n" + "=" * 40, "PATH A · Chat 冒充检索（塞全库）")
    chat_chars = approx_chars(QUESTION, *PARAS)
    print(f"粗算塞进 Prompt 的字符量 ≈ {chat_chars}（全库每次都付）")
    note.append("## PATH A · Chat 冒充检索\n\n")
    note.append(f"- 粗算 Prompt 字符量 ≈ **{chat_chars}**（每次塞全库）\n\n")

    if use_chat:
        for i in range(CHAT_REPEATS):
            t0 = time.perf_counter()
            ans = path_chat_as_retriever(PARAS, QUESTION)
            ms = (time.perf_counter() - t0) * 1000
            print(f"--- round {i + 1} ({ms:.0f} ms) ---")
            print(ans)
            note.append(f"### round {i + 1}（{ms:.0f} ms）\n\n{ans}\n\n")
    else:
        msg = "USE_CHAT=False，跳过 PATH A 的真实 Chat 调用。"
        print(msg)
        note.append(f"{msg}\n\n")

    # ---------- 路径 B：Embedding → top2 → Chat ----------
    print("\n" + "=" * 40, "PATH B · Embedding top2 再 Chat")
    t0 = time.perf_counter()
    top, ans_b = path_embed_then_chat(PARAS, QUESTION, top_k=2, use_chat=use_chat)
    ms = (time.perf_counter() - t0) * 1000
    print(f"耗时 {ms:.0f} ms")
    print("召回排序（相似度）：")
    for text, score in top:
        print(f"  {score:.4f}  {text}")
    print("ANSWER:\n", ans_b)

    # 只统计 topK 相关字符：应明显小于「塞全库」
    embed_chars = approx_chars(QUESTION, *(t for t, _ in top))
    print(f"交给 Chat 的片段字符量 ≈ {embed_chars}（只付 topK）")

    note.append("## PATH B · Embedding → top2 → Chat\n\n")
    note.append(f"- 耗时：{ms:.0f} ms\n")
    note.append(f"- 交给 Chat 的片段字符量 ≈ **{embed_chars}**\n\n")
    note.append("### 召回 top2\n\n")
    for text, score in top:
        note.append(f"- `{score:.4f}` {text}\n")
    note.append(f"\n### Answer\n\n{ans_b}\n\n")

    # ---------- 验收：续航段进 top2，食堂段不能进 ----------
    top_ids = " ".join(t for t, _ in top)
    assert "P1" in top_ids or "P2" in top_ids, "召回应包含续航相关段落"
    assert "P4" not in top_ids, "食堂无关段不应进 top2"
    print("\nASSERT: top2 含续航段、不含食堂段 → PASS")

    note.append("## 结论\n\n")
    note.append(
        "- PATH A：每次把全库塞进 Chat，字符多、贵、答案可能漂移。\n"
        "- PATH B：Embedding 先缩小到 topK，再 Chat；召回可复现，生成只看相关片段。\n"
        "- 选型：**检索用 Embedding，生成用 Chat**。\n"
    )

    out = ROOT / "notes" / "embed_vs_chat_result.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("".join(note), encoding="utf-8")
    print(f"\n记录已写入：{out}")


if __name__ == "__main__":
    main()
