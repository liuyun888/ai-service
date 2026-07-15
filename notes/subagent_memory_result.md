# 08.05 子 Agent 与长期记忆 · 实跑记录


- goal: 写一份退货体验改进草案
- skills: ['research_agent', 'writer_agent']

## STEP 1 · skills

- `['research_agent', 'writer_agent']`

## STEP 2 · 委派

- problems: `[{'title': '已拆封与七天无理由口径冲突', 'evidence': '政策：已拆封通常不支持无理由→质量问题通道', 'path': 'manual/return_policy.md'}, {'title': '退款到账时限说不清', 'evidence': '退款到账时限说不清', 'path': 'case/complaints_week.md'}, {'title': '物流破损却被当成无理由拒', 'evidence': '政策：已拆封通常不支持无理由→质量问题通道', 'path': 'manual/return_policy.md'}]`
- isolation_ok: True

## STEP 3 · 防套娃

- `{'ok': False, 'error': 'error=depth_exceeded:1>=1'}`

## STEP 4 · Memory 文件

- got: 条目制；少形容词；避免绝对承诺
- path: `/Users/liuyunkai/Documents/workspace/AI从0到1/ai-service/notes/memory_store_demo.json`

## STEP 5 · 租户

- {'A': '租户A偏好', 'B': '租户B偏好', 'A_cannot_see_B_value': True}
- 生产必须按 tenant_id 隔离；本课 get/put 已带租户作用域

## STEP 6 · 最终稿

```
# 退货体验改进草案（子 Agent 写作）

1. 问题：已拆封与七天无理由口径冲突
   - 动作：针对「已拆封与七天无理由口径冲突」统一话术与流程卡
   - 度量：相关投诉周环比下降
   - 证据路径：manual/return_policy.md
2. 问题：退款到账时限说不清
   - 动作：针对「退款到账时限说不清」统一话术与流程卡
   - 度量：相关投诉周环比下降
   - 证据路径：case/complaints_week.md
3. 问题：物流破损却被当成无理由拒
   - 动作：针对「物流破损却被当成无理由拒」统一话术与流程卡
   - 度量：相关投诉周环比下降
   - 证据路径：manual/return_policy.md

依据来自 research JSON；未额外检索全库。
（草稿语气：（已按偏好去掉（已按偏好去掉绝对化表述）化表述）的方案，（已按偏好去掉绝对化表述）（已按偏好去掉绝对化表述）——应交父级按偏好删掉）

> 来自记忆的偏好：条目制；少形容词；避免绝对承诺
（来自记忆的偏好已应用）
```
