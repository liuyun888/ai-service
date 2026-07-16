# 11.03 多步工作流集成 · 实跑记录


## 角色

- 受理员 (`intake`): 登记诉求 → intake_notes
- 核查员 (`gather_evidence`): 订单 mock + 政策证据 → evidence
- 风控员 (`assess_risk`): 规则打 risk_level
- 审核员 (`human_review`): 高风险 HITL interrupt
- 执行员 (`execute_or_skip`): 开单 mock / 驳回
- 话术员 (`draft_reply`): 只基于 State 写 user_message

## STEP 1 · 低风险

- `{'case_id': 'R-low-1103', 'status': 'completed', 'risk_level': 'low', 'evidence': ['order_status=delivered', 'policy_hit=[return_window] 退货时效: 自签收之日起 7 天内可申请无理由退货；商品需未损坏、配件齐全。 | [return_freight] 退货运费: 质量问题由商家承担退货运费；无理由退货运费由买家承担。'], 'action_result': 'mock_return_created', 'user_message': '已根据证据处理。结果=mock_return_created。证据=order_status=delivered; policy_hit=[return_window] 退货时效: 自签收之日起 7 天内可申请无理由退货；商品需未损坏、配件齐全。 | [return_freight] 退货运费: 质量问题由商家承担退货运费；无理由退货运费由买家承担。。（decision=auto_pass）', 'decision': 'auto_pass', 'role_handoff': ['受理员', '核查员', '风控员', '执行员', '话术员'], 'path': ['intake', 'gather_evidence', 'assess_risk', 'execute_or_skip', 'draft_reply'], 'interrupted': False, 'interrupt': None, 'ok': True, 'tenant_id': 'demo'}`

## STEP 2 · 高风险暂停

- status=`waiting_human`

## STEP 3 · 批准

- `completed` / `mock_return_created`

## STEP 4 · 驳回

- `rejected`

## STEP 5 · HTTP

- low=`completed` high=`waiting_human` resume=`completed`
- 无令牌 → `401`

## STEP 6 · curl

```bash
curl -s http://127.0.0.1:8091/v1/workflows/return/start \
  -H 'X-Internal-Token: dev-internal-token' -H 'X-Tenant-Id: demo' \
  -H 'Content-Type: application/json' \
  -d '{"case_id":"R-curl","user_request":"破损要全额退款"}'
curl -s http://127.0.0.1:8091/v1/workflows/return/resume \
  -H 'X-Internal-Token: dev-internal-token' -H 'X-Tenant-Id: demo' \
  -H 'Content-Type: application/json' \
  -d '{"case_id":"R-curl","approved":true,"reviewer":"ops_01"}'
```
