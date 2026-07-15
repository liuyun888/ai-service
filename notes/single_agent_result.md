# 06.04 单 Agent 落地 · 实跑记录


- USE_CHAT=0
- Tools: `get_inventory` / `get_shipment`（业务状态）+ `search_knowledge`（知识检索）
- HTTP: `POST /agent/chat`

## STEP 0 · search_knowledge

- `[return_window] 退货时效: 自签收之日起 7 天内可申请无理由退货；商品需未损坏、配件齐全。 | [return_freight] 退货运费: 质量问题由商家承担退货运费；无理由退货运费由买家承担。`

## STEP 1 · 只问库存

- trace: `[{'tool': 'get_inventory', 'args': {'sku': 'EARPHONE-PRO-BK'}, 'observation': 'sku=EARPHONE-PRO-BK, stock=12'}]`
- classes: ['业务状态']
- reply: 库存查询结果：sku=EARPHONE-PRO-BK, stock=12（数字来自工具，非估算）。 以上均基于 Tool Observation，未编造业务状态。

## STEP 2 · 组合问

- trace: `[{'tool': 'get_inventory', 'args': {'sku': 'EARPHONE-PRO-BK'}, 'observation': 'sku=EARPHONE-PRO-BK, stock=12'}, {'tool': 'search_knowledge', 'args': {'query': '黑色 Pro 还有货吗？退货几天内可以？'}, 'observation': '[return_window] 退货时效: 自签收之日起 7 天内可申请无理由退货；商品需未损坏、配件齐全。 | [return_freight] 退货运费: 质量问题由商家承担退货运费；无理由退货运费由买家承担。'}]`
- classes: ['业务状态', '知识检索']
- reply: 库存查询结果：sku=EARPHONE-PRO-BK, stock=12（数字来自工具，非估算）。 政策检索结果：[return_window] 退货时效: 自签收之日起 7 天内可申请无理由退货；商品需未损坏、配件齐全。 | [return_freight] 退货运费: 质量问题由商家承担退货运费；无理由退货运费由买家承担。 以上均基于 Tool Observation，未编造业务状态。

## STEP 3 · 无关拒答

- trace: `[]`
- reply: 这个问题超出只读客服范围（库存/运单/售后政策）。我没有查询业务系统。请换库存、退货政策或运单相关问题。

## STEP 4 · 多轮记忆

- turn2 trace: `[{'tool': 'get_inventory', 'args': {'sku': 'EARPHONE-PRO-BK'}, 'observation': 'sku=EARPHONE-PRO-BK, stock=12'}]`
- turn2 reply: 库存查询结果：sku=EARPHONE-PRO-BK, stock=12（数字来自工具，非估算）。 以上均基于 Tool Observation，未编造业务状态。

## STEP 5 · HTTP

- status: 200
- tool_classes: ['业务状态', '知识检索']
- reply: 库存查询结果：sku=EARPHONE-PRO-BK, stock=12（数字来自工具，非估算）。 政策检索结果：[return_window] 退货时效: 自签收之日起 7 天内可申请无理由退货；商品需未损坏、配件齐全。 | [return_freight] 退货运费: 质量问题由商家承担退货运费；无理由退货运费由买家承担。 以上均基于 Tool Observation，未编造业务状态。

## 结论

- 单 Agent = System + ≥2 类 Tool + Loop 限制 +（可选）session 记忆。
- 组合问必须能在 trace 里看到两类工具；回答拴在 Observation 上。
- 下一步（06.05）回炉 Tool 粒度、幂等与错误返回。
