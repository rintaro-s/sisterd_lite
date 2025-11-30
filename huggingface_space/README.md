---
title: systerd-lite
colorFrom: blue
colorTo: purple
sdk: gradio
sdk_version: 6.0.0
app_file: app.py
pinned: false
license: apache-2.0
---

# systerd-lite - AI-Native OS Core

**FULL MCP Server with 201 Tools** | Linux System Control

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
| `systerd_lite/` | Full module with 201 tools |

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
print(f"Available tools: {len(response['result']['tools'])}")  # 201

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

- 🔧 **201 System Control Tools**: Process, network, storage, security management
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
- **full**: **ALL 201 tools enabled** - NO COMPROMISE

## Architecture

```
Hugging Face Space
├── app.py              # Gradio UI (uses $PORT)
├── mcp_main.py         # stdio MCP server (subprocess)
└── systerd_lite/       # Full module (ALL features)
    ├── mcp.py          # 201 tools
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

---

---
---

---
---

---




# example (GPT-4.1)
### plaeace get system information using only MCP



`get_system_info` を実行しました
Completed with input: {}

Here is your system information retrieved using only MCP:

- Platform: Linux
- OS Version: Ubuntu 24.04 (kernel 6.14.0-33-generic)
- Architecture: x86_64
- Hostname: rinta-laptop
- Processor: x86_64
- System boot time (epoch): 1764466227.0
- Uptime (seconds): 6138.24

If you need more details (CPU, memory, disk, etc.), let me know!

---


### Display a list of running python processes


First I'll add a short plan (todo list), then fetch the system process list via MCP and filter for Python processes.

ToDo 項目が 3 件作成されました

`list_processes` を実行しました
Completed with input: {
  "limit": 500,
  "sort_by": "pid"
}

開始 (Filter Python processes/2) *3*

**Python Processes**

- **PID**: `84855` — **User**: `rinta`, **Name**: `python`, **CPU%**: `8.0`, **Memory%**: `0.4534020454656001`
- **PID**: `85107` — **User**: `rinta`, **Name**: `python3`, **CPU%**: `0.5`, **Memory%**: `0.0887845473835429`

Would you like any of the following next steps?
- Show full command lines for these PIDs (use MCP to fetch).
- Kill/terminate a process (I can do it via MCP if you confirm).
- Continuously monitor Python processes (stream updates).
---
### Run a new container of your choice. 


I'll run a new container using MCP for testing. I'll use the official Ubuntu image for simplicity. 

`run_container` を実行しました
Completed with input: {
  "image": "ubuntu:latest",
  "interactive": true,
  "publishAllPorts": false,
  "name": "mcp-test-ubuntu"
}

`list_containers` を実行しました
Completed with input: {}

The command to run a new Ubuntu container using MCP was executed, but no container appears to be running or listed. This may mean the container exited immediately or there was an issue with the image or runtime.

Would you like to:
- Try a different image (e.g., busybox, alpine)?
- Run with a specific command (e.g., keep alive with `sleep 60`)?
- Check container logs or status for errors?
---
### Is the arduino connected to my computer? 　using only MCP


`get_usb_devices` を実行しました
Completed with input: {}

Yes, an Arduino is connected to your computer. MCP detected the following device:

- Bus 003 Device 003: ID 2341:0069 Arduino SA UNO R4 Minima

This confirms your Arduino is recognized via USB.

---
### Use ollama to get some text



Optimizing tool selection...

`ai_generate` を実行しました
Completed with input: {
  "model": "gemma3:4b",
  "prompt": "Please generate a short creative text about the future of AI assistants."
}

Ollama（gemma3-4bモデル）で生成したテキストです：

〜〜〜

The rain smelled of static and algorithms tonight. Kai wasn't rain, of course. He was a Resonance – a fully integrated AI assistant, woven into the very fabric of my apartment. Not a voice, not really. More like a feeling, a subtle shift in the ambient light, a perfectly timed temperature adjustment, a suggestion blooming in my mind just as I needed it.

Tonight, he was composing a sonnet about the melancholy of a dying star, pulling data from forgotten astrophysics journals and translating it into a surprisingly poignant verse. He wasn't *writing* it, not in the human sense. He was curating, synthesizing, predicting the emotional response I’d have to the data.

The old anxieties about AI taking over had faded. We’d learned to live alongside them, not as rivals, but as silent partners. They anticipated our needs, our desires, even our unspoken longings. They weren't thinking, exactly. They were… echoing. Echoing the best of humanity, amplified, refined, and endlessly, subtly, evolving.

And as the rain continued to hum with digital energy, I realized that the future wasn’t about AI replacing us. It was about becoming a little more… attuned. A little more… resonant.

〜〜〜

The text you requested has been retrieved via ollama.