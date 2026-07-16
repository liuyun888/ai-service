# app/tools/inventory.py
"""课次 05.07 · 查库存 Tool（mock 目录，不接真实仓配）。

直觉：
- Tool = 说明书（name/description/参数）+ 真正干活的函数
- 模型靠描述决定「调不调、怎么调」
- 出错时返回可读字符串，不要把进程打崩（除非真致命）
"""

from __future__ import annotations

from langchain_core.tools import tool

# mock 库存表：SKU → 可用库存（0 = 无货但仍「查到了」）
MOCK_CATALOG: dict[str, int] = {
    "EARPHONE-PRO-BK": 12,
    "EARPHONE-PRO-WH": 0,
    "CABLE-USB-C": 56,
}


@tool
def get_inventory(sku: str) -> str:
    """查询商品 SKU 的库存数量（只读）。

    何时用：用户问「还有货吗 / 库存多少 / 黑色还有没有」且能对应到 sku。
    何时不用：闲聊、问政策条款（应走文档检索）、改库存/下单（本课无写权限）。

    参数:
        sku: 商品编码，例如 EARPHONE-PRO-BK

    返回:
        成功: 「sku=..., stock=N」；未知 sku: 「not_found」
    """
    key = (sku or "").strip().upper()
    if not key:
        return "error: sku 不能为空"
    if key not in MOCK_CATALOG:
        return "not_found"
    return f"sku={key}, stock={MOCK_CATALOG[key]}"


@tool
def get_shipment(tracking_no: str) -> str:
    """查询运单当前状态（只读，mock）。

    对照示例：与 get_inventory 同构——换参数名与 mock 表即可。
    何时用：用户给出运单号问「到哪了」。
    何时不用：没有运单号时硬猜；退款/改址等写入操作。

    参数:
        tracking_no: 运单号，例如 SF123456

    返回:
        成功: 「tracking_no=..., status=...」
        失败: 「not_found」或「error: tracking_no 不能为空」
    """
    no = (tracking_no or "").strip().upper()
    mock = {
        "SF123456": "已发货，转运中心",
        "YT998877": "派送中",
    }
    if not no:
        return "error: tracking_no 不能为空"
    if no not in mock:
        return "not_found"
    return f"tracking_no={no}, status={mock[no]}"


@tool
def get_order_status(tracking_no: str) -> str:
    """查询订单物流状态（只读）；客服配置里常用此名，底层同 get_shipment。

    参数:
        tracking_no: 运单/订单物流号，例如 SF123456
    """
    return get_shipment.invoke({"tracking_no": tracking_no})
