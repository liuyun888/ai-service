# app/mcp/concepts.py
"""课次 09.01 · MCP 四要素的进程内迷你实现（不装官方 SDK 也能跑通概念）。

直觉：MCP ≈ AI 工具的 USB——Client 插上 Server，就能 list / call Tool、读 Resource。
本文件刻意不依赖 `mcp` 包：09.02 再换成真正的 stdio Server。

和「普通函数 Tool」差在哪：
- 普通：调用方必须 import 函数，换 IDE/框架要重新接线
- MCP 形：调用方只认「名字 + JSON Schema」，经协议发现与调用
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

# ---------------------------------------------------------------------------
# 四要素：用小白能看懂的数据结构钉死含义
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class McpTool:
    """Tool = 可调用动作（带参数 Schema）。

    参数:
        name: 工具名，Client list 时看到的名字
        description: 给模型看的一句话说明
        input_schema: JSON Schema 风格的参数描述（演示用 dict）
        handler: 真正干活的函数；生产里 handler 要薄，核心进 service
    """

    name: str
    description: str
    input_schema: dict[str, Any]
    handler: Callable[..., Any]


@dataclass(frozen=True)
class McpResource:
    """Resource = 可读数据/文件类资源（不是动作）。

    参数:
        uri: 如 policy://return —— 像说明书编号
        name: 人类可读名
        description: 用途说明
        mime_type: 内容类型
        reader: 无参读取函数，返回文本
    """

    uri: str
    name: str
    description: str
    mime_type: str
    reader: Callable[[], str]


@dataclass
class MiniMcpServer:
    """Server = 暴露能力的「工具箱」进程（本课用内存对象模拟）。

    生产：独立进程，经 stdio / HTTP 与 Client 通信（见 09.02）。
    """

    name: str
    tools: dict[str, McpTool] = field(default_factory=dict)
    resources: dict[str, McpResource] = field(default_factory=dict)

    def register_tool(self, tool: McpTool) -> None:
        """注册一个 Tool；同名覆盖并记一条（演示用直接覆盖）。"""
        self.tools[tool.name] = tool

    def register_resource(self, resource: McpResource) -> None:
        """注册一个 Resource。"""
        self.resources[resource.uri] = resource

    def list_tools(self) -> list[dict[str, Any]]:
        """协议层：tools/list —— 只返回描述，不返回 handler 源码。"""
        return [
            {
                "name": t.name,
                "description": t.description,
                "inputSchema": t.input_schema,
            }
            for t in self.tools.values()
        ]

    def call_tool(self, name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
        """协议层：tools/call —— 按名字调，Client 不必 import 业务函数。"""
        arguments = dict(arguments or {})
        tool = self.tools.get(name)
        if tool is None:
            return {"ok": False, "error": f"unknown_tool:{name}", "content": ""}
        # 极简参数校验：required 字段必须出现
        required = list((tool.input_schema.get("required") or []))
        missing = [k for k in required if k not in arguments]
        if missing:
            return {
                "ok": False,
                "error": f"missing_required:{missing}",
                "content": "",
            }
        try:
            result = tool.handler(**arguments)
        except TypeError as exc:
            return {"ok": False, "error": f"bad_args:{exc}", "content": ""}
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": f"{type(exc).__name__}: {exc}", "content": ""}
        return {"ok": True, "error": "", "content": str(result)}

    def list_resources(self) -> list[dict[str, Any]]:
        """协议层：resources/list。"""
        return [
            {
                "uri": r.uri,
                "name": r.name,
                "description": r.description,
                "mimeType": r.mime_type,
            }
            for r in self.resources.values()
        ]

    def read_resource(self, uri: str) -> dict[str, Any]:
        """协议层：resources/read —— 读内容，不是「执行动作」。"""
        res = self.resources.get(uri)
        if res is None:
            return {"ok": False, "error": f"unknown_resource:{uri}", "text": ""}
        try:
            text = res.reader()
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": f"{type(exc).__name__}: {exc}", "text": ""}
        return {
            "ok": True,
            "error": "",
            "uri": uri,
            "mimeType": res.mime_type,
            "text": text,
        }


@dataclass
class MiniMcpClient:
    """Client = 连接并调用的一方（IDE / Agent 运行时）。

    本课：直接持有 Server 引用。真 MCP：经 stdio/HTTP 发 JSON-RPC。
    """

    server: MiniMcpServer

    def discover(self) -> dict[str, Any]:
        """一次「插上 USB」后能看见什么。"""
        return {
            "server": self.server.name,
            "tools": self.server.list_tools(),
            "resources": self.server.list_resources(),
        }

    def call(self, tool_name: str, **kwargs: Any) -> dict[str, Any]:
        """调用已发现的 Tool。"""
        return self.server.call_tool(tool_name, kwargs)

    def read(self, uri: str) -> dict[str, Any]:
        """读取 Resource。"""
        return self.server.read_resource(uri)


# ---------------------------------------------------------------------------
# 演示业务：同一能力，两种接线方式
# ---------------------------------------------------------------------------


def plain_search_docs(query: str) -> str:
    """普通函数 Tool：调用方必须 import 本函数（换框架就要重接线）。"""
    q = (query or "").strip()
    if not q:
        return "error=empty_query"
    # 复用 08.03 知识库；失败则退回 mock，保证本课不依赖外网
    try:
        from app.harness.context.vfs import DEFAULT_VFS

        hits = DEFAULT_VFS.search_docs(q, limit=3)
        if not hits:
            return f"plain: no hits for {q!r}"
        lines = [f"{h['path']} :: {h['snippet'][:80]}" for h in hits]
        return "plain:\n" + "\n".join(lines)
    except Exception:  # noqa: BLE001
        return f"plain mock: found 0 for {q!r}"


def _mcp_search_handler(query: str) -> str:
    """MCP Tool 背后的 handler：逻辑可与 plain 相同，但对外只暴露名字+Schema。"""
    # 故意复用同一核心，突出「差异在接线方式，不在业务本身」
    text = plain_search_docs(query)
    if text.startswith("plain:"):
        return "mcp:" + text[len("plain") :]
    if text.startswith("plain mock:"):
        return "mcp mock:" + text[len("plain mock") :]
    return f"mcp: {text}"


def _read_return_policy() -> str:
    """Resource reader：读退货政策片段。"""
    try:
        from app.harness.context.vfs import DEFAULT_VFS

        return DEFAULT_VFS.read_doc("manual/return_policy.md", offset=0, limit=400)
    except Exception:  # noqa: BLE001
        return "（演示）七天无理由相关条款摘要：已拆封通常不支持无理由……"


def build_demo_server() -> MiniMcpServer:
    """搭一个带 search_docs Tool + policy Resource 的迷你 Server。"""
    server = MiniMcpServer(name="ai-service-tools-mini")
    server.register_tool(
        McpTool(
            name="search_docs",
            description="按关键词搜索知识库（退货政策/投诉摘要等）",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "搜索关键词，如「已拆封」",
                    }
                },
                "required": ["query"],
            },
            handler=_mcp_search_handler,
        )
    )
    server.register_resource(
        McpResource(
            uri="policy://return",
            name="退货政策",
            description="退换货政策可读资源（不是 Tool）",
            mime_type="text/plain",
            reader=_read_return_policy,
        )
    )
    return server


def contrast_plain_vs_mcp(query: str = "已拆封") -> dict[str, Any]:
    """对照：普通函数调用 vs MCP 发现后再调用。

    返回:
        两边结果 + 接线差异说明（给笔记用）
    """
    plain_out = plain_search_docs(query)
    server = build_demo_server()
    client = MiniMcpClient(server)
    discovered = client.discover()
    mcp_out = client.call("search_docs", query=query)
    resource = client.read("policy://return")
    return {
        "query": query,
        "plain": {
            "how": "from app.mcp.concepts import plain_search_docs; plain_search_docs(q)",
            "result": plain_out,
            "must_import_function": True,
        },
        "mcp": {
            "how": "client.discover() → client.call('search_docs', query=...)",
            "discovered_tool_names": [t["name"] for t in discovered["tools"]],
            "discovered_resource_uris": [r["uri"] for r in discovered["resources"]],
            "call_result": mcp_out,
            "resource_preview": (resource.get("text") or "")[:200],
            "must_import_function": False,
        },
        "lesson": (
            "同一业务能力可以既是普通函数，也是 MCP Tool；"
            "MCP 的价值是标准发现与跨 Client 复用，不是换一套业务逻辑。"
        ),
    }


def four_elements_cheatsheet() -> list[dict[str, str]]:
    """四要素一句话小抄（验收口述用）。"""
    return [
        {"name": "Server", "ask": "谁在暴露能力？", "one_liner": "工具箱进程"},
        {"name": "Client", "ask": "谁来连接并调用？", "one_liner": "IDE / Agent 运行时"},
        {"name": "Tool", "ask": "能做什么动作？", "one_liner": "带 Schema 的可调用扳手"},
        {
            "name": "Resource",
            "ask": "能读什么数据？",
            "one_liner": "说明书/配置片（读，不是调）",
        },
    ]


def topology_ascii() -> str:
    """Client–Server–Tool/Resource 关系图（写入笔记）。"""
    return """\
[Cursor / Agent Client]
        |  MCP（本课：进程内迷你协议；09.02：stdio）
        v
[Server: ai-service-tools]
        |-- Tool: search_docs(query)
        |-- Resource: policy://return
        v
  业务：知识库 VFS / 本地文件 / 下游 API
"""
