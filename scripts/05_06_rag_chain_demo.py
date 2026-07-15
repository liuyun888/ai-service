# scripts/05_06_rag_chain_demo.py
"""05.06 RAG Chain 组装演示。

【本课要感受的三件事】
1. 一条链 invoke({"question": ...}) 完成检索→闸门→生成
2. 库内题有据作答且能指向 source；离谱题拒答且不调模型（离线也能验闸门）
3. 零件可换（Retriever / 模型），链骨架不变

工作目录：必须在 ai-service/ 下。
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from app.chains.rag_chain import (  # noqa: E402
    build_rag_chain,
    format_docs,
    run_rag_chain,
)
from app.chains.knowledge_retriever import KnowledgeRetriever  # noqa: E402
from app.lessons.m02_03_embeddings import default_embedding_model  # noqa: E402
from app.lessons.m03_02_ingest import build_index  # noqa: E402
from app.lessons.m03_05_ingest_batch import chunks_from_markdown_dir  # noqa: E402
from app.lessons.m04_01_qa_chain import DEFAULT_MIN_SCORE, REFUSE_TEXT  # noqa: E402
from app.models.factory import describe_provider, get_chat_model  # noqa: E402

# ======================== 可调开关 ========================

USE_CHAT = os.getenv("USE_CHAT", "0").strip().lower() in {"1", "true", "yes", "on"}
TOP_K = int(os.getenv("TOP_K", "4"))
MIN_SCORE = float(os.getenv("MIN_SCORE", str(DEFAULT_MIN_SCORE)))
SAMPLE_DIR = ROOT / "samples" / "docs"
NOTE_PATH = ROOT / "notes" / "rag_chain_result.md"

# 库内应答题 / 离谱拒答题（与 04.01 演示同气质）
Q_OK = os.getenv("RAG_Q_OK", "七天无理由退货需要什么条件？")
Q_BAD = os.getenv("RAG_Q_BAD", "你们支持月球仓发货吗？")


def main() -> None:
    print("=" * 52, "CONFIG")
    print("USE_CHAT:", USE_CHAT)
    print("embedding:", default_embedding_model())
    print("provider:", describe_provider())
    print("top_k:", TOP_K, "min_score:", MIN_SCORE)
    print("sample_dir:", SAMPLE_DIR)
    print("cwd 提示: 应在 ai-service；ROOT =", ROOT)

    if not SAMPLE_DIR.is_dir():
        raise FileNotFoundError(f"缺少样例库：{SAMPLE_DIR}")

    note: list[str] = [
        "# 05.06 RAG Chain · 实跑记录\n",
        f"- USE_CHAT: `{USE_CHAT}`",
        f"- min_score: `{MIN_SCORE}` top_k: `{TOP_K}`",
        f"- embedding: `{default_embedding_model()}`",
        f"- provider: `{describe_provider().get('provider')}`",
        "",
    ]

    # ---- STEP 1 · 建索引 + format_docs 预览 ----
    print("\n" + "=" * 52, "STEP 1 · 建索引并预览 format_docs")
    index = build_index(chunks_from_markdown_dir(SAMPLE_DIR))
    retriever = KnowledgeRetriever(index=index, top_k=TOP_K)
    docs_preview = retriever.invoke(Q_OK)
    ctx = format_docs(docs_preview)
    print(ctx[:320], "..." if len(ctx) > 320 else "")
    assert "[1]" in ctx and "source=" in ctx
    print("ASSERT: format_docs 含 [n] 与 source → PASS")
    note.append("## STEP 1 · format_docs\n")
    note.append("```text\n" + ctx[:500] + "\n```\n")

    # ---- STEP 2 · 库内题整链 ----
    print("\n" + "=" * 52, "STEP 2 · 库内题整链 invoke")
    result_ok = run_rag_chain(
        Q_OK,
        index=index,
        top_k=TOP_K,
        min_score=MIN_SCORE,
        use_chat=USE_CHAT,
    )
    print("refused:", result_ok["refused"], "top1:", result_ok.get("top1_score"))
    print("sources:", result_ok.get("sources"))
    print("answer:\n", result_ok["answer"][:500])
    assert result_ok["refused"] is False, "库内退货题不应拒答"
    assert any("return" in s.lower() for s in result_ok.get("sources") or []), (
        "应命中 return_policy"
    )
    if USE_CHAT:
        ans = result_ok["answer"]
        assert "7" in ans or "七天" in ans or "自然日" in ans or "资料" in ans
    print("ASSERT: 有据问答（未拒答 + 有 source）→ PASS")
    note.append("## STEP 2 · 库内题\n")
    note.append(f"- refused: `{result_ok['refused']}` top1: `{result_ok.get('top1_score')}`")
    note.append(f"- sources: `{result_ok.get('sources')}`")
    note.append("```text\n" + str(result_ok["answer"])[:600] + "\n```\n")

    # ---- STEP 3 · 离谱题拒答（短路）----
    print("\n" + "=" * 52, "STEP 3 · 离谱题拒答闸门")
    result_bad = run_rag_chain(
        Q_BAD,
        index=index,
        top_k=TOP_K,
        min_score=MIN_SCORE,
        use_chat=USE_CHAT,
    )
    print("refused:", result_bad["refused"], "reason:", result_bad.get("reason"))
    print("top1:", result_bad.get("top1_score"))
    print("answer:\n", result_bad["answer"][:240])
    assert result_bad["refused"] is True, "离谱题应拒答"
    assert result_bad["answer"] == REFUSE_TEXT
    print("ASSERT: 拒答短路（固定话术、不编造）→ PASS")
    note.append("## STEP 3 · 拒答\n")
    note.append(f"- reason: `{result_bad.get('reason')}`")
    note.append(f"- top1: `{result_bad.get('top1_score')}`")
    note.append("```text\n" + result_bad["answer"] + "\n```\n")

    # ---- STEP 4 · 也可 build_rag_chain 再 invoke（真模型时）----
    print("\n" + "=" * 52, "STEP 4 · build_rag_chain 接口")
    if USE_CHAT:
        chain = build_rag_chain(
            retriever,
            get_chat_model(temperature=0.1),
            min_score=MIN_SCORE,
        )
        r2 = chain.invoke({"question": "订单一般几天能发货？"})
        print("refused:", r2["refused"], "sources:", r2.get("sources"))
        print(r2["answer"][:300])
        assert isinstance(r2["answer"], str) and r2["answer"].strip()
        note.append("## STEP 4 · build_rag_chain\n")
        note.append(f"- sources: `{r2.get('sources')}`")
        note.append("```text\n" + r2["answer"][:500] + "\n```\n")
    else:
        # 离线再验：字符串输入同样合法
        r2 = run_rag_chain(
            "选修数据结构需要先修哪些课？",
            index=index,
            use_chat=False,
            min_score=MIN_SCORE,
        )
        print("offline invoke str question, refused:", r2["refused"])
        print("sources:", r2.get("sources"))
        assert r2["refused"] is False
        note.append("## STEP 4 · 离线另一问\n")
        note.append(f"- sources: `{r2.get('sources')}`\n")
    print("ASSERT: 统一 invoke 接口 → PASS")

    note.append("## 结论\n")
    note.append("- LCEL RAG：question → Retriever → 闸门 → Prompt → Model。")
    note.append("- 拒答是硬短路：低相关不进 Generate，省钱且更安全。")
    note.append("- 有据回答应能从 sources / 文末引用看到文件名。")
    note.append("")

    NOTE_PATH.parent.mkdir(parents=True, exist_ok=True)
    NOTE_PATH.write_text("\n".join(note), encoding="utf-8")
    print(f"\n笔记已写入: {NOTE_PATH}")
    print("SUMMARY: rag_chain 验收通过")


if __name__ == "__main__":
    main()
