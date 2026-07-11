# scripts/context_window_demo.py
"""02.05 上下文窗口：整本（被截断）vs 只塞相关片段——真实计数 + 真实 Chat。

【你要看懂的一件事】
模型一次能「看见」的字数有上限，叫上下文窗口（用 token 计量）。
白皮书很长时，如果硬塞进去又超预算，系统常会从后面截断——
文末的关键政策就「消失」了，模型会诚实地说「文档里没有」。

正确做法：先把长文切成块，只把和问题相关的几块塞进窗口（RAG 的动机）。

演示路径：
- PATH A：假装整本塞入，但按小预算截断（丢掉文末）→ 常答「没有」
- PATH B：只塞含「退货时效」的片段 → 应能答出「7 日」
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import tiktoken  # OpenAI 系常用分词器；本课用它统一数 token

# ---------- 让本脚本能 import app.*（无论从哪启动）----------
# __file__ = .../ai-service/scripts/context_window_demo.py
# parents[1] = .../ai-service
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")  # 读 OPENAI_API_KEY 等，供 call_chat 使用

from app.llm.client import call_chat, default_model  # noqa: E402

# ======================== 可调开关（小白先改这里）========================

# False：只打印 token 预算、做截断断言，不花钱调 Chat
# True ：PATH A / PATH B 都真实调用对话模型
USE_CHAT = True

# 「文档侧」最多允许多少 token——故意设小，才能看到截断效果
# 调大 chapters 或调小这个数，都能更容易触发截断
DOC_BUDGET_TOKENS = 500

# 用户问题：专门问退货时效（答案埋在文末）
QUESTION = "请列出文档里关于『退货时效』的要点。若文中没有，请明确说没有。"

# 关键事实：故意放在文档最后。预算截断「保开头丢尾巴」时，这段会被切掉
TAIL_FACT = (
    "【第99章·售后政策】退货时效：签收后 7 日内可无理由退货，需配件齐全；"
    "超过 7 日仅支持质量问题换货。本条为验收关键句。"
)

# 填充段落：用来把文档撑得很长；不要写「退货」等词，以免关键词召回误伤
FILLER = (
    "【产品白皮书章节】本产品支持主动降噪与长续航，适用于通勤地铁场景。"
    "包装内含充电线与说明书。本节只介绍外观与接口，不涉及售后政策，仅作填充。"
)


def count_tokens(text: str, encoding_name: str = "cl100k_base") -> int:
    """统计文本有多少 token（窗口预算的「尺子」）。

    说明：不同厂商分词器略有差别；本课固定一种编码做对比即可，
    不必和线上 100% 一致，重点是建立「先数再塞」的习惯。
    """
    enc = tiktoken.get_encoding(encoding_name)
    # encode：把字符串变成 token id 列表；列表长度 ≈ token 数
    return len(enc.encode(text))


def build_long_document(*, chapters: int = 40) -> str:
    """拼出一份「假白皮书」：前面很多填充章，最后才是退货政策。

    :param chapters: 填充段数量，越大全文 token 越多，越容易超过预算
    """
    body = "\n".join(f"{FILLER}（填充段 {i + 1}/{chapters}）" for i in range(chapters))
    # 文末追加关键句——这是 PATH A 截断后会丢掉的部分
    return body + "\n\n" + TAIL_FACT


def truncate_to_budget(text: str, budget: int) -> tuple[str, bool]:
    """按 token 预算截断：保留开头、丢掉尾部。

    现实里供应商可能截开头、截中间或直接报错；
    本课用「保头丢尾」模拟一种常见静默伤害：文末政策没了，模型却仍自信作答。

    :param text: 原文
    :param budget: 最多保留多少 token
    :return: (截断后文本, 是否真的发生了截断)
    """
    enc = tiktoken.get_encoding("cl100k_base")
    ids = enc.encode(text)
    if len(ids) <= budget:
        return text, False  # 没超预算，原样返回
    # 只留前 budget 个 token，再 decode 回字符串 → 尾巴（含 TAIL_FACT）没了
    return enc.decode(ids[:budget]), True


def naive_chunks(text: str, size: int = 280) -> list[str]:
    """最简单的切块：按固定字数切开。

    本课只为演示「必须切」；生产里会用语义边界更好的 splitter（见 M03）。
    """
    return [
        text[i : i + size]
        for i in range(0, len(text), size)
        if text[i : i + size].strip()
    ]


def pick_relevant_chunks(chunks: list[str], question: str, *, top_k: int = 3) -> list[str]:
    """从所有块里挑出和问题最相关的几块，准备塞进窗口。

    策略（由稳到兜底）：
    1. 关键词：块里出现「退货时效」或「7 日」→ 优先保留
    2. 不够 top_k 时：用 Embedding 相似度补齐（02.03 / 02.04 那套）
    3. Embedding 不可用：只用关键词；再不行就取文末几块

    注意：关键词不要用太宽的「退货」——填充段若误写该词会脏召回。
    """
    keyed = [
        c
        for c in chunks
        if ("退货时效" in c) or ("7 日" in c) or ("7日" in c)
    ]
    if len(keyed) >= top_k:
        return keyed[:top_k]

    try:
        from app.models.embeddings import cosine, embed_texts

        # 一次向量化：第 0 条是问题，后面是各 chunk
        vectors = embed_texts([question, *chunks])
        q, rest = vectors[0], vectors[1:]
        # 按与问题的余弦相似度从高到低排序下标
        ranked = sorted(
            range(len(chunks)),
            key=lambda i: cosine(q, rest[i]),
            reverse=True,
        )
        picked: list[str] = list(keyed)  # 关键词命中的必须留下
        for i in ranked:
            if chunks[i] not in picked:
                picked.append(chunks[i])
            if len(picked) >= top_k:
                break
        return picked
    except Exception as e:  # noqa: BLE001 — 本地没装模型时仍能跑关键词路径
        print("Embedding 召回不可用，仅用关键词：", e)
        # 没有关键词命中时，取文末几块（政策往往在后面）
        return keyed[:top_k] or chunks[-top_k:]


def build_full_prompt(doc: str) -> str:
    """PATH A 用的 Prompt：把（可能已被截断的）「全文」塞给模型。"""
    return (
        "你是售后助手。仅根据下列文档回答，不要编造。"
        "若文档中没有相关信息，必须明确说没有。\n\n"
        f"文档：\n{doc}\n\n问题：{QUESTION}"
    )


def build_chunk_prompt(chunks: list[str]) -> str:
    """PATH B 用的 Prompt：只给相关片段，用 --- 分隔。"""
    joined = "\n---\n".join(chunks)
    return (
        "你是售后助手。仅根据下列片段回答，不要编造。"
        "若片段中没有相关信息，必须明确说没有。\n\n"
        f"片段：\n{joined}\n\n问题：{QUESTION}"
    )


def main() -> None:
    """主流程：造长文 → 数 token → 截断对比 →（可选）调 Chat → 写笔记。"""
    # 1) 造一份很长的文档，关键答案在最后
    doc = build_long_document(chapters=40)
    full_tokens = count_tokens(doc)

    # 2) 按小预算截断：模拟「窗口不够，尾巴被丢掉」
    truncated_doc, was_cut = truncate_to_budget(doc, DOC_BUDGET_TOKENS)
    trunc_tokens = count_tokens(truncated_doc)

    # 3) 切块并挑选与「退货时效」相关的片段
    chunks_all = naive_chunks(doc, size=280)
    chunks = pick_relevant_chunks(chunks_all, QUESTION, top_k=3)
    chunk_prompt = build_chunk_prompt(chunks)
    full_prompt_cut = build_full_prompt(truncated_doc)

    # ---------- 打印预算表（不调模型也能学到重点）----------
    print("=" * 40, "CONFIG")
    print("chat_model:", default_model() if USE_CHAT else "(skipped)")
    print("DOC_BUDGET_TOKENS:", DOC_BUDGET_TOKENS)
    print("USE_CHAT:", USE_CHAT)

    print("=" * 40, "BUDGET")
    print("full_doc chars:", len(doc), "tokens:", full_tokens)
    print(
        "after_truncate chars:",
        len(truncated_doc),
        "tokens:",
        trunc_tokens,
        "cut:",
        was_cut,
    )
    # 截断后文末政策还应在不在？期望 False
    print("tail_fact_in_truncated:", TAIL_FACT[:20] in truncated_doc)
    print("relevant_chunks:", len(chunks), "chars:", sum(len(c) for c in chunks))
    print("chunk_prompt tokens:", count_tokens(chunk_prompt))
    print("full_cut_prompt tokens:", count_tokens(full_prompt_cut))

    # ---------- 硬断言：保证演示条件成立 ----------
    assert was_cut, "请调大 chapters 或调小 DOC_BUDGET_TOKENS，确保发生截断"
    assert TAIL_FACT[:12] not in truncated_doc, "截断后仍含文末政策，演示失效"
    assert any("7 日" in c or "7日" in c for c in chunks), "相关片段应含退货时效"

    # 准备写入 notes 的 Markdown 片段
    note: list[str] = [
        "# 上下文窗口实跑记录\n\n",
        f"- 问题：{QUESTION}\n",
        f"- 全文 tokens：**{full_tokens}**；预算 DOC_BUDGET=**{DOC_BUDGET_TOKENS}**\n",
        f"- 截断后是否还含文末退货政策：**否**（tail_fact_in_truncated=False）\n",
        f"- 相关片段 tokens（整段 prompt）：**{count_tokens(chunk_prompt)}**\n\n",
    ]

    ans_a = ans_b = "(skipped)"
    if USE_CHAT:
        # ----- PATH A：截断后的「全文」→ 模型往往答「没有」-----
        print("\n" + "=" * 40, "PATH A · 整本塞入但被预算截断（丢文末）")
        t0 = time.perf_counter()
        try:
            ans_a = call_chat(
                [{"role": "user", "content": full_prompt_cut}],
                temperature=0.1,  # 偏低：减少胡编，便于对比
            )
            print(f"耗时 {(time.perf_counter() - t0) * 1000:.0f} ms")
            print("ANSWER A:\n", ans_a)
        except Exception as e:  # noqa: BLE001
            ans_a = f"[调用失败] {type(e).__name__}: {e}"
            print(ans_a)

        # ----- PATH B：只塞相关片段 → 应能答出 7 日 -----
        print("\n" + "=" * 40, "PATH B · 只塞相关片段")
        t0 = time.perf_counter()
        try:
            ans_b = call_chat(
                [{"role": "user", "content": chunk_prompt}],
                temperature=0.1,
            )
            print(f"耗时 {(time.perf_counter() - t0) * 1000:.0f} ms")
            print("ANSWER B:\n", ans_b)
        except Exception as e:  # noqa: BLE001
            ans_b = f"[调用失败] {type(e).__name__}: {e}"
            print(ans_b)

        # 验收：B 必须提到 7 日；A 通常没有（丢了文末）
        ok_b = ("7" in ans_b) and ("日" in ans_b) and ("没有" not in ans_b[:40])
        assert "7" in ans_b and "日" in ans_b, (
            f"PATH B 应答出退货 7 日，实际：{ans_b[:200]}"
        )
        print("\nASSERT: PATH B 含『7日』类要点 → PASS")
        if "7" not in ans_a:
            print("观察: PATH A 未复述 7 日（符合『截断丢文末』预期）")
        else:
            print(
                "观察: PATH A 仍提到 7——可能是模型猜测；"
                "对照 token 仍可见 PATH B 更省、更稳"
            )

        note.append("## PATH A（截断后的「全文」）\n\n")
        note.append(f"{ans_a}\n\n")
        note.append("## PATH B（相关片段）\n\n")
        note.append(f"{ans_b}\n\n")
        note.append(f"- PATH B 是否答出 7 日：{'是' if ok_b else '需人工核对'}\n")
    else:
        print("\nUSE_CHAT=False：跳过真实 Chat，仅完成预算/截断断言。")

    note.append("\n## 结论\n\n")
    note.append(
        "> 超长知识不能靠「整本塞进上下文」；预算不够会静默丢掉文末关键章。"
        "必须切分（并检索）后再读。\n"
    )

    # 4) 把本次实跑写入笔记，方便对照专栏验收清单
    out = ROOT / "notes" / "context_window_result.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("".join(note), encoding="utf-8")
    print(f"\n记录已写入：{out}")


if __name__ == "__main__":
    # 直接 python scripts/context_window_demo.py 时走这里
    main()
