# 07.01 图 vs 单 Agent · 实跑记录


## 选型清单（勾选 ≥2 再上图）

- `staged`: 存在明确业务阶段（受理→审核→通知），不能乱跳
- `hitl`: 需要人工确认后才能继续
- `resume`: 流程可能中断数分钟～数天再续跑
- `routable`: 不同意图必须走不同子系统，且要可测
- `audit`: 需要多角色分工且交接状态要审计

## STEP 2 · 选型表

| 场景 | 命中条数 | 结论 | 说明 |
|------|----------|------|------|
| 包装尺寸 FAQ | 0 | Agent | 无线上图硬需求：单 Agent Loop 足够 |
| 查实时库存 | 0 | Agent | 无线上图硬需求：单 Agent Loop 足够 |
| 退货审核（校验→判责→人确认→开单） | 5 | Graph | 命中 5 条上图信号（≥2） |
| 请假审批流 | 4 | Graph | 命中 4 条上图信号（≥2） |
| 异常理赔确认 | 3 | Graph | 命中 3 条上图信号（≥2） |

## STEP 3 · 单 Agent

- FAQ path: `['think', 'act:search_knowledge', 'final']`
- FAQ answer: 根据政策检索：[return_window] 退货时效: 自签收之日起 7 天内可申请无理由退货；商品需未损坏、配件齐全。 | [return_freight] 退货运费: 质量问题由商家承担退货运费；无理由退货运费由买家承担。
- 库存: 查过了：sku=EARPHONE-PRO-BK, stock=12

## STEP 4 · 状态图

- path: `['classify', 'validate_order', 'await_human', 'draft_ticket']`
- needs_human: True
- answer: 订单 ORD12345 校验=通过；已暂停，待人工确认责权后再开单。 → 已生成草稿 TICKET-DRAFT:ORD12345（未真正退款）。

## STEP 5 · 对照

- Agent FAQ path: `['think', 'act:search_knowledge', 'final']`
- Graph return path: `['classify', 'validate_order', 'await_human', 'draft_ticket']`
- 政策口语误走轻量图: `['classify', 'faq_answer']` （能跑 ≠ 选型该上图）

## STEP 6 · 反例

- 只有查库存数字、无线上审批/暂停 → 单 Agent，不上图

## 结论

- 图管宏观路径；Loop 管局部探索——Loop 不会消失。
- ≥2 条信号再上图；先跑通单 Agent 里程碑。
- 下一课：最小 Hello StateGraph（定义 State / compile / invoke）。
