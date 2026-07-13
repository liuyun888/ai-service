# scripts/02_03_embedding_demo.py
"""02.03 Embedding 实操：真实向量化三句文本并比较余弦相似度。

【你要看懂的一件事】
「续航多久」和「电池能用几小时」意思近 → 相似度应明显高于
「续航多久」和「食堂吃什么」。

禁止用随机数/哈希冒充向量；必须走 app.lessons.m02_03_embeddings 的真模型。
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

from app.lessons.m02_03_embeddings import (  # noqa: E402
    cosine,
    default_embedding_model,
    embed_texts,
)

# 三句对照：
# 0 与 1 = 同义（都在问续航）
# 0 与 2 = 无关（耳机 vs 食堂）
TEXTS = [
    "降噪耳机续航多久",
    "这款耳机电池能用几小时",
    "明天食堂吃什么",
]


def main() -> None:
    """向量化 → 打印维度与向量头 → 算相似度 → 断言 → 写笔记。"""
    provider = os.getenv("EMBEDDING_PROVIDER", "local").strip() or "local"
    model = default_embedding_model()
    print("=" * 40, "CONFIG")
    print("provider:", provider)
    print("model:", model)

    print("=" * 40, "EMBED")
    # 一次请求三句，得到三条等长向量
    vecs = embed_texts(TEXTS)
    dim = len(vecs[0])

    # 同一批向量维度必须一致（否则没法两两比）
    assert all(len(v) == dim for v in vecs), "同一批向量维度必须一致"
    # 真向量几乎不可能全是 0；全 0 多半是实现写错了
    assert any(abs(x) > 1e-8 for x in vecs[0]), "疑似空/伪向量"

    print("count:", len(vecs))
    print("dim:", dim)
    # 只看前 8 维，感受「真是一串小数」
    print("vec0_head:", [round(x, 5) for x in vecs[0][:8]])

    # 余弦相似度：越大越像
    sim12 = cosine(vecs[0], vecs[1])  # 同义
    sim13 = cosine(vecs[0], vecs[2])  # 无关
    print("=" * 40, "COSINE")
    print("sim_1_2 (同义续航):", round(sim12, 4))
    print("sim_1_3 (无关食堂):", round(sim13, 4))

    # 验收：同义必须明显高于无关（阈值 0.15 较保守，兼容不同模型）
    assert sim12 > sim13, f"期望 sim_1_2 > sim_1_3，实际 {sim12=} {sim13=}"
    assert sim12 - sim13 > 0.15, (
        f"同义与无关差距过小：{sim12 - sim13:.4f}，请检查是否用了真 Embedding"
    )
    print("ASSERT: sim_1_2 > sim_1_3 且差距 > 0.15  → PASS")

    # 写入笔记，方便对照专栏验收清单
    out = ROOT / "notes" / "embedding_similarity.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Embedding 相似度实跑记录\n",
        f"- provider: `{provider}`\n",
        f"- model: `{model}`\n",
        f"- dim: **{dim}**\n",
        f"- vec0_head: `{[round(x, 5) for x in vecs[0][:8]]}`\n",
        "\n## 文本\n",
    ]
    for i, t in enumerate(TEXTS, 1):
        lines.append(f"{i}. {t}\n")
    lines.extend(
        [
            "\n## 余弦相似度\n",
            f"- sim(1,2) 同义续航 = **{sim12:.4f}**\n",
            f"- sim(1,3) 无关食堂 = **{sim13:.4f}**\n",
            "\n结论：同义句明显高于无关句 → Embedding 几何距离可用。\n",
            "\n> 写入 Milvus 前确认 Collection 维度与本 dim 一致"
            "（本仓库 `scripts/00_05_init_milvus.py` 默认 1024；"
            "若用 bge-small-zh-v1.5 为 512，需改 DIM 或换模型）。\n",
        ]
    )
    out.write_text("".join(lines), encoding="utf-8")
    print(f"\n记录已写入：{out}")


if __name__ == "__main__":
    main()
