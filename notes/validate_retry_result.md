# 12.02 校验与失败重试 · 验收笔记

## 非法样例
```json
{
  "invoice_no": "24442000001234567890",
  "date": "2026-03-15",
  "amount": "12.00元",
  "seller_name": "示例科技有限公司"
}
```
error: `amount: Value error, amount 须为数字，不要带单位或中文`

## 重试修复
```json
{
  "status": "ok",
  "attempts": 2,
  "wrote_db": true,
  "amount": 12.0
}
```

## need_human
```json
{
  "status": "need_human",
  "attempts": 3,
  "wrote_db": false,
  "last_error": "amount: Value error, amount 须为数字，不要带单位或中文"
}
```

write_blocked_on_bad=True

SUMMARY: validate_retry 验收通过
