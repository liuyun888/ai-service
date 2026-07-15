# 03.06 上下文注入 · 端到端演示记录

- 问题：七天无理由退货需要什么条件？
- top_k：4
- Embedding：`BAAI/bge-small-zh-v1.5`
- Chat：`astron-code-latest`
- topK sources：['return_policy.md', 'hospital_visit.md', 'return_policy.md', 'shipping_faq.md']
- 期望 source 命中：是

## Prompt

```text
你只能根据【资料】回答。
资料不足时说「根据现有资料无法确定」，不要编造。
回答末尾列出引用的 source（文件名即可）。

【资料】
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

【问题】
七天无理由退货需要什么条件？
```

## Answer

七天无理由退货需要满足以下条件：
1. 在签收后7个自然日内；
2. 商品完好、配件齐全、不影响二次销售；
3. 运费由买家承担（具体以订单页规则为准）。

source: return_policy.md
