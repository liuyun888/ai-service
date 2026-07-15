# scripts/03_06_qa_chain_demo.py
"""03.06 上下文注入演示：Retrieve → Augment → Generate（带 [n] 引用）。

【本课要感受的两件事】
1. 资料编号进 Prompt 后，模型更容易写出「根据[1]…」并点名 source
2. USE_CHAT=False 时可先验收 Prompt 长什么样，再花费用调模型

默认走内存索引（与 03.05 相同样例库），不强制 Milvus。
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from app.lessons.m02_03_embeddings import default_embedding_model  # noqa: E402
from app.lessons.m03_05_ingest_batch import chunks_from_markdown_dir  # noqa: E402
from app.lessons.m03_05_retriever import build_index, format_hit  # noqa: E402
from app.lessons.m03_06_qa_chain import answer  # noqa: E402
from app.llm.client import default_model  # noqa: E402

# ======================== 可调开关 ========================

# False：只打印增强 Prompt，不调 Chat（离线/省费用验收 Augment）
USE_CHAT = True

TOP_K = 4
SAMPLE_DIR = ROOT / "samples" / "docs"
NOTE_PATH = ROOT / "notes" / "qa_chain_demo_result.md"

# 与专栏主示例一致：耳机售后政策里的「七天无理由」
DEMO_QUESTION = "七天无理由退货需要什么条件？"
EXPECT_SOURCE = "return_policy.md"
EXPECT_KEYWORDS = ("7", "七", "自然日", "完好")


def main() -> None:
    if not SAMPLE_DIR.is_dir():
        raise FileNotFoundError(f"请先准备样例目录：{SAMPLE_DIR}")

    print("=" * 52, "CONFIG")
    print("sample_dir:", SAMPLE_DIR)
    print("embedding:", default_embedding_model())
    print("chat_model:", default_model() if USE_CHAT else "(skipped)")
    print("USE_CHAT:", USE_CHAT)
    print("top_k:", TOP_K)
    print("question:", DEMO_QUESTION)

    # ---- Index（离线，内存）----
    print("\n" + "=" * 52, "STEP 1 · Index")
    t0 = time.perf_counter()
    chunks = chunks_from_markdown_dir(SAMPLE_DIR)
    index = build_index(chunks)
    print(f"总块数: {len(index.items)}  耗时: {(time.perf_counter() - t0) * 1000:.0f} ms")

    # ---- Retrieve → Augment → Generate ----
    print("\n" + "=" * 52, "STEP 2 · qa_chain")
    t1 = time.perf_counter()
    result = answer(index, DEMO_QUESTION, top_k=TOP_K, use_chat=USE_CHAT)
    ms = (time.perf_counter() - t1) * 1000

    print(f"\n--- hits（top_{TOP_K}）---")
    for i, (chunk, score) in enumerate(result["hits"], start=1):
        print(f"  #{i}  {format_hit(chunk, score)}")

    print("\n--- augmented prompt（节选）---")
    prompt: str = result["prompt"]
    # 只展示前 800 字，避免终端刷屏；完整 Prompt 写进笔记
    print(prompt[:800] + ("…" if len(prompt) > 800 else ""))

    print("\n--- answer ---")
    print(result["answer"])
    print(f"\n耗时: {ms:.0f} ms")

    # ---- 简易验收 ----
    sources = [c.source for c, _ in result["hits"]]
    source_ok = EXPECT_SOURCE in sources
    print("\n" + "=" * 52, "ASSERT")
    print(f"topK 含 {EXPECT_SOURCE}:", "PASS" if source_ok else "FAIL")

    if USE_CHAT:
        ans = result["answer"]
        kw_ok = any(k in ans for k in EXPECT_KEYWORDS)
        cite_ok = EXPECT_SOURCE in ans or "return_policy" in ans
        print("答案含关键要点（7日/完好等）:", "PASS" if kw_ok else "FAIL（人工再看）")
        print("答案提到期望 source:", "PASS" if cite_ok else "FAIL（人工再看）")

    # ---- 写笔记 ----
    NOTE_PATH.parent.mkdir(parents=True, exist_ok=True)
    NOTE_PATH.write_text(
        "\n".join(
            [
                "# 03.06 上下文注入 · 端到端演示记录\n",
                f"- 问题：{DEMO_QUESTION}",
                f"- top_k：{TOP_K}",
                f"- Embedding：`{default_embedding_model()}`",
                f"- Chat：`{default_model() if USE_CHAT else 'skipped'}`",
                f"- topK sources：{sources}",
                f"- 期望 source 命中：{'是' if source_ok else '否'}",
                "",
                "## Prompt",
                "",
                "```text",
                prompt,
                "```",
                "",
                "## Answer",
                "",
                result["answer"],
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(f"\n笔记已写入: {NOTE_PATH}")


if __name__ == "__main__":
    # 允许环境变量覆盖：USE_CHAT=0 python scripts/03_06_qa_chain_demo.py
    env_flag = os.getenv("USE_CHAT")
    if env_flag is not None:
        USE_CHAT = env_flag.strip().lower() in {"1", "true", "yes", "on"}
    main()
