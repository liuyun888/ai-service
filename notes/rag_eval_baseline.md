# 03.06 召回评测基线

- 小测集：`tests/rag_cases.jsonl`（10 题）
- top_k：5
- Embedding：`BAAI/bge-small-zh-v1.5`
- 后端：`memory`
- **命中率：10/10 ≈ 100%**

> 以后改切分 / topK / 模型，用同一题集重跑，和本基线对比。

## 明细

| # | 问题 | 期望 source | 命中 | top sources（最多 3） |
|---|------|-------------|------|------------------------|
| 1 | 七天无理由退货需要什么条件？ | `return_policy.md` | ✓ | `['return_policy.md', 'hospital_visit.md', 'return_policy.md']` |
| 2 | 降噪耳机 Pro 整机保修多久？ | `return_policy.md` | ✓ | `['return_policy.md', 'return_policy.md', 'return_policy.md']` |
| 3 | 签收超过七天出现质量问题如何处理？ | `return_policy.md` | ✓ | `['return_policy.md', 'return_policy.md', 'shipping_faq.md']` |
| 4 | 工作日几点前付款可以当天发货？ | `shipping_faq.md` | ✓ | `['shipping_faq.md', 'return_policy.md', 'cafeteria_menu.md']` |
| 5 | 新疆西藏偏远地区时效大概怎样？ | `shipping_faq.md` | ✓ | `['shipping_faq.md', 'shipping_faq.md', 'course_enrollment.md']` |
| 6 | 发货后怎么查询物流运单号？ | `shipping_faq.md` | ✓ | `['shipping_faq.md', 'shipping_faq.md', 'return_policy.md']` |
| 7 | 选修数据结构需要先修哪些课？ | `course_enrollment.md` | ✓ | `['course_enrollment.md', 'course_enrollment.md', 'course_enrollment.md']` |
| 8 | 数据结构课程平时作业占总成绩多少？ | `course_enrollment.md` | ✓ | `['course_enrollment.md', 'course_enrollment.md', 'course_enrollment.md']` |
| 9 | 门诊就诊前需要携带哪些证件？ | `hospital_visit.md` | ✓ | `['hospital_visit.md', 'hospital_visit.md', 'hospital_visit.md']` |
| 10 | 医院当日号源大概几点开放？ | `hospital_visit.md` | ✓ | `['hospital_visit.md', 'hospital_visit.md', 'cafeteria_menu.md']` |

## 失败题（优先分析）

_本题集本轮全部命中_
