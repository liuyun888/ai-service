# app/mcp/tools_inventory.py
"""课次 09.03 · 查库存业务纯函数（与 MCP 注册分层，方便单测）。

MCP 只是对外暴露的壳；真正逻辑写在这里，Server 里薄薄包一层即可。
"""

from __future__ import annotations

import json

# 演示库存表：SKU 必须含颜色/尺码后缀（和 description 里的约定一致）
MOCK_DB: dict[str, dict[str, object]] = {
    "SHOE-RED-42": {"qty": 7, "warehouse": "华东一仓"},
    "SHOE-BLK-41": {"qty": 0, "warehouse": "华南二仓"},
    "BAG-BLU-M": {"qty": 3, "warehouse": "华东一仓"},
}


def get_inventory(sku: str) -> str:
    """按 SKU 查询可用库存；不要用于下单或改库存。

    参数:
        sku: 含颜色尺码后缀，如 SHOE-RED-42

    返回:
        成功：短 JSON 字符串 {sku, qty, warehouse}
        失败：error=...; hint=...（不抛异常，方便模型回灌）
    """
    key = (sku or "").strip().upper()
    if not key:
        return "error=empty_sku; hint=传入如 SHOE-RED-42"
    row = MOCK_DB.get(key)
    if not row:
        return (
            f"error=not_found; hint=检查 SKU 是否含颜色尺码后缀; sku={key}; "
            f"known={sorted(MOCK_DB)}"
        )
    payload = {"sku": key, "qty": row["qty"], "warehouse": row["warehouse"]}
    return json.dumps(payload, ensure_ascii=False)


def get_shipment(tracking_no: str) -> str:
    """按运单号查询物流状态；不要用于改地址或拦截件。

    与 get_inventory 同一 Schema 形状：一个主键 → 短 JSON / error=。
    """
    no = (tracking_no or "").strip().upper()
    if not no:
        return "error=empty_tracking; hint=传入如 SF1234567890"
    # 演示：以 SF 开头视为在途
    if no.startswith("SF") and len(no) >= 10:
        return json.dumps(
            {"tracking_no": no, "status": "in_transit", "last_hub": "杭州转运中心"},
            ensure_ascii=False,
        )
    return f"error=not_found; hint=运单号需以 SF 开头且足够长; tracking_no={no}"
