# docs/ops.md
# 运维速查（课次 13.02）

## 可观测

| 信号 | 本仓库落点 |
|------|------------|
| request_id | 内部头 `X-Request-Id`（BFF → ai-service） |
| Trace | `app/harness/middleware/trace.py` → `tmp/trace-final.json` |
| Token | `app/harness/middleware/token_log.py`（粗估） |
| 脱敏 | `app/harness/middleware/redact.py` |

有 LangSmith 时：把同一 `trace_id` 挂到平台；没有平台时自建 JSON 足够迭代。

## 成本杠杆（优先序）

见 `app/ops/cost.py` 的 `list_cost_levers()`：规则/缓存 → topK → max_steps → 分流 → Compaction → **最后**换模。

## 评估

- 金标抽检：`app/ops/eval_gold.py`
- 单测：`tests/test_harness.py`、`tests/test_extract_validate.py`

## 一键验收

```bash
cd ai-service
.venv/bin/python scripts/13_02_observability_cost_demo.py
```
