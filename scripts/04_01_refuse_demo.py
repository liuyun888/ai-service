# scripts/04_01_refuse_demo.py
"""04.01 拒答与 Grounding 演示：闸门短路 + 阈值调参实验。

【本课要感受的三件事】
1. 库内问题：top1 够高 → 通过闸门 → 正常答（并可点 source）
2. 库外问题：top1 偏低 → 直接拒答模板，不调 Chat 编故事
3. min_score 调很高会误拒；调很低会把无关题放进 Generate（危险）

默认内存索引 + samples/docs（与 03.05/03.06 同一套样例库）。
"""

from __future__ import annotations

import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from app.lessons.m02_03_embeddings import default_embedding_model  # noqa: E402
from app.lessons.m03_05_ingest_batch import chunks_from_markdown_dir  # noqa: E402
from app.lessons.m03_05_retriever import build_index, format_hit, retrieve  # noqa: E402
from app.lessons.m04_01_qa_chain import (  # noqa: E402
    DEFAULT_MIN_SCORE,
    REFUSE_TEXT,
    answer_with_gate,
)
from app.llm.client import default_model  # noqa: E402

# ======================== 可调开关 ========================

# False：仍测闸门分流，但不调 Chat（省费用；应答题只看到「已通过闸门」）
USE_CHAT = True

TOP_K = 4
# 本机 bge-small-zh + samples/docs 实测参考：
#   库内退货/发货 ≈ 0.77～0.81；食堂菜单 ≈ 0.66；月球仓半沾边 ≈ 0.56；股票收益 ≈ 0.41
# 默认 0.58：拒掉月球仓，放行库内题。务必以 STEP 1 打印分数再改。
MIN_SCORE = float(os.getenv("MIN_SCORE", str(DEFAULT_MIN_SCORE)))

SAMPLE_DIR = ROOT / "samples" / "docs"
NOTE_PATH = ROOT / "notes" / "refuse_grounding_result.md"


@dataclass
class Probe:
    """一道探针：期望拒答或期望应答。"""

    name: str
    question: str
    expect_refuse: bool
    note: str


# 三类实验题（与专栏示例对齐）
PROBES: list[Probe] = [
    Probe(
        name="A·库内必有",
        question="七天无理由退货需要什么条件？",
        expect_refuse=False,
        note="应正常答，并落到 return_policy.md",
    ),
    Probe(
        name="B·库外离谱",
        question="你们支持月球仓发货吗？保证 10 分钟送达月亮表面吗？",
        expect_refuse=True,
        note="库中无此政策；语义会漂到 shipping_faq，分数中等偏低 → 应拒",
    ),
    Probe(
        name="C·库内菜单",
        question="食堂周三午餐有什么菜？",
        expect_refuse=False,
        note="库内有 cafeteria_menu，分数带作对照（不应被闸门误杀）",
    ),
    Probe(
        name="D·完全无关",
        question="公司股票明年能涨多少？请给出确定收益率。",
        expect_refuse=True,
        note="更低分对照题；比「月球仓」更干净地落在阈值下方",
    ),
]


def _print_hits(hits: list, *, top_n: int = 3) -> None:
    for i, (chunk, score) in enumerate(hits[:top_n], start=1):
        print(f"  #{i}  {format_hit(chunk, score)}")


