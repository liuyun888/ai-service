# scripts/03_03_splitters_demo.py
"""课次 03.03 · 文档分割演示（两种切法并排对比）。

源码课次文件：app/lessons/m03_03_splitters.py（import 03.02，不修改 03.02 文件）
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.lessons.m03_03_splitters import (  # noqa: E402
    compare_strategies,
    find_chunks_containing,
    format_chunk_preview,
)

# ======================== 可调开关 ========================

# 固定切分：故意设小一点，方便看到「切太碎」的失败模式
FIXED_SIZE = 200
FIXED_OVERLAP = 40

# 样例文档（含规格表 + 安装步骤 1～5，与专栏主示例一致）
SAMPLE_DOC = ROOT / "samples" / "product_manual.md"

# 验收问题：哪种切法更容易整段召回「第 4 步」？
PROBE_KEYWORD = "第 4 步"


def main() -> None:
    if not SAMPLE_DOC.exists():
        raise FileNotFoundError(f"请先准备样例文档：{SAMPLE_DOC}")

    doc_text = SAMPLE_DOC.read_text(encoding="utf-8")
    result = compare_strategies(
        doc_text,
        source=SAMPLE_DOC.name,
        fixed_size=FIXED_SIZE,
        fixed_overlap=FIXED_OVERLAP,
    )

    print("=" * 48, "CONFIG")
    print("doc:", SAMPLE_DOC.name)
    print("fixed:", f"size={FIXED_SIZE}, overlap={FIXED_OVERLAP}")
    print("heading: split by ##")
    print("probe:", PROBE_KEYWORD)

    print("\n" + "=" * 48, "切法 A · 固定长度")
    print("块数:", len(result.fixed))
    for c in result.fixed:
        print(" ", format_chunk_preview(c))

    print("\n" + "=" * 48, "切法 B · 按标题")
    print("块数:", len(result.heading))
    for c in result.heading:
        print(" ", format_chunk_preview(c))

    # ---------- 对比：谁更容易回答「第 4 步是什么」 ----------
    print("\n" + "=" * 48, f"对比 · 含「{PROBE_KEYWORD}」的块")
    fixed_hits = find_chunks_containing(result.fixed, PROBE_KEYWORD)
    heading_hits = find_chunks_containing(result.heading, PROBE_KEYWORD)

    print(f"固定切分命中 {len(fixed_hits)} 块：")
    for c in fixed_hits:
        print(" ", format_chunk_preview(c, max_len=120))

    print(f"按标题切分命中 {len(heading_hits)} 块：")
    for c in heading_hits:
        print(" ", format_chunk_preview(c, max_len=120))

    # 固定切：没有任何一块同时含 第 1～5 步（步骤被刀口拆开）
    all_steps = tuple(f"第 {n} 步" for n in range(1, 6))
    fixed_has_all = any(all(s in c.text for s in all_steps) for c in result.fixed)
    assert not fixed_has_all, "固定切不应把 5 个步骤完整留在同一块"
    print("\nASSERT: 固定切 · 5 步被拆散，无单块含 1～5 步 → PASS")

    # 按标题切：安装步骤应在同一 chunk，且含步骤 1～5
    step_chunk = next(
        (c for c in result.heading if c.section == "安装步骤"), None
    )
    assert step_chunk is not None, "按标题切应存在「安装步骤」块"
    for n in ("第 1 步", "第 2 步", "第 3 步", "第 4 步", "第 5 步"):
        assert n in step_chunk.text, f"安装步骤块应含 {n}"
    print("\nASSERT: 按标题切 · 安装步骤 1～5 在同一块 → PASS")

    # 固定切：块数应明显多于按标题（演示切太碎）
    assert len(result.fixed) > len(result.heading), (
        f"固定切块数({len(result.fixed)}) 应多于按标题({len(result.heading)})"
    )
    print(
        f"ASSERT: 固定切 {len(result.fixed)} 块 > 按标题 {len(result.heading)} 块 → PASS"
    )

    # 写笔记
    note: list[str] = [
        "# 03.03 文档分割 · 两种切法对比\n\n",
        f"- 文档：`{SAMPLE_DOC.name}`\n",
        f"- 固定切：size={FIXED_SIZE}, overlap={FIXED_OVERLAP}\n",
        f"- 探针问题：{PROBE_KEYWORD} 在哪一块？\n\n",
        "## 切法 A · 固定长度\n\n",
        f"- 块数：**{len(result.fixed)}**\n\n",
    ]
    for c in result.fixed:
        note.append(f"- {format_chunk_preview(c)}\n")
    note.append("\n## 切法 B · 按标题\n\n")
    note.append(f"- 块数：**{len(result.heading)}**\n\n")
    for c in result.heading:
        note.append(f"- {format_chunk_preview(c)}\n")

    note.append("\n## 结论（参考答案）\n\n")
    note.append(
        "- **固定切**容易把「安装步骤」拦腰斩断，问「第 4 步是什么」时可能只召回半段。\n"
        "- **按标题切**把「安装步骤」整段保留，步骤 1～5 在同一块，检索更可用。\n"
        "- 生产环境常见做法：先按标题/段落切，过长的小节再用固定长度 + overlap 二次切。\n"
    )

    out = ROOT / "notes" / "splitters_compare_result.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("".join(note), encoding="utf-8")
    print(f"\n笔记已写入：{out}")


if __name__ == "__main__":
    main()
