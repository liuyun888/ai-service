# 11.02 对话客服集成 · 实跑记录


## 配置

- `/Users/liuyunkai/Documents/workspace/AI从0到1/ai-service/app/agents/cs_config.yaml` name=`customer_service`

## STEP 1 · 物流

- action=`reply` reply=`物流状态（Tool）：tracking_no=SF123456, status=已发货，转运中心。以上来自查询，非估算。`

## STEP 2 · 记忆

- tracking=`SF123456`

## STEP 3 · handoff

- reason=`complaint`
- summary:

```
- session_id: cs-ho
- 用户诉求: 你们太坑了要投诉转人工
- tool_fails: 0
- 最近轨迹: （尚无 Tool 调用）
```

## STEP 4 · 规则

- tool_fail=`{'handoff': True, 'reason': 'tool_fail'}` keyword_转人工=`user_requested`

## STEP 5 · HTTP

- ship action=`reply`
- handoff action=`handoff` summary 非空
- 无令牌 → `401`

## STEP 6 · curl

```bash
curl -s http://127.0.0.1:8091/v1/cs/chat \
  -H 'Content-Type: application/json' \
  -H 'X-Internal-Token: dev-internal-token' \
  -H 'X-Tenant-Id: demo' \
  -d '{"message":"我要投诉转人工","session_id":"s1"}'
```
