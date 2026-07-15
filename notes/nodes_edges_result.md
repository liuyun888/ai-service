# 07.03 节点与边 · 实跑记录


- USE_KNOWLEDGE_TOOL=True
- 拓扑: retrieve → analyze → generate（普通边）

## STEP 1 · 职责

| 节点 | 职责 | 写入字段 |
|------|------|----------|
| retrieve | 按 query 取 docs；空查询/失败写 error，不抛崩 | docs, error, path |
| analyze | 判断 docs 是否够用；写 summary 或 need_clarify | summary, need_clarify, path |
| generate | 根据 summary / need_clarify 拼 answer | answer, path |

## STEP 2 · 边

- START → retrieve
- retrieve → analyze
- analyze → generate
- generate → END

## STEP 3 · 幸福路径

- path: `['retrieve', 'analyze', 'generate']`
- docs: `['[return_window] 退货时效: 自签收之日起 7 天内可申请无理由退货；商品需未损坏、配件齐全。', '[return_freight] 退货运费: 质量问题由商家承担退货运费；无理由退货运费由买家承担。']`
- answer: 基于资料：[return_window] 退货时效: 自签收之日起 7 天内可申请无理由退货；商品需未损坏、配件齐全。 | [return_freight] 退货运费: 质量问题由商家承担退货运费；无理由退货运费由买家承担。

## STEP 4 · 空资料

- need_clarify: True
- answer: （资料不足）未能检索到相关片段。请补充更具体的问题（例如退货天数、运费规则），或转人工。

## STEP 5 · PartialState

- retrieve → `['docs', 'error', 'path']`
- analyze → `['need_clarify', 'path', 'summary']`
- generate → `['answer', 'path']`

## STEP 6 · 可替换

- `retrieve` 内标注「可替换为真实 Retriever / search_knowledge」
- 质保样例 answer: 基于资料：[warranty] 质保说明: 耳机主机质保 12 个月；人为进水、私自拆机不在保修范围。

## 结论

- 宏观路径用边钉死；局部探索可放在单节点内 Loop。
- need_clarify 已写入 State，下一课用条件边分流。
