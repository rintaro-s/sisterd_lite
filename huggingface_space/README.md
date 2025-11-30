---
title: systerd-lite
colorFrom: blue
colorTo: purple
sdk: gradio
sdk_version: 4.0.0
app_file: app.py
pinned: false
license: mit
---

# systerd-lite - AI-Native OS Core

**FULL MCP Server with 199+ Tools** | Linux System Control

systerd-lite enables LLMs to autonomously monitor, control, and optimize Linux systems through the Model Context Protocol (MCP).

## 🎬 Demo

<video src="./demo.webm" controls loop muted playsinline style="max-width:100%;height:auto;">
Your browser does not support the video tag. Download the demo: [demo.webm](./demo.webm)
</video>

## 📁 Structure

| File | Role |
|------|------|
| `app.py` | **Main entry point** - Gradio Web UI (uses `$PORT` from HF) |
| `mcp_main.py` | **Backend MCP server** - stdio transport for MCP clients |
| `systerd_lite/` | Full module with 199+ tools |

## 🚀 Quick Start

### Web UI (Gradio)

The Space automatically runs `app.py` which provides:
- Tool browser and executor
- Permission template manager
- Calculator and system monitor

### MCP Client Integration

`mcp_main.py` is a stdio-based MCP server. Connect from any MCP client:

```python
import subprocess
import json

# Start MCP server as subprocess
proc = subprocess.Popen(
    ["python", "mcp_main.py"],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE
)

# Initialize
request = {"jsonrpc": "2.0", "id": 1, "method": "initialize"}
proc.stdin.write((json.dumps(request) + '\n').encode())
proc.stdin.flush()
response = json.loads(proc.stdout.readline())
print(response)  # {"result": {"protocolVersion": "2024-11-05", ...}}

# List all tools
request = {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}
proc.stdin.write((json.dumps(request) + '\n').encode())
proc.stdin.flush()
response = json.loads(proc.stdout.readline())
print(f"Available tools: {len(response['result']['tools'])}")  # 199+

# Call a tool
request = {
    "jsonrpc": "2.0",
    "id": 3,
    "method": "tools/call",
    "params": {"name": "get_system_info", "arguments": {}}
}
proc.stdin.write((json.dumps(request) + '\n').encode())
proc.stdin.flush()
response = json.loads(proc.stdout.readline())
print(json.loads(response['result']['content'][0]['text']))
```

### VS Code MCP Integration

Add to `.vscode/mcp.json`:

```json
{
  "servers": {
    "systerd-lite": {
      "type": "stdio",
      "command": "python",
      "args": ["mcp_main.py"],
      "cwd": "${workspaceFolder}/huggingface_space"
    }
  }
}
```

### CLI Test

```bash
# Test initialization
echo '{"jsonrpc":"2.0","id":1,"method":"initialize"}' | python mcp_main.py

# Test tools/list
echo '{"jsonrpc":"2.0","id":2,"method":"tools/list"}' | python mcp_main.py
```

## Features

- 🔧 **199+ System Control Tools**: Process, network, storage, security management
- 🤖 **LLM Self-Editing**: Read, write, and modify its own environment
- 📡 **MCP Support**: stdio transport (NOT HTTP - runs as subprocess)
- 🔐 **Flexible Permissions**: Per-tool permission settings

## Tool Categories

| Category | Description | Example Tools |
|----------|-------------|---------------|
| Monitoring | System observation | `get_system_info`, `list_processes`, `get_cpu_info` |
| Security | Security status | `get_selinux_status`, `audit_permissions`, `scan_suid_files` |
| System | Systemd/kernel | `manage_service`, `list_units`, `get_kernel_modules` |
| Network | Networking | `list_interfaces`, `ping_host`, `list_routes` |
| Container | Docker/Podman | `list_containers`, `start_container`, `execute_code` |
| Calculator | Math operations | `calculate`, `convert_units`, `statistics` |
| Self | LLM environment | `read_workspace_file`, `write_workspace_file`, `execute_shell_command` |
| MCP | Configuration | `list_mcp_tools`, `apply_mcp_template`, `get_mcp_config` |
| Scheduler | Task scheduling | `create_task`, `list_tasks`, `create_reminder` |
| AI | Ollama integration | `ai_generate`, `ai_chat`, `ai_analyze_issue` |

## Permission Templates

- **minimal**: Basic monitoring (~18 tools)
- **monitoring**: System monitoring (~18 tools)
- **development**: Dev tools + containers + self-modification (~47 tools)
- **security**: Security audit tools (~31 tools)
- **full**: **ALL 199+ tools enabled** - NO COMPROMISE

## Architecture

```
Hugging Face Space
├── app.py              # Gradio UI (uses $PORT)
├── mcp_main.py         # stdio MCP server (subprocess)
└── systerd_lite/       # Full module (ALL features)
    ├── mcp.py          # 199+ tools
    ├── mcp_extended.py # 100+ extended tools
    ├── calculator.py   # Advanced calculator
    ├── scheduler.py    # Task scheduler
    ├── container.py    # Container manager
    ├── ollama.py       # AI integration
    └── ...
```

## Links

- [GitHub Repository](https://github.com/rintaro-s/sisterd_lite)
- [MCP Protocol](https://modelcontextprotocol.io/)


➤ Gradio is NOT the MCP server.
➤ The MCP server is a pure stdio process (`mcp_main.py`) called as a child process.

I thought about publishing the MCP server via HTTP, but I interpreted that only one port can be open within a space, so I thought this was appropriate.