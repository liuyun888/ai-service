# 12.01 正则与 LLM 抽取 · 验收笔记

## 样例字段
```json
{
  "invoice_no": "24442000001234567890",
  "date": "2026-03-15",
  "amount": 1280.0,
  "seller_name": "示例科技有限公司"
}
```

- regex 覆盖前 LLM 号码: `LLM-HALLUCINATED-000`
- 合并后号码: `24442000001234567890`
- filled_keys: `['invoice_no', 'date', 'amount', 'seller_name']`

## 字段策略
```json
{
  "invoice_no": "固定长数字串，正则稳定可审计；禁止 LLM 覆盖",
  "date": "写法多变（年月日/斜杠），适合 LLM 或宽松解析后再校验",
  "amount": "常带货币符号与中文大写，适合 LLM 归一成 number",
  "seller_name": "专名、换行、别名多，适合 LLM；仍禁止编造"
}
```

SUMMARY: regex_llm_extract 验收通过
