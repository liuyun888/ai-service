# 09.04 客户端接入与选型集成 · 实跑记录


## STEP 1 · Cursor 配置

- `/Users/liuyunkai/Documents/workspace/AI从0到1/ai-service/notes/cursor_mcp_ai_service_tools.json`

## STEP 2 · 选型

- **进程内函数**：生产热路径、低延迟 Agent/Harness；注意：与 app 同发版；改 Tool 要发应用
- **MCP**：IDE 调试、多 Client 复用同一工具箱、本地资源；注意：stdio 生命周期、版本与 Client 协同；勿为统一强行上生产热路径
- **REST**：多语言服务、公网/网关、非模型调用方；注意：自建鉴权与 OpenAPI 文档；粒度按 HTTP 资源设计

## STEP 3 · 场景

- Cursor 里调试 get_inventory → **MCP**（开发期发现+试调最快；与生产函数同源）
- 生产 Harness 热路径查库存 → **进程内函数**（少一次进程跳；Harness 直接 import 纯函数）
- 给外部网关 OpenAPI 暴露库存 → **REST**（非模型调用方 / 跨语言，走 HTTP 更合适）

## STEP 4 · 双入口

- inprocess: `{"sku": "SHOE-RED-42", "qty": 7, "warehouse": "华东一仓"}`
- mcp: `{"sku": "SHOE-RED-42", "qty": 7, "warehouse": "华东一仓"}`
- rest: `{'method': 'GET', 'path': '/api/inventory/SHOE-RED-42', 'status': 200, 'body': '{"sku": "SHOE-RED-42", "qty": 7, "warehouse": "华东一仓"}'}`
- 三入口共用 tools_inventory；生产优先进程内，IDE 用 MCP，网关用 REST

## STEP 5 · Harness

- 开发调试走 MCP，生产热路径进程内直连同一 tools_*.py

## STEP 6 · 文档与安全

- README: `/Users/liuyunkai/Documents/workspace/AI从0到1/ai-service/app/mcp/README.md`
- no_dup: `{'server_imports_tools': True, 'mock_db_only_in_tools': True, 'ok': True}`
- MCP Server ≈ 高权限插件: 能读本地/内网的 Tool 默认只读；敏感目录拒绝
- 密钥: 不要把生产密钥塞进 MCP 配置「反正本机」；Tool 内做租户校验
- 写入类 Tool: 默认不进 MCP；若暴露必须 HITL / 鉴权（见 M07）
- 本课工具箱: search_docs / get_inventory / get_shipment 均为只读
