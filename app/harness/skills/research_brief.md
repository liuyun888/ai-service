# research_agent brief

## 目标

只读退货政策与投诉摘要，提炼 Top3 问题；不做写作、不对用户承诺。

## 完成定义

返回 JSON：`{"problems":[{"title":"","evidence":"","path":""}]}`，恰好 3 条。

## 允许 Tool

- `list_docs`
- `search_docs`
- `read_doc`

## 必须引用的材料路径

- `manual/return_policy.md`
- `case/complaints_week.md`

## 禁止事项

- 不得对用户直接下承诺（退款/时效）
- 不得再开子 Agent（深度限制 = 1）
- 不得读取父会话闲聊；只用本 brief 与工具结果
