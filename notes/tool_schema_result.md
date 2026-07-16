# 09.03 用 Schema 定义 Tool · 实跑记录


## STEP 1 · 好坏对照

- bad: `{'name': 'do', 'description': '做事', 'params': 'data: any', 'why_bad': '模型不知道何时调、怎么传、错了怎么办'}`
- good: `{'name': 'get_inventory', 'description': '按 SKU 查询可用库存；不要用于下单。SKU 需含颜色后缀。', 'params': 'sku: string (required)', 'returns': 'JSON {sku, qty, warehouse} 或 error=...', 'why_good': '何时用/不用、类型、例子、错误可回灌都写清'}`

## STEP 2 · 分层

- plain: `{"sku": "SHOE-RED-42", "qty": 7, "warehouse": "华东一仓"}`
- 业务仍是 tools_inventory.get_inventory；MCP 只是壳

## STEP 3 · list Schema

- tools: `['search_docs', 'get_inventory', 'get_shipment']`
- **search_docs**: 按关键词搜索知识库；不要用于写入或删改文件。适合找政策/投诉摘要片段。
  - params: `{'query': '搜索关键词，如「已拆封」；不要传整段文章'}`
- **get_inventory**: 按 SKU 查询可用库存；不要用于下单或改库存。返回短 JSON {sku,qty,warehouse}。
  - params: `{'sku': 'SKU，须含颜色尺码后缀，示例 SHOE-RED-42'}`
- **get_shipment**: 按运单号查询物流状态；不要用于改地址或拦截件。返回短 JSON 或 error=。
  - params: `{'tracking_no': '运单号，示例 SF1234567890'}`

## STEP 4 · 成功 call

- input: sku=SHOE-RED-42
- output: `{"sku": "SHOE-RED-42", "qty": 7, "warehouse": "华东一仓"}`
- shipment: `{"tracking_no": "SF1234567890", "status": "in_transit", "last_hub": "杭州转运中心"}`

## STEP 5 · 错误 call

- input: sku=NO-SUCH-SKU
- output: `error=not_found; hint=检查 SKU 是否含颜色尺码后缀; sku=NO-SUCH-SKU; known=['BAG-BLU-M', 'SHOE-BLK-41', 'SHOE-RED-42']`

## STEP 6 · unit

- `{'ok_qty': 7, 'bad_soft': True, 'empty_soft': True, 'ship_ok': True, 'layered': True}`
