# 09.02 搭建 MCP Server · 实跑记录


- lifecycle: 启动 → 握手 initialize → tools/list →（09.03）tools/call 完善 Schema

## STEP 1 · 进程模型

- **stdio**：Client 拉起子进程，stdin/stdout 管道（本地 IDE 调试（本课主路径））
- **HTTP/SSE**：独立常驻服务，网络访问（团队共享 / 远程（进阶））

## STEP 2 · import

- `{'mcp_package_ok': True, 'mcp_error': '', 'server_import_ok': True, 'server_name': 'ai-service-tools', 'server_error': '', 'ok': True}`

## STEP 3 · inprocess list

- tools: `['search_docs']`

## STEP 4 · stdio

- tools: `['search_docs']`
- call: `["mock: no hits for 'ping'; server is alive"]`

## STEP 5 · stderr

- `{'log_uses_stderr': True, 'suspect_stdout_log': False, 'ok': True}`

## STEP 6 · Cursor 配置

- 文件: `/Users/liuyunkai/Documents/workspace/AI从0到1/ai-service/notes/cursor_mcp_ai_service_tools.json`
```json
{
  "mcpServers": {
    "ai-service-tools": {
      "command": "/Users/liuyunkai/Documents/workspace/AI从0到1/ai-service/.venv/bin/python",
      "args": [
        "-m",
        "app.mcp.server"
      ],
      "cwd": "/Users/liuyunkai/Documents/workspace/AI从0到1/ai-service"
    }
  }
}
```
