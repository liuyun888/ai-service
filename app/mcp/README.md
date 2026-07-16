# MCP 工具箱（ai-service）

本目录把「可被 IDE / Agent 发现的工具」与「业务纯函数」拆开，避免两份逻辑。

## 结构

| 路径 | 职责 |
|------|------|
| `tools_*.py` | 业务纯函数（单测、生产热路径） |
| `server.py` | MCP 薄壳：注册 Tool + stdio |
| `concepts.py` | 09.01 迷你协议（概念课） |
| `dual_entry.py` | 09.04 进程内 / MCP / REST 形对照 |
| `selection.py` | 选型矩阵与 Harness 接入策略 |

## 何时用 MCP

- 本地 IDE（Cursor 等）调试 Tool：改完即 `list` / `call`
- 需要给多个 Agent **宿主**复用同一套工具描述时
- 需要访问本机资源、又希望协议标准可发现时

## 何时不用（改走别的门）

- **生产热路径低延迟**：优先进程内 `import tools_*.py`（不要为统一而强制 stdio MCP）
- **纯服务间集成 / 公网网关 / 多语言调用方**：优先 REST + 网关鉴权
- **写入 / 赔付 / 改密**：默认不进 MCP；要上必须鉴权 + HITL（M07）

## 与运行时关系（双入口、单实现）

```text
同一份业务函数（tools_inventory.get_inventory 等）
  ├─ 生产 Agent / Harness：进程内直接调（快）
  └─ 开发 IDE：MCP 暴露同一函数（好调）
```

- 业务实现：`app/mcp/tools_*.py`
- MCP 暴露：`app/mcp/server.py`
- Agent 生产调用：`import` 纯函数，**不强制**经 MCP

## Cursor 配置

见 `notes/cursor_mcp_ai_service_tools.json`（由 `scripts/09_02_mcp_server_demo.py` / `09_04_*` 生成）。

要点：

- `command`：`.venv/bin/python`
- `args`：`["-m", "app.mcp.server"]`
- `cwd`：`ai-service` 根目录
- 一般**不必**把 `OPENAI_API_KEY` 塞进 MCP，除非某个 Tool 真的要调模型

## 验收命令

```bash
cd ai-service
python scripts/09_04_client_integration_demo.py
```

## 安全

MCP Server 能读本地文件 / 调内网 API 时，等同高权限插件。本课三个 Tool 默认只读；写入策略见上「何时不用」。
