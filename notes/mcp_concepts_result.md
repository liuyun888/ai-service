# 09.01 MCP 概念 · 实跑记录


## 拓扑

```
[Cursor / Agent Client]
        |  MCP（本课：进程内迷你协议；09.02：stdio）
        v
[Server: ai-service-tools]
        |-- Tool: search_docs(query)
        |-- Resource: policy://return
        v
  业务：知识库 VFS / 本地文件 / 下游 API
```

- **Server**：工具箱进程
- **Client**：IDE / Agent 运行时
- **Tool**：带 Schema 的可调用扳手
- **Resource**：说明书/配置片（读，不是调）

## STEP 3 · 对照

- plain: `plain:
case/complaints_week.md :: 练「先规划再执行」。真实环境请换成导出工单。  ## Top 问题  1. **已拆封与七天无理由口径冲突**（42 单）      用户看到营销页「七天无理由
manual/return_policy.md :: . 未激活账号绑定、未写入不可撤销数据（数字商品另见专章）。  ### 2.1 已拆封是否支持七天无理由？  **一般情况：不支持「七天无理由」。**   商品
manual/shipping.md :: 破损处。  ## 与退货的关系  物流破损走「质量问题退换」，不按七天无理由卡「已拆封」。详见 `manual`
- mcp tools: `['search_docs']`
- mcp call: `{'ok': True, 'error': '', 'content': 'mcp::\ncase/complaints_week.md :: 练「先规划再执行」。真实环境请换成导出工单。  ## Top 问题  1. **已拆封与七天无理由口径冲突**（42 单）      用户看到营销页「七天无理由\nmanual/return_policy.md :: . 未激活账号绑定、未写入不可撤销数据（数字商品另见专章）。  ### 2.1 已拆封是否支持七天无理由？  **一般情况：不支持「七天无理由」。**   商品\nmanual/shipping.md :: 破损处。  ## 与退货的关系  物流破损走「质量问题退换」，不按七天无理由卡「已拆封」。详见 `manual/return_policy.md` 第 3 章。'}`
- 同一业务能力可以既是普通函数，也是 MCP Tool；MCP 的价值是标准发现与跨 Client 复用，不是换一套业务逻辑。

## STEP 4 · Tool vs Resource

- Tool=动作(call)；Resource=可读数据(read)；URI 不是 Tool 名

## STEP 5 · 三问

1. Client=Cursor（或你的 Agent 运行时）——连接并调用的一方；Server=ai-service-tools（迷你/后续真 MCP Server）——暴露能力的进程
2. Tool=`search_docs`
3. 参数=`['query: str  # 搜索关键词']`

## STEP 6

- 下一课落地真 MCP Server 进程
