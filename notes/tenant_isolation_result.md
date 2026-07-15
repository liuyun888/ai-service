# 04.03 多库隔离 · 实跑记录

- Embedding：`BAAI/bge-small-zh-v1.5`
- 问题：无理由退货可以几天内申请？
- 硬隔离 Collection 名示例：`kb_tenant_a` / `kb_tenant_b`

## STEP 0 · 入库

- 总块数 `6`；tenant_a=3；tenant_b=3

## STEP 1 · 默认拒绝

- 空 `tenant_id` → `ValueError`（未查全库）

## STEP 2 · 分租户

- A top1: 0.7825  tenant_id=tenant_a  source=return_policy.md  chunk 1  [七天无理由退货] ## 七天无理由退货  签收后 **7 个自然日** 内，商品完好、配件齐全，可申请无理由退货。 本政策仅适用于租户 A（Acme 商城旗舰店）...
- B top1: 0.7869  tenant_id=tenant_b  source=return_policy.md  chunk 1  [十五天无理由退货] ## 十五天无理由退货  签收后 **15 个自然日** 内，商品完好、配件齐全，可申请无理由退货。 本政策仅适用于租户 B（Beta 奥莱专营...

## STEP 3 · 漏过滤

- topK 租户集合：`['tenant_a', 'tenant_b']`
- 结论：过滤必须写在检索 API，不能指望 Prompt。

## 选用策略（笔记自填）

- 本课验证：metadata 强制过滤可互不串库。
- 强合规场景应升级为多 Collection / 强分区。
