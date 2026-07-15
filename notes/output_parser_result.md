# 05.04 Output Parser · 实跑记录

- USE_CHAT: `False`
- pref: 预算 1000 内，通勤地铁降噪，续航尽量长
- provider: `openai`

## STEP 1 · 成功

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

## STEP 2 · 失败可见

```text
1 validation error for RecommendResult
items.0.score
  Input should be less than or equal to 1 [type=less_than_equal, input_value=1.5, input_type=float]
    For further information visit https://errors.pydantic.dev/2.13/v/less_than_equal
```

## STEP 3 · 重试

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

## STEP 4 · Runnable Parser

- type: `RecommendResult`

## STEP 5 · 离线 run_recommend

```json
{
  "items": [
    {
      "name": "城际降噪 Pro",
      "reason": "匹配通勤降噪与预算",
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

## 结论

- Parser 在模型之后、业务之前；失败要可见，不要静默 None。
- 造数据可单独验收 Schema；真模型用校验错误回喂修复。
- LCEL：`prompt | model | StrOutputParser | pydantic_parser`。
