# 10.04 ai-service 内部鉴权 · 实跑记录


## STEP 1

- 无令牌 → `401`

## STEP 2

- 缺租户 → `400`

## STEP 3

- echo: `{'tenant_id': 'tenant-a', 'user_id': 'u-alice', 'model_id': 'default', 'request_id': 'req-demo-001'}`

## STEP 4

- done: `{'type': 'done', 'tenant_id': 'tenant-a', 'user_id': 'u-alice', 'model_id': 'default', 'request_id': 'req-demo-001'}`