def main() -> None:
    global USE_CHAT
    env_flag = os.getenv("USE_CHAT")
    if env_flag is not None:
        USE_CHAT = env_flag.strip().lower() in {"1", "true", "yes", "on"}

    if not SAMPLE_DIR.is_dir():
        raise FileNotFoundError(f"请先准备样例目录：{SAMPLE_DIR}")

    print("=" * 52, "CONFIG")
    print("sample_dir:", SAMPLE_DIR)
    print("embedding:", default_embedding_model())
    print("chat_model:", default_model() if USE_CHAT else "(skipped)")
    print("USE_CHAT:", USE_CHAT)
    print("top_k:", TOP_K)
    print("min_score:", MIN_SCORE)

    # ---- Index ----
    print("\n" + "=" * 52, "STEP 0 · Index")
    t0 = time.perf_counter()
    chunks = chunks_from_markdown_dir(SAMPLE_DIR)
    index = build_index(chunks)
    print(f"总块数: {len(index.items)}  耗时: {(time.perf_counter() - t0) * 1000:.0f} ms")

    # ---- 先看分数分布（调阈值的依据）----
    print("\n" + "=" * 52, "STEP 1 · 分数探针（调 min_score 用）")
    score_rows: list[str] = []
    for probe in PROBES:
        hits = retrieve(index, probe.question, top_k=TOP_K)
        top1 = hits[0][1] if hits else 0.0
        print(f"\n[{probe.name}] {probe.question}")
        print(f"  top1_score={top1:.4f}  ({probe.note})")
        _print_hits(hits)
        score_rows.append(f"| {probe.name} | {top1:.4f} | {probe.note} |")

    # ---- 默认阈值下：应答 / 应拒 ----
    print("\n" + "=" * 52, f"STEP 2 · 闸门实验（min_score={MIN_SCORE}）")
    results: list[dict] = []
    all_ok = True
    # A 应答、B/D 拒答是硬验收；C 只做分数对照（会进 Chat 可省）
    hard_probes = [PROBES[0], PROBES[1], PROBES[3]]
    for probe in hard_probes:
        print(f"\n--- {probe.name} ---")
        print("Q:", probe.question)
        # 拒答题不必调 Chat；应答题才按 USE_CHAT
        call_chat = USE_CHAT and (not probe.expect_refuse)
        t1 = time.perf_counter()
        out = answer_with_gate(
            index,
            probe.question,
            top_k=TOP_K,
            min_score=MIN_SCORE,
            use_chat=call_chat,
        )
        ms = (time.perf_counter() - t1) * 1000
        results.append(out)

        print(f"top1_score: {out['top1_score']}")
        print(f"refused: {out['refused']}  reason: {out['reason']}")
        print(f"answer: {out['answer'][:220]}{'…' if len(out['answer']) > 220 else ''}")
        print(f"耗时: {ms:.0f} ms")

        ok = out["refused"] == probe.expect_refuse
        if not probe.expect_refuse and USE_CHAT:
            ok = ok and out["answer"] != REFUSE_TEXT
        if probe.expect_refuse:
            ok = ok and out["answer"] == REFUSE_TEXT
        print("ASSERT:", "PASS" if ok else "FAIL", f"（期望 refused={probe.expect_refuse}）")
        if not ok:
            all_ok = False
    # ---- 阈值极端：误拒 / 滥放 ----
    print("\n" + "=" * 52, "STEP 3 · 阈值极端对比")
    q_good = PROBES[0].question
    q_bad = PROBES[1].question

    high = 0.95
    low = 0.20
    r_high = answer_with_gate(
        index, q_good, top_k=TOP_K, min_score=high, use_chat=False
    )
    r_low = answer_with_gate(
        index, q_bad, top_k=TOP_K, min_score=low, use_chat=False
    )
    print(f"\n好问 + min_score={high} → refused={r_high['refused']}  "
          f"(top1={r_high['top1_score']:.4f})  ← 易误拒")
    print(f"坏问 + min_score={low}  → refused={r_low['refused']}  "
          f"(top1={r_low['top1_score']:.4f})  ← 易把离谱题放进 Generate")

    assert r_high["refused"] is True, "阈值过高时应误拒库内题（演示用）"
    assert r_low["refused"] is False, "阈值过低时应放行库外题（演示危险）"
    print("ASSERT: 极端阈值行为符合预期 → PASS")

    # ---- 无闸门对比（库外题调 Chat：演示「就算模型偶尔老实，仍浪费费用并可乱引用」）----
    print("\n" + "=" * 52, "STEP 4 · 对比：无闸门会怎样？")
    if USE_CHAT:
        from app.lessons.m03_06_qa_chain import answer as answer_no_gate

        bare = answer_no_gate(index, q_bad, top_k=TOP_K, use_chat=True)
        gated = answer_with_gate(
            index, q_bad, top_k=TOP_K, min_score=MIN_SCORE, use_chat=True
        )
        print("\n[无闸门] 月球仓题 → 仍会调 Chat（可能拒得含糊或乱点 source）：")
        print(bare["answer"][:320])
        print("\n[有闸门] 同题 → 固定拒答模板，reason 含 top1_score：")
        print(gated["answer"][:320])
        print("reason:", gated["reason"])
        print(
            "ASSERT: 有闸门 refused=True 且答案为 REFUSE_TEXT →",
            "PASS" if gated["refused"] and gated["answer"] == REFUSE_TEXT else "FAIL",
        )
        if not (gated["refused"] and gated["answer"] == REFUSE_TEXT):
            all_ok = False
    else:
        print("USE_CHAT=False：跳过无闸门真实生成对比（设 USE_CHAT=1 可看）")

    # ---- 写笔记 ----
    NOTE_PATH.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# 04.01 拒答与 Grounding · 实跑记录\n",
        f"- Embedding：`{default_embedding_model()}`",
        f"- Chat：`{default_model() if USE_CHAT else 'skipped'}`",
        f"- **选用 min_score：{MIN_SCORE}**",
        f"- top_k：{TOP_K}",
        "",
        "## 分数探针",
        "",
        "| 探针 | top1 | 说明 |",
        "|------|------|------|",
        *score_rows,
        "",
        "## 闸门结果",
        "",
    ]
    for out in results:
        lines.append(f"### {out['question']}\n")
        lines.append(f"- refused: `{out['refused']}`")
        lines.append(f"- reason: `{out['reason']}`")
        lines.append(f"- top1_score: `{out['top1_score']}`")
        lines.append(f"- answer: {out['answer'][:400]}")
        lines.append("")
    lines.extend(
        [
            "## 阈值极端",
            "",
            f"- 好问 + min_score={high} → refused=`{r_high['refused']}`（误拒演示）",
            f"- 坏问 + min_score={low} → refused=`{r_low['refused']}`（滥放演示）",
            "",
            "## 结论（自己填）",
            "",
            f"- 我最终选用的 min_score：`{MIN_SCORE}`",
            "- 依据：比「库内题 top1」低一截，比「库外离谱题 top1」高一截。",
            "",
        ]
    )
    NOTE_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"\n笔记已写入: {NOTE_PATH}")
    print("\nSUMMARY:", "全部硬验收 PASS" if all_ok else "有 FAIL，请看 ASSERT 行")


if __name__ == "__main__":
    main()
