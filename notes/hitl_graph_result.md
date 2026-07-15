# 07.06 HITL（图内）· 实跑记录


```text
validate_order → prepare_summary → human_review
  → execute_refund | reject_notify
```

## STEP 1 · 暂停

- next: `('human_review',)`
- path: `['validate_order', 'prepare_summary']`
- interrupt: `{'question': '是否批准执行退货写入？', 'order_id': 'ORD-C300', 'summary': '拟对订单 ORD-C300 执行退货退款（mock 摘要，尚未执行任何写入）。', 'order_ok': True}`

## STEP 2 · 批准

- path: `['validate_order', 'prepare_summary', 'human_review', 'execute_refund']`
- result: 已执行退货处理（mock）order=ORD-A100; by=ops_01

## STEP 3 · 驳回

- path: `['validate_order', 'prepare_summary', 'human_review', 'reject_notify']`
- result: 已驳回，未执行任何写入

## STEP 4 · thread_id

- resume 必须与 pause 使用同一 `thread_id`

## STEP 5 · BFF 契约

- 第一次响应：status=interrupted + thread_id + summary 摘要
- 人工在工单台批准/驳回
- BFF 用同一 thread_id 调 resume（Command(resume=...)）
- 写入类 Tool 只能在 approved 之后的节点

## 结论

- 图内 interrupt 把 HITL 做成一等公民；配合 Checkpointer 可跨天审批。
- 写入类动作锁在批准之后；驳回要响亮，不要静默。
- 下一课：多智能体 + 多步工作流端到端。
