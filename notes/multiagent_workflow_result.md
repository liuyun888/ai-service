# 07.07 多智能体与多步工作流 · 实跑记录


```text
intake → gather_evidence → assess_risk
  → human_review(HITL) | execute_or_skip → draft_reply
```

## STEP 1 · 角色

| 角色 | 节点 | 职责 |
|------|------|------|
| 受理员 | intake | 登记诉求 → intake_notes |
| 核查员 | gather_evidence | 订单 mock + 政策证据 → evidence |
| 风控员 | assess_risk | 规则打 risk_level |
| 审核员 | human_review | 高风险 HITL interrupt |
| 执行员 | execute_or_skip | 开单 mock / 驳回 |
| 话术员 | draft_reply | 只基于 State 写 user_message |

- 门禁: assess_risk → human_review | execute_or_skip（按 risk_level）
- 门禁: human_review 内 interrupt（高风险人工门禁）

## STEP 2 · 低风险

```json
{
  "case_id": "R-1",
  "decision": "auto_pass",
  "risk_level": "low",
  "action_result": "mock_return_created",
  "user_message": "已根据证据处理。结果=mock_return_created。证据=order_status=delivered; policy_hit=[return_window] 退货时效: 自签收之日起 7 天内可申请无理由退货；商品需未损坏、配件齐全。 | [return_freight] 退货运费: 质量问题由商家承担退货运费；无理由退货运费由买家承担。。（decision=auto_pass）",
  "evidence": [
    "order_status=delivered",
    "policy_hit=[return_window] 退货时效: 自签收之日起 7 天内可申请无理由退货；商品需未损坏、配件齐全。 | [return_freight] 退货运费: 质量问题由商家承担退货运费；无理由退货运费由买家承担。"
  ],
  "role_handoff": [
    "受理员",
    "核查员",
    "风控员",
    "执行员",
    "话术员"
  ],
  "path": [
    "intake",
    "gather_evidence",
    "assess_risk",
    "execute_or_skip",
    "draft_reply"
  ]
}
```

## STEP 3 · 高风险暂停

- next: `('human_review',)`
- path: `['intake', 'gather_evidence', 'assess_risk']`

## STEP 4 · 批准

```json
{
  "case_id": "R-2",
  "decision": "approved",
  "risk_level": "high",
  "action_result": "mock_return_created",
  "user_message": "已根据证据处理。结果=mock_return_created。证据=order_status=delivered; policy=7_day_unopened(mock_default)。（decision=approved）",
  "evidence": [
    "order_status=delivered",
    "policy=7_day_unopened(mock_default)"
  ],
  "role_handoff": [
    "受理员",
    "核查员",
    "风控员",
    "审核员",
    "执行员",
    "话术员"
  ],
  "path": [
    "intake",
    "gather_evidence",
    "assess_risk",
    "human_review",
    "execute_or_skip",
    "draft_reply"
  ]
}
```

## STEP 5 · 驳回

- `{'case_id': 'R-3', 'decision': 'rejected', 'risk_level': 'high', 'action_result': 'rejected', 'user_message': '审核未通过，未创建退货单。已参考证据：order_status=delivered; policy=7_day_unopened(mock_default)', 'evidence': ['order_status=delivered', 'policy=7_day_unopened(mock_default)'], 'role_handoff': ['受理员', '核查员', '风控员', '审核员', '执行员', '话术员'], 'path': ['intake', 'gather_evidence', 'assess_risk', 'human_review', 'execute_or_skip', 'draft_reply']}`

## STEP 6 · 对照

- 预问诊: 主诉采集→红旗规则→医生确认→就诊建议
- 材料预审: 收件→缺件检测→人工抽检→通知补正

## 结论

- 多智能体在工程上 = 多角色节点 + State 交接 + 图门禁。
- M07 里程碑：多步图可跑，高风险可暂停，结果可结构化交付。
- 下一模块：Harness / Deep Agents 运行时外壳。
