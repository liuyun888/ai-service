# 11.01 业务助手集成 · 实跑记录


## STEP 1 · 组合问

- Q: `防水款还有吗？退货多久？`
- reply:

```
库存（Tool）：防水款对应 `EARPHONE-PRO-BK`，现货 stock=12。（证据：get_inventory → sku=EARPHONE-PRO-BK, stock=12）
退货规则（RAG）：[return_window] 退货时效: 自签收之日起 7 天内可申请无理由退货；商品需未损坏、配件齐全。 | [return_freight] 退货运费: 质量问题由商家承担退货运费；无理由退货运费由买家承担。 （证据路径/条目：`manual/return_policy.md`；数值类以 Tool 为准，条款以文档为准。）
```

- evidence: `{'doc_paths': ['case/complaints_week.md', 'case/ticket-10086/notes.md', 'manual/return_policy.md', 'manual/shipping.md'], 'doc_snippets': ['划再执行」。真实环境请换成导出工单。  ## Top 问题  1. **已拆封与七天无理由口径冲突**（42 单）      用户看到营销页「七天无理由」，拆箱试听后被拒；客服话术不一致。  2. *', '注  - 用户：想退耳机，外包装已拆、耳机试听约 10 分钟。 - 诉求：要求「七天无理由全额退」。 - 暂定处理：对照 `manual/return_policy.md` §2.1 —— 通常不支持', '策适用于自营平台标价商品（不含第三方代发、预售特批与虚拟商品）。  ## 2. 七天无理由退货  自签收之日起七个自然日内，符合下列条件可申请无理由退货：  1. 商品及包装保持完好，不影响二次销售；', '签并拍摄面单与破损处。  ## 与退货的关系  物流破损走「质量问题退换」，不按七天无理由卡「已拆封」。详见 `manual/return_policy.md` 第 3 章。'], 'tool_observations': ['case/complaints_week.md :: 划再执行」。真实环境请换成导出工单。  ## Top 问题  1. **已拆封与七天无理由口径冲突**（42 单）      用户看到营销页「七天无理由」，拆箱试听后被拒；客服话术不一致。  2. *', 'case/ticket-10086/notes.md :: 注  - 用户：想退耳机，外包装已拆、耳机试听约 10 分钟。 - 诉求：要求「七天无理由全额退」。 - 暂定处理：对照 `manual/return_policy.md` §2.1 —— 通常不支持', 'manual/return_policy.md :: 策适用于自营平台标价商品（不含第三方代发、预售特批与虚拟商品）。  ## 2. 七天无理由退货  自签收之日起七个自然日内，符合下列条件可申请无理由退货：  1. 商品及包装保持完好，不影响二次销售；', 'manual/shipping.md :: 签并拍摄面单与破损处。  ## 与退货的关系  物流破损走「质量问题退换」，不按七天无理由卡「已拆封」。详见 `manual/return_policy.md` 第 3 章。', '[return_window] 退货时效: 自签收之日起 7 天内可申请无理由退货；商品需未损坏、配件齐全。 | [return_freight] 退货运费: 质量问题由商家承担退货运费；无理由退货运费由买家承担。', 'sku=EARPHONE-PRO-BK, stock=12'], 'stock': 12, 'sku': 'EARPHONE-PRO-BK', 'policy_ids': ['return_window']}`

## STEP 2 · 租户

- `error=forbidden_tenant; hint='evil' 不在允许列表`

## STEP 3 · 只读

- `error=hitl_required; hint=高风险动作 'create_refund' 必须人工确认，禁止自动执行`

## STEP 4 · HTTP

- status=200 ok=`True`
- 无令牌 → `401`

## STEP 5 · curl

```bash
curl -s http://127.0.0.1:8091/v1/assistant/chat \
  -H 'Content-Type: application/json' \
  -H 'X-Internal-Token: dev-internal-token' \
  -H 'X-Tenant-Id: demo' \
  -d '{"message":"防水款还有吗？退货多久？","session_id":"s1"}'
```
