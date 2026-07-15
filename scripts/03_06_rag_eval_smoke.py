# scripts/03_06_rag_eval_smoke.py
"""03.06 最小召回评估：读 10 条小测集，看 topK 是否包含 expected_source。

【为什么先评召回、不评答案对错】
答案对错受 Chat 模型影响大；召回@K 只测「检索有没有把正确文件捞上来」，
调切分 / topK / Embedding 时先固定这 10 题，才能用数据说话。

本脚本默认不调 Chat，只跑 retrieve + 打勾，几秒可出基线命中率。
"""

from __future__ import annotations

import json
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
from app.lessons.m03_05_retriever import build_index, format_hit, retrieve  # noqa: E402
from app.lessons.m03_06_qa_chain import hit_sources, recall_hit  # noqa: E402

# ======================== 可调开关 ========================

TOP_K = 5  # 评测用的 K；改这里会直接影响命中率，调参时只改一处
SAMPLE_DIR = ROOT / "samples" / "docs"
CASES_PATH = ROOT / "tests" / "rag_cases.jsonl"
NOTE_PATH = ROOT / "notes" / "rag_eval_baseline.md"

# 可选：内存 / Milvus（需先跑 03.04 入库）
INDEX_BACKEND = os.getenv("INDEX_BACKEND", "memory").strip().lower()


def load_cases(path: Path) -> list[dict]:
    """逐行读 jsonl：每行一个 {question, expected_source}。"""
    cases: list[dict] = []
    for line_no, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError as e:
            raise ValueError(f"{path} 第 {line_no} 行不是合法 JSON：{e}") from e
        if "question" not in obj or "expected_source" not in obj:
            raise ValueError(f"{path} 第 {line_no} 行缺少 question / expected_source")
        cases.append(obj)
    return cases


def main() -> None:
    if not SAMPLE_DIR.is_dir():
        raise FileNotFoundError(f"请先准备样例目录：{SAMPLE_DIR}")
    if not CASES_PATH.is_file():
        raise FileNotFoundError(f"请先准备小测集：{CASES_PATH}")

    cases = load_cases(CASES_PATH)
    print("=" * 52, "CONFIG")
    print("cases:", CASES_PATH.name, f"({len(cases)} 题)")
    print("top_k:", TOP_K)
    print("index_backend:", INDEX_BACKEND)
    print("embedding:", default_embedding_model())

    # ---- Index ----
    print("\n" + "=" * 52, "STEP 1 · Index")
    t0 = time.perf_counter()
    if INDEX_BACKEND == "milvus":
        # 与 03.05 相同：走 ingest 包里的 connect，便于 entity_count 校验
        from app.lessons.m03_04_ingest import connect_milvus_index

        index = connect_milvus_index()
        if index.entity_count == 0:
            raise RuntimeError(
                "Milvus 库为空，请先运行：python scripts/03_04_ingest_sample_docs.py"
            )
        print(f"Milvus entity_count: {index.entity_count}")
    else:
        chunks = chunks_from_markdown_dir(SAMPLE_DIR)
        index = build_index(chunks)
        print(f"内存索引块数: {len(index.items)}")
    print(f"耗时: {(time.perf_counter() - t0) * 1000:.0f} ms")

    # ---- Evaluate ----
    print("\n" + "=" * 52, "STEP 2 · Recall@K")
    rows: list[str] = []
    hit_count = 0
    fail_examples: list[str] = []

    for i, case in enumerate(cases, start=1):
        q = case["question"]
        expect = case["expected_source"]
        hits = retrieve(index, q, top_k=TOP_K)
        ok = recall_hit(hits, expect)
        if ok:
            hit_count += 1
            mark = "PASS"
        else:
            mark = "FAIL"
            fail_examples.append(
                f"- Q{i}: {q}\n  期望: {expect}\n  实际: {hit_sources(hits)}"
            )

        top1 = format_hit(*hits[0]) if hits else "(empty)"
        print(f"[{mark}] Q{i:02d}  expect={expect}")
        print(f"       Q: {q}")
        print(f"       top1: {top1}")
        rows.append(
            f"| {i} | {q} | `{expect}` | "
            f"{'✓' if ok else '✗'} | `{hit_sources(hits)[:3]}` |"
        )

    rate = hit_count / len(cases) if cases else 0.0
    print("\n" + "=" * 52, "SUMMARY")
    print(f"命中: {hit_count}/{len(cases)}  ≈ 召回率 {rate:.0%}（简化版 Recall@{TOP_K}）")

    # ---- 写基线笔记 ----
    NOTE_PATH.parent.mkdir(parents=True, exist_ok=True)
    fail_block = "\n".join(fail_examples) if fail_examples else "_本题集本轮全部命中_"
    NOTE_PATH.write_text(
        "\n".join(
            [
                "# 03.06 召回评测基线\n",
                f"- 小测集：`tests/rag_cases.jsonl`（{len(cases)} 题）",
                f"- top_k：{TOP_K}",
                f"- Embedding：`{default_embedding_model()}`",
                f"- 后端：`{INDEX_BACKEND}`",
                f"- **命中率：{hit_count}/{len(cases)} ≈ {rate:.0%}**",
                "",
                "> 以后改切分 / topK / 模型，用同一题集重跑，和本基线对比。",
                "",
                "## 明细",
                "",
                "| # | 问题 | 期望 source | 命中 | top sources（最多 3） |",
                "|---|------|-------------|------|------------------------|",
                *rows,
                "",
                "## 失败题（优先分析）",
                "",
                fail_block,
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(f"基线笔记: {NOTE_PATH}")


if __name__ == "__main__":
    main()
