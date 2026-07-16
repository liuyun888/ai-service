# 12.03 OCR/上游编排 · 验收笔记

## demo_suite
```json
{
  "ok": true,
  "ocr_ok": {
    "status": "ok",
    "invoice_no": "INV-2026-001",
    "amount": 128.5
  },
  "empty": "ocr_failed",
  "short": "need_human",
  "missing": "ocr_failed",
  "paste": "ok"
}
```

## HTTP
- `/v1/extract/invoice` ocr_mock img-1 → `ok`
- invoice_no=`INV-2026-001` amount=`128.5`

```bash
curl -s http://127.0.0.1:8091/v1/extract/invoice \
  -H 'Content-Type: application/json' \
  -H 'X-Internal-Token: dev-internal-token' \
  -H 'X-Tenant-Id: demo' \
  -d '{"source":"ocr_mock","image_id":"img-1"}'
```

SUMMARY: ocr_orchestration 验收通过
