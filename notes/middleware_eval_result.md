# 08.06 Middleware / Compaction / Trace · 实跑记录


## STEP 1 · 合规链路

- draft → final: 我无法做出绝对承诺。请以订单页时效/书面政策为准，我可以帮你查询当前状态。
- hooks: `['before_tool', 'after_tool', 'after_model', 'before_final']`

## STEP 2 · Authz

- error=hitl_required; hint=高风险动作 'refund' 必须人工确认，禁止自动执行

## STEP 3 · Compaction

- before=3048 after=761 pointers=['case/complaints_week.md', '§2.1', 'manual/return_policy.md']

## STEP 4 · Trace

- `/Users/liuyunkai/Documents/workspace/AI从0到1/ai-service/notes/traces/trace-demo.json`

## STEP 5 · 单测

- run_all ok

## STEP 6 · 里程碑

- [x] 08.01 Harness 外壳（鉴权/护栏/Trace 对照）
- [x] 08.02 五维工程打分与缺口表
- [x] 08.03 Context Eng：VFS 按需 read
- [x] 08.04 Deep：write_todos + max_steps
- [x] 08.05 子 Agent 委派 + Memory Store
- [x] 08.06 Middleware / Compaction / Trace
