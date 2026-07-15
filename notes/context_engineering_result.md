# 08.03 Context Engineering · 实跑记录


- USE_CHAT=0
- VFS root: `/Users/liuyunkai/Documents/workspace/AI从0到1/ai-service/knowledge_base`
- Tools: `['list_docs', 'search_docs', 'read_doc']`

## STEP 1 · Tools

- `['list_docs', 'search_docs', 'read_doc']`

## STEP 2 · Prompt 预算

- stuff=1574 tree=254 ratio=6.2x

## STEP 3 · 脚本轨迹

- tools: `['list_docs', 'search_docs', 'read_doc']`
- reply: 一般不支持七天无理由：外包装已拆、影响二次销售的，走质量问题退换。依据：`manual/return_policy.md` §2.1。若有功能故障，可按同文件第 3 章举证申请。
- cite: `manual/return_policy.md`

## STEP 4 · 安全

- outside: error=path_outside_root
- secret: error=denied_prefix:secrets
- truncate_ok: True

## STEP 5 · LLM

- skipped (USE_CHAT=0)

## STEP 6 · 五维映射

- 信息流：按需 read，不预装全书
