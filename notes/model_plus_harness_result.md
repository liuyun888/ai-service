# 08.01 Agent = Model + Harness · 实跑记录


## 公式

`Agent ≈ Model + Harness`；Framework 管编排，Harness 管运营外壳。


## STEP 1 · 目录

- `app/harness/middleware` exists=True
- `app/harness/context` exists=True
- `app/harness/memory` exists=True
- `app/harness/skills` exists=True

## STEP 2 · 三层

| 层 | 职责 | 例子 | 不该管 |
|----|------|------|--------|
| Model | 推理、选 Tool、生成文本 | Chat 模型；本课用模板代替 | 不负责限流/租户鉴权 |
| Framework | 图、Chain、消息协议、Tool 绑定 | LangGraph / LangChain | 不等于已经有运营外壳 |
| Harness | 中间件、上下文策略、安全门、观测 | app/harness/（鉴权、护栏、Trace、截断） | 不塞具体业务 if-else 全文 |

## STEP 3 · 对照

- bare: 根据政策：[return_window] 退货时效: 自签收之日起 7 天内可申请无理由退货；商品需未损坏、配件齐全。 | [return_freight] 退货运费: 质量问题由商家承担退货运费；无理由退货运费由买家承担。（以上来自检索 Observation，非估算。）
- harness: 根据政策：[return_window] 退货时效: 自签收之日起 7 天内可申请无理由退货；商品需未损坏、配件齐全。 | [return_freight] 退货运费: 质量问题由商家承担退货运费；无理由退货运费由买家承担。（以上来自检索 Observation，非估算。）
- harness trace: `[{'name': 'auth.tenant', 'detail': 'ok'}, {'name': 'context.truncate', 'detail': 'truncated=False; len=6'}, {'name': 'tool.whitelist', 'detail': 'ok'}, {'name': 'tool.search_knowledge', 'detail': '[return_window] 退货时效: 自签收之日起 7 天内可申请无理由退货；商品需未损坏、配件齐全。 | [return_freight] 退货运费: 质量问题由商家承担退货运费；无理由退货运费由买家承担。'}, {'name': 'guard.output', 'detail': 'ok=True; hit=-'}]`

## STEP 4 · 拦截

- bad tenant: 无权访问：租户校验失败。
- promise blocked: 我不能做出该类绝对承诺或诊断式结论。我可以说明通常规则，或帮你转人工确认。请补充订单号/诉求要点。

## STEP 5 · 缺口表

| 能力 | 现在在哪一层？ | 是否应上移到 Harness？ |
|------|----------------|------------------------|
| max_steps | Framework/Loop（M06 run_tao_loop / agent max_steps） | 可：统一默认值与超限兜底话术 |
| Tool 白名单 | Harness middleware/safety.py（06.06 已落） | 已在 Harness |
| 日志/Trace | 脚本 print / 部分笔记 | 是：统一 Trace 事件结构 |
| 上下文截断 | 分散或缺失 | 是：context/truncate（本课示意） |
| 输出承诺护栏 | Harness guard_output | 已在 Harness |
| 租户鉴权 | 本课 shell.ensure_tenant | 是：调用前钩子 |

## 结论

- 模型可换，Harness 要稳；图/Loop 跑在外壳里，外壳不替代图。
- Demo→生产：同一答案，可运营性靠 Harness。
- 下一课：五维工程模型系统扫缺口。
