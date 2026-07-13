# scripts/03_02_rag_pipeline_demo.py
"""课次 03.02 · RAG 全流程演示：Index → Retrieve → Augment → Generate。

源码课次文件：
- app/lessons/m03_02_splitters.py
- app/lessons/m03_02_ingest.py
- app/lessons/m03_02_retriever.py
- app/lessons/m03_02_qa_chain.py
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from app.lessons.m03_02_qa_chain import augment, generate, run_rag  # noqa: E402
from app.llm.client import default_model  # noqa: E402
from app.lessons.m02_03_embeddings import default_embedding_model  # noqa: E402
from app.lessons.m03_02_ingest import build_index  # noqa: E402
from app.lessons.m03_02_retriever import retrieve  # noqa: E402
from app.lessons.m03_02_splitters import split_by_heading  # noqa: E402

# ======================== 可调开关 ========================

# False：跑到 Augment 为止，打印 Prompt，不调 Chat
USE_CHAT = True

TOP_K = 2

# 样例文档与问题（与专栏主示例一致）
SAMPLE_DOC = ROOT / "samples" / "return_policy.md"
QUESTION = "七天无理由怎么算？"

# 验收：带资料路径应能答出与「7 日/七天」相关要点
EXPECT_KEYWORDS = ("7", "七", "日", "天")


def main() -> None:
    if not SAMPLE_DOC.exists():
        raise FileNotFoundError(f"请先准备样例文档：{SAMPLE_DOC}")

    doc_text = SAMPLE_DOC.read_text(encoding="utf-8")

    print("=" * 40, "CONFIG")
    print("doc:", SAMPLE_DOC.name)
    print("embedding:", default_embedding_model())
    print("chat_model:", default_model() if USE_CHAT else "(skipped)")
    print("USE_CHAT:", USE_CHAT)
    print("question:", QUESTION)

    note: list[str] = [
        "# RAG 四步全流程实跑\n\n",
        f"- 文档：`{SAMPLE_DOC.name}`\n",
        f"- 问题：{QUESTION}\n",
        f"- Embedding：`{default_embedding_model()}`\n",
        f"- Chat：`{default_model() if USE_CHAT else 'skipped'}`\n\n",
    ]

    # ==================== Step 1 · Index ====================
    print("\n" + "=" * 40, "STEP 1 · Index（离线）")
    t0 = time.perf_counter()
    chunks = split_by_heading(doc_text, source=SAMPLE_DOC.name)
    index = build_index(chunks)
    ms_index = (time.perf_counter() - t0) * 1000
    print(f"切分块数: {len(chunks)}")
    for c in chunks:
        preview = c.text[:60].replace("\n", " ")
        print(f"  chunk {c.chunk_id}: {preview}...")
    print(f"索引块数: {len(index.items)}，model={index.model}，耗时 {ms_index:.0f} ms")

    note.append("## Step 1 · Index\n\n")
    note.append(f"- 块数：**{len(chunks)}**\n")
    note.append(f"- 耗时：{ms_index:.0f} ms\n\n")
    for c in chunks:
        note.append(f"- chunk {c.chunk_id}：`{c.text[:80].replace(chr(10), ' ')}...`\n")
    note.append("\n")

    # ==================== Step 2 · Retrieve ====================
    print("\n" + "=" * 40, "STEP 2 · Retrieve（在线）")
    t0 = time.perf_counter()
    hits = retrieve(index, QUESTION, top_k=TOP_K)
    ms_ret = (time.perf_counter() - t0) * 1000
    print(f"top_{TOP_K} 召回（耗时 {ms_ret:.0f} ms）：")
    for chunk, score in hits:
        print(f"  {score:.4f}  chunk {chunk.chunk_id}  {chunk.text[:50].replace(chr(10), ' ')}...")

    # 召回应包含「七天无理由」相关块（chunk_id=1 左右，按标题切分）
    hit_text = " ".join(c.text for c, _ in hits)
    assert "七天" in hit_text or "7" in hit_text, "Retrieve 应召回到退货政策相关块"
    print("ASSERT: Retrieve 含退货相关块 → PASS")

    note.append("## Step 2 · Retrieve\n\n")
    note.append(f"- top_k={TOP_K}，耗时 {ms_ret:.0f} ms\n\n")
    for chunk, score in hits:
        note.append(f"- `{score:.4f}` chunk {chunk.chunk_id}：{chunk.text[:100]}...\n")
    note.append("\n")

    # ==================== Step 3 · Augment ====================
    print("\n" + "=" * 40, "STEP 3 · Augment（在线）")
    prompt = augment(QUESTION, hits)
    print("增强后 Prompt 预览：\n", prompt[:400], "...")

    note.append("## Step 3 · Augment\n\n")
    note.append(f"```text\n{prompt}\n```\n\n")

    # ==================== Step 4 · Generate ====================
    print("\n" + "=" * 40, "STEP 4 · Generate（在线）")
    if USE_CHAT:
        t0 = time.perf_counter()
        answer = generate(prompt)
        ms_gen = (time.perf_counter() - t0) * 1000
        print(f"耗时 {ms_gen:.0f} ms")
        print("ANSWER:\n", answer)

        ok = any(k in answer for k in EXPECT_KEYWORDS)
        assert ok, f"Generate 应含 7 日/七天 相关表述，实际：{answer[:200]}"
        print("ASSERT: Generate 含七天/7日要点 → PASS")

        note.append("## Step 4 · Generate\n\n")
        note.append(f"耗时 {ms_gen:.0f} ms\n\n{answer}\n\n")
    else:
        print("USE_CHAT=False，跳过 Generate。")
        note.append("## Step 4 · Generate\n\n（skipped）\n\n")

    # 也可用 run_rag 一行调用在线三步（Index 仍须离线先建好）
    _ = run_rag(index, QUESTION, top_k=TOP_K, use_chat=False)

    note.append("## 结论\n\n")
    note.append(
        "口诀：**先入库（Index），再找出（Retrieve），再塞进（Augment），再生成（Generate）**。\n"
        "- 离线：文档变更时才 Index\n"
        "- 在线：每个用户问题只跑 Retrieve → Augment → Generate\n"
    )

    out = ROOT / "notes" / "rag_pipeline_result.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("".join(note), encoding="utf-8")
    print(f"\n记录已写入：{out}")


if __name__ == "__main__":
    main()
