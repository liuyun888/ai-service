# 04.04 上下游对接 ingest · 实跑记录

- tenant: `tenant_a`
- source: `return_policy.md`
- 问题：审核通过后几个工作日到账？

## STEP 1 · 鉴权

- 无 Token → `401`

## STEP 2 · 参数校验

- 空 text → `400` detail=`text required for this lesson（file_url 下节再接）`

## STEP 3 · 首次入库

- 响应：`{"ok": true, "deleted": 0, "inserted": 2, "remain": 2, "source": "return_policy.md", "tenant_id": "tenant_a", "path": "/Users/liuyunkai/Documents/workspace/AI从0到1/ai-service/samples/ingest_inbox/tenant_a/return_policy.md", "strategy": "heading"}`
- 检索 top1：0.8316  tenant_id=tenant_a  source=return_policy.md  chunk 1  [到账时效] ## 到账时效  审核通过后 **7 个工作日** 到账，节假日顺延。

## STEP 4 · 幂等改版

- 响应：`{"ok": true, "deleted": 2, "inserted": 2, "remain": 2, "source": "return_policy.md", "tenant_id": "tenant_a", "path": "/Users/liuyunkai/Documents/workspace/AI从0到1/ai-service/samples/ingest_inbox/tenant_a/return_policy.md", "strategy": "heading"}`
- 检索 top1：0.8395  tenant_id=tenant_a  source=return_policy.md  chunk 1  [到账时效] ## 到账时效  审核通过后 **3 个工作日** 到账，节假日顺延。

## curl 对照（需先起服务）

```bash
uvicorn app.main:app --port 8001
curl -s -X POST http://127.0.0.1:8001/rag/ingest \
  -H 'Content-Type: application/json' \
  -H 'X-Ingest-Token: dev-ingest-token' \
  -d '{"source":"return_policy.md","tenant_id":"tenant_a","text":"审核通过后 **3** 个工作日到账。"}'
```
