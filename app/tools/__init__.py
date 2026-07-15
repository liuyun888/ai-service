# app/tools/__init__.py
"""业务 Tool 包：给 Agent / MCP 复用的只读查询函数。

05.07 起：inventory.get_inventory / get_shipment
"""

from app.tools.inventory import get_inventory, get_shipment

__all__ = ["get_inventory", "get_shipment"]
