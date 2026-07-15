# app/tools/knowledge.py
"""课次 06.04 · 政策/须知检索 Tool（mock 知识库，不接真实向量库）。

和 get_inventory 的分工（两类 Tool）：
- get_inventory / get_shipment：查**系统实时状态**（库存、运单）
- search_knowledge：查**文档里的固定政策**（退货几天、运费谁出…）

直觉：状态不能靠猜；条款也不该瞎编——但查条款走「文档检索」这类工具。
"""

from __future__ import annotations

from langchain_core.tools import tool

# 极小 mock 语料：关键词 → 条款原文（教学够用；生产应换检索器）
_MOCK_DOCS: list[dict[str, str]] = [
    {
        "id": "return_window",
        "title": "退货时效",
        "text": "自签收之日起 7 天内可申请无理由退货；商品需未损坏、配件齐全。",
        "keywords": "退货 几天 7天 无理由 退换 时效",
    },
    {
        "id": "return_freight",
        "title": "退货运费",
        "text": "质量问题由商家承担退货运费；无理由退货运费由买家承担。",
        "keywords": "运费 谁出 质量 无理由 退货运费",
    },
    {
        "id": "warranty",
        "title": "质保说明",
        "text": "耳机主机质保 12 个月；人为进水、私自拆机不在保修范围。",
        "keywords": "质保 保修 12个月 进水 拆机",
    },
    {
        "id": "shipping_eta",
        "title": "发货时效说明（非运单）",
        "text": "一般现货 48 小时内发货；具体在途位置请查运单，客服不编造 ETA。",
        "keywords": "发货 48小时 多久发 时效 ETA",
    },
]


def _score(query: str, doc: dict[str, str]) -> int:
    """按关键词命中数打粗分（重合的词越多越相关）。"""
    q = (query or "").strip().lower()
    if not q:
        return 0
    blob = f"{doc['title']} {doc['text']} {doc['keywords']}".lower()
    hits = 0
    for t in doc["keywords"].lower().split():
        if t and t in q:
            hits += 1
    for piece in ("退货", "运费", "质保", "保修", "发货", "7天", "无理由", "几天"):
        if piece in q and piece in blob:
            hits += 2
    return hits


@tool
def search_knowledge(query: str) -> str:
    """检索售后政策、质保、发货须知等固定文档（只读 mock）。

    何时用：用户问「退货几天 / 运费谁出 / 质保多久」等**条款类**问题。
    何时不用：问实时库存或运单到哪了（应分别用 get_inventory / get_shipment）。

    参数:
        query: 用户问题或检索短语，如「退货几天内可以」

    返回:
        命中: 一条或多条「title: text」；无命中: 「not_found」
    """
    q = (query or "").strip()
    if not q:
        return "error: query 不能为空"

    ranked = sorted(
        (( _score(q, d), d) for d in _MOCK_DOCS),
        key=lambda x: x[0],
        reverse=True,
    )
    # 至少要有一点分，避免「你好」扫出退货政策
    tops = [d for score, d in ranked if score > 0][:2]
    if not tops:
        return "not_found"

    lines = [f"[{d['id']}] {d['title']}: {d['text']}" for d in tops]
    return " | ".join(lines)
