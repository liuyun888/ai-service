# 07.04 条件路由 · 实跑记录


```text
classify → product → retrieve → generate
         → order   → order_tool → generate
         → other   → clarify
```

## STEP 1 · 真值表

| query | intent | route |
|-------|--------|-------|
| 这款鞋防水吗 | product | retrieve |
| 耳机质保多久 | product | retrieve |
| 订单 10086 到哪了 | order | order_tool |
| 运单 SF123456 到哪了 | order | order_tool |
| 你好 | other | clarify |
| 今天心情怎么样 | other | clarify |

## STEP 2 · 兜底

- 非法 intent → `clarify`

## STEP 3 · 三路

### product

- path: `['classify', 'retrieve', 'generate']`
- intent: `product`
- answer: [检索] [return_window] 退货时效: 自签收之日起 7 天内可申请无理由退货；商品需未损坏、配件齐全。 | [return_freight] 退货运费: 质量问题由商家承担退货运费；无理由退货运费由买家承担。

### order

- path: `['classify', 'order_tool', 'generate']`
- intent: `order`
- answer: [Tool] tracking_no=SF123456, status=已发货，转运中心

### other

- path: `['classify', 'clarify']`
- intent: `other`
- answer: 请说明是商品/政策咨询，还是订单/物流查询？（可带规格关键词或运单号）

## STEP 4 · 课文样例

- `这款鞋防水吗` → `['classify', 'retrieve', 'generate']` / `[检索] [检索空] 未命中「这款鞋防水吗」相关资料`
- `订单 10086 到哪了` → `['classify', 'order_tool', 'generate']` / `[Tool] tracking_no=SF123456, status=已发货，转运中心`
- `你好` → `['classify', 'clarify']` / `请说明是商品/政策咨询，还是订单/物流查询？（可带规格关键词或运单号）`

## STEP 5 · 心智

- 图路由：宏观走哪条业务链（product/order/other）
- Agent 选 Tool：链内局部探索（一节点内 Loop）
- 不要用「挂 20 个 Tool」代替两条清晰业务边

## 结论

- 条件边返回节点名；intent 落 State 便于 Trace。
- 换 LLM 分类时保留 route_after_classify 接口。
- 下一课：Checkpointer + thread_id 续跑。
