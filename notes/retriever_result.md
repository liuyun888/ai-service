# 05.05 Retriever 抽象 · 实跑记录

- query: `七天无理由退货需要什么条件？`
- top_k: `4`
- embedding: `BAAI/bge-small-zh-v1.5`

## STEP 1 · 单库

- #1  score=0.8124  source=return_policy.md  ## 七天无理由退货  签收后 **7 个自然日** 内，商品完好、配件齐全、不影响二次销售， 可申请无理由退货。运费由买家承担…
- #2  score=0.6433  source=hospital_visit.md  ## 退费说明  未做的检查项目可在 7 个工作日内到收费窗口申请退费，需出示缴费凭证。
- #3  score=0.5921  source=return_policy.md  ## 质量问题换货  签收超过 7 日后，若出现非人为质量问题，凭购买凭证申请换货或维修。 需提供订单号与故障描述。
- #4  score=0.5520  source=shipping_faq.md  ## 签收与验货  请当面验货后再签收。若外包装明显破损，可拒收并联系客服处理。

## STEP 2 · 缺 tenant

- `tenant_id required；禁止无租户查全库`

## STEP 3 · 租户隔离

### tenant_a

- #1  score=0.7673  source=return_policy.md tenant=tenant_a  ## 七天无理由退货  签收后 **7 个自然日** 内，商品完好、配件齐全，可申请无理由退货。 本政策仅适用于租户 A（Acm…
- #2  score=0.7028  source=return_policy.md tenant=tenant_a  ## 运费  无理由退货运费由买家承担。
- #3  score=0.5726  source=return_policy.md tenant=tenant_a  # 租户 A · 退货政策
### tenant_b

- #1  score=0.7239  source=return_policy.md tenant=tenant_b  ## 十五天无理由退货  签收后 **15 个自然日** 内，商品完好、配件齐全，可申请无理由退货。 本政策仅适用于租户 B（B…
- #2  score=0.6627  source=return_policy.md tenant=tenant_b  ## 运费  无理由退货运费由平台券补贴（活动期内）。
- #3  score=0.5726  source=return_policy.md tenant=tenant_b  # 租户 B · 退货政策

## 结论

- Retriever = 统一插头：`invoke(query) → list[Document]`。
- 适配器内部可换内存 / Milvus / 租户过滤，链代码下节课不用改。
- Document.metadata 至少保留 source、score；租户场景加 tenant_id。
