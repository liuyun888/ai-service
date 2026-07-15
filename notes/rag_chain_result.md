# 05.06 RAG Chain · 实跑记录

- USE_CHAT: `False`
- min_score: `0.58` top_k: `4`
- embedding: `BAAI/bge-small-zh-v1.5`
- provider: `openai`

## STEP 1 · format_docs

```text
[1] (source=return_policy.md) ## 七天无理由退货

签收后 **7 个自然日** 内，商品完好、配件齐全、不影响二次销售，
可申请无理由退货。运费由买家承担，具体以订单页规则为准。
[2] (source=hospital_visit.md) ## 退费说明

未做的检查项目可在 7 个工作日内到收费窗口申请退费，需出示缴费凭证。
[3] (source=return_policy.md) ## 质量问题换货

签收超过 7 日后，若出现非人为质量问题，凭购买凭证申请换货或维修。
需提供订单号与故障描述。
[4] (source=shipping_faq.md) ## 签收与验货

请当面验货后再签收。若外包装明显破损，可拒收并联系客服处理。
```

## STEP 2 · 库内题

- refused: `False` top1: `0.8123660700123901`
- sources: `['return_policy.md', 'hospital_visit.md', 'return_policy.md', 'shipping_faq.md']`
```text
(offline preview) 将根据以下资料生成作答：
[1] (source=return_policy.md) ## 七天无理由退货

签收后 **7 个自然日** 内，商品完好、配件齐全、不影响二次销售，
可申请无理由退货。运费由买家承担，具体以订单页规则为准。
[2] (source=hospital_visit.md) ## 退费说明

未做的检查项目可在 7 个工作日内到收费窗口申请退费，需出示缴费凭证。
[3] (source=return_policy.md) ## 质量问题换货

签收超过 7 日后，若出现非人为质量问题，凭购买凭证申请换货或维修。
需提供订单号与故障描述。
[4] (source=shipping_faq.md) ## 签收与验货

请当面验货后再签收。若外包装明显破损，可拒收并联系客服处理。
```

## STEP 3 · 拒答

- reason: `top1_score=0.5255418570990784 < min_score=0.58`
- top1: `0.5255418570990784`
```text
根据当前知识库资料，我无法确定这一点。你可以换个问法，或补充文档后再问。我不会编造具体数字、条款或承诺。
```

## STEP 4 · 离线另一问

- sources: `['course_enrollment.md', 'course_enrollment.md', 'course_enrollment.md', 'course_enrollment.md']`

## 结论

- LCEL RAG：question → Retriever → 闸门 → Prompt → Model。
- 拒答是硬短路：低相关不进 Generate，省钱且更安全。
- 有据回答应能从 sources / 文末引用看到文件名。
