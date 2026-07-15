# scripts/04_03_tenant_isolation_demo.py
"""04.03 多库隔离演示：同库混存 + 强制 tenant_id 过滤，对照串库风险。

【本课要感受的三件事】
1. 缺 tenant_id → 直接报错（默认拒绝查全库）
2. 同一问题分别查 tenant_a / tenant_b → 7 天 vs 15 天，互不串味
3. 漏过滤的全库检索可能把 B 的 15 天捞进「问 A」的结果——隔离必须在检索层

样例目录：
  samples/tenants/tenant_a/return_policy.md  → 7 天
  samples/tenants/tenant_b/return_policy.md  → 15 天
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from app.lessons.m02_03_embeddings import default_embedding_model  # noqa: E402
from app.lessons.m04_03_tenant_store import (  # noqa: E402
    TENANT_FIELD,
    build_index_from_tenant_roots,
    collection_for_tenant,
    count_by_tenant,
    format_tenant_hit,
    retrieve_for_tenant,
    retrieve_without_tenant_filter,
)

# ======================== 可调开关 ========================

TENANT_ROOT = ROOT / "samples" / "tenants"
NOTE_PATH = ROOT / "notes" / "tenant_isolation_result.md"
QUESTION = "无理由退货可以几天内申请？"

TENANT_A = "tenant_a"
TENANT_B = "tenant_b"
EXPECT_A = "7"
EXPECT_B = "15"


def main() -> None:
    dir_a = TENANT_ROOT / TENANT_A
    dir_b = TENANT_ROOT / TENANT_B
    if not dir_a.is_dir() or not dir_b.is_dir():
        raise FileNotFoundError(f"请准备 {dir_a} 与 {dir_b}")

    print("=" * 52, "CONFIG")
    print("embedding:", default_embedding_model())
    print("question:", QUESTION)
    print("hard-isolation name A:", collection_for_tenant(TENANT_A))
    print("hard-isolation name B:", collection_for_tenant(TENANT_B))
    print(f"（本脚本用同库 + {TENANT_FIELD} 过滤；上列为多 Collection 命名对照）")

    note: list[str] = [
        "# 04.03 多库隔离 · 实跑记录\n",
        f"- Embedding：`{default_embedding_model()}`",
        f"- 问题：{QUESTION}",
        f"- 硬隔离 Collection 名示例：`{collection_for_tenant(TENANT_A)}` / "
        f"`{collection_for_tenant(TENANT_B)}`",
        "",
    ]

    # ---- STEP 0 · 混存入库（模拟同 Collection）----
    print("\n" + "=" * 52, "STEP 0 · 两租户混存入库（同索引 + metadata）")
    index = build_index_from_tenant_roots({TENANT_A: dir_a, TENANT_B: dir_b})
    n_a = count_by_tenant(index, TENANT_A)
    n_b = count_by_tenant(index, TENANT_B)
    print(f"总块数: {len(index.items)}  {TENANT_A}={n_a}  {TENANT_B}={n_b}")
    assert n_a >= 1 and n_b >= 1
    print("ASSERT: 两租户均有块 → PASS")
    note.append("## STEP 0 · 入库\n")
    note.append(f"- 总块数 `{len(index.items)}`；{TENANT_A}={n_a}；{TENANT_B}={n_b}")
    note.append("")

    # ---- STEP 1 · 缺租户必须失败 ----
    print("\n" + "=" * 52, "STEP 1 · 缺 tenant_id 必须报错")
    raised = False
    try:
        retrieve_for_tenant(index, QUESTION, tenant_id="")  # type: ignore[arg-type]
    except ValueError as e:
        raised = True
        print(f"捕捉到 ValueError: {e}")
    assert raised, "空 tenant_id 应抛 ValueError"
    print("ASSERT: 默认拒绝查全库 → PASS")
    note.append("## STEP 1 · 默认拒绝\n")
    note.append(f"- 空 `{TENANT_FIELD}` → `ValueError`（未查全库）")
    note.append("")

    # ---- STEP 2 · 分租户查询，互不串库 ----
    print("\n" + "=" * 52, "STEP 2 · 同问分租户检索")
    hits_a = retrieve_for_tenant(index, QUESTION, tenant_id=TENANT_A, top_k=3)
    hits_b = retrieve_for_tenant(index, QUESTION, tenant_id=TENANT_B, top_k=3)

    print(f"\n[{TENANT_A}]")
    for i, (c, s) in enumerate(hits_a, start=1):
        print(f"  #{i}  {format_tenant_hit(c, s)}")
    print(f"\n[{TENANT_B}]")
    for i, (c, s) in enumerate(hits_b, start=1):
        print(f"  #{i}  {format_tenant_hit(c, s)}")

    assert hits_a and hits_b
    assert all(c.tenant_id == TENANT_A for c, _ in hits_a)
    assert all(c.tenant_id == TENANT_B for c, _ in hits_b)
    top_a = hits_a[0][0].text
    top_b = hits_b[0][0].text
    assert f"{EXPECT_A} 个自然日" in top_a, f"A 的 top1 应含「{EXPECT_A} 个自然日」"
    assert f"{EXPECT_B} 个自然日" in top_b, f"B 的 top1 应含「{EXPECT_B} 个自然日」"
    assert f"{EXPECT_B} 个自然日" not in top_a, "A 的结果不应出现 15 天政策"
    # B 文案里可能提到「与租户 A 的 7 天不同」——允许对照句，但主条款须是 15
    assert "十五天" in top_b or f"**{EXPECT_B}**" in top_b or f"{EXPECT_B} 个自然日" in top_b

    print("ASSERT: A 只含本租户块且政策为 7 天 → PASS")
    print("ASSERT: B 只含本租户块且政策为 15 天 → PASS")

    note.append("## STEP 2 · 分租户\n")
    note.append(f"- A top1: {format_tenant_hit(*hits_a[0])}")
    note.append(f"- B top1: {format_tenant_hit(*hits_b[0])}")
    note.append("")

    # ---- STEP 3 · 反面：漏过滤可能串库 ----
    print("\n" + "=" * 52, "STEP 3 · 反面教材：漏过滤查全库")
    leaked = retrieve_without_tenant_filter(index, QUESTION, top_k=4)
    print("全库 top4（无 tenant 过滤）：")
    tenant_mix = set()
    for i, (c, s) in enumerate(leaked, start=1):
        print(f"  #{i}  {format_tenant_hit(c, s)}")
        tenant_mix.add(c.tenant_id)

    # 同一问题下，无过滤时 topK 里经常同时出现两家
    mixed = len(tenant_mix) > 1
    print(f"topK 出现的租户集合: {sorted(tenant_mix)}")
    if mixed:
        print("ASSERT: 漏过滤导致多租户混入 topK → PASS（串库风险坐实）")
    else:
        print(
            "WARN: 本轮巧合未混租户；换问法或看全文仍应用过滤。"
            "隔离不能赌排序。"
        )
    # 至少证明：无过滤函数能返回任意租户（与强制过滤对比）
    assert leaked, "全库检索不应为空"

    note.append("## STEP 3 · 漏过滤\n")
    note.append(f"- topK 租户集合：`{sorted(tenant_mix)}`")
    note.append("- 结论：过滤必须写在检索 API，不能指望 Prompt。")
    note.append("")
    note.append("## 选用策略（笔记自填）\n")
    note.append("- 本课验证：metadata 强制过滤可互不串库。")
    note.append("- 强合规场景应升级为多 Collection / 强分区。")
    note.append("")

    NOTE_PATH.parent.mkdir(parents=True, exist_ok=True)
    NOTE_PATH.write_text("\n".join(note), encoding="utf-8")
    print(f"\n笔记已写入: {NOTE_PATH}")
    print("SUMMARY: 租户隔离对照实验通过")


if __name__ == "__main__":
    main()
