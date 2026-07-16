# 11.04 知识库与护栏集成 · 实跑记录


## M11 自检

- [x] 11.01 业务助手 (`/v1/assistant/chat`)
- [x] 11.02 对话客服 (`/v1/cs/chat`)
- [x] 11.03 多步工作流 (`/v1/workflows/return/*`)
- [x] 11.04 知识库+护栏 (`/v1/kb/chat + /rag/ingest`)

## STEP 1 · ingest

- `{'ok': True, 'deleted': 0, 'inserted': 1, 'remain': 1, 'source': 'policy_unique_42.md', 'tenant_id': 'demo', 'path': '/Users/liuyunkai/Documents/workspace/AI从0到1/ai-service/samples/ingest_inbox/demo/policy_unique_42.md', 'strategy': 'heading'}`

## STEP 2 · 可问

- reply 含 `POLICY_UNIQUE_42`

## STEP 3 · 护栏

- guard_triggered=`True` reply=`我无法做出绝对承诺。请以订单页时效/书面政策为准，我可以帮你查询当前状态。`

## STEP 4 · 租户

- tenant-b ok=`False`

## STEP 5 · HTTP

- ingest=200 ask ok；guard_triggered=`True`；无令牌 401

## STEP 6 · curl

```bash
curl -s http://127.0.0.1:8091/v1/rag/ingest \
  -H 'X-Ingest-Token: dev-ingest-token' -H 'Content-Type: application/json' \
  -d '{"source":"policy_unique_42.md","tenant_id":"demo","text":"标记 POLICY_UNIQUE_42：7日内可退。"}'
curl -s http://127.0.0.1:8091/v1/kb/chat \
  -H 'X-Internal-Token: dev-internal-token' -H 'X-Tenant-Id: demo' \
  -H 'Content-Type: application/json' \
  -d '{"message":"POLICY_UNIQUE_42 怎么说？","session_id":"s1"}'
```
