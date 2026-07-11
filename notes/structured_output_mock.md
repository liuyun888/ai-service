# 结构化输出造数据演示

## 合格 JSON

```json
{
  "items": [
    {
      "name": "城际降噪 Pro",
      "reason": "降噪标注通勤级且在预算内",
      "score": 0.88
    },
    {
      "name": "轻听 Air",
      "reason": "更便宜但降噪偏弱",
      "score": 0.62
    }
  ],
  "refuse": false,
  "message": ""
}
```

## 带围栏+废话

```json
{
  "items": [
    {
      "name": "城际降噪 Pro",
      "reason": "续航更长更适合通勤",
      "score": 0.9
    }
  ],
  "refuse": false,
  "message": ""
}
```

## score 超界 → 重试

```json
{
  "items": [
    {
      "name": "城际降噪 Pro",
      "reason": "匹配通勤降噪与预算",
      "score": 0.85
    }
  ],
  "refuse": false,
  "message": ""
}
```
