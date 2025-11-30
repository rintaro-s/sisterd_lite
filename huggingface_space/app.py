#!/usr/bin/env python3
"""
systerd-lite Gradio UI for Hugging Face Space

This is the entry point for the Hugging Face Space.
Gradio app that provides a web UI for interacting with systerd-lite.

The MCP server runs as a SUBPROCESS using stdio transport (NOT HTTP).
Gradio uses $PORT environment variable from Hugging Face.
"""

import gradio as gr
import json
import os
import subprocess
import asyncio
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List

# Add systerd_lite to path
script_dir = Path(__file__).parent.resolve()
sys.path.insert(0, str(script_dir))

# Import full systerd_lite modules
from systerd_lite.context import SysterdContext
from systerd_lite.modes import ModeController, SysterdMode
from systerd_lite.neurobus import NeuroBus
from systerd_lite.permissions import PermissionManager, Permission
from systerd_lite.mcp import MCPHandler
from systerd_lite.calculator import Calculator
from systerd_lite.sensors import SystemSensors

# State directory (inside huggingface_space for self-contained deployment)
STATE_DIR = script_dir / ".state"
STATE_DIR.mkdir(exist_ok=True)

# Config file for persistent settings
CONFIG_FILE = STATE_DIR / "config.json"

# Global instances
_context = None
_handler = None
_calculator = Calculator()
_sensors = SystemSensors()


def load_config() -> Dict[str, Any]:
    """Load configuration from file."""
    default_config = {
        "template": "full",
        "mode": "transparent",
        "ollama_url": "http://localhost:11434",
        "ollama_model": "gemma3:12b"
    }
    if CONFIG_FILE.exists():
        try:
            config = json.loads(CONFIG_FILE.read_text())
            # Merge with defaults to ensure all keys exist
            return {**default_config, **config}
        except:
            pass
    return default_config


def save_config(config: Dict[str, Any]) -> None:
    """Save configuration to file."""
    CONFIG_FILE.write_text(json.dumps(config, indent=2))


def get_context() -> SysterdContext:
    """Get or create the SysterdContext."""
    global _context
    if _context is None:
        socket_path = STATE_DIR / "systerd.sock"
        acl_file = STATE_DIR / "mode.acl"
        
        mode_controller = ModeController(
            state_file=STATE_DIR / "mode.json",
            acl_file=acl_file
        )
        
        neurobus = NeuroBus(
            storage=STATE_DIR / "neurobus.db",
            max_rows=10000,
            retention_days=7
        )
        
        _context = SysterdContext(
            state_dir=STATE_DIR,
            socket_path=socket_path,
            mode_controller=mode_controller,
            neurobus=neurobus,
            acl_file=acl_file
        )
        
        perm_file = STATE_DIR / "permissions.json"
        _context.permission_manager = PermissionManager(perm_file)
    
    return _context


def get_handler() -> MCPHandler:
    """Get or create the MCPHandler with ALL tools."""
    global _handler
    if _handler is None:
        _handler = MCPHandler(get_context())
    return _handler


# ===== MCP Info Functions =====
def get_mcp_info() -> str:
    """Get MCP server information."""
    handler = get_handler()
    config = load_config()
    
    info = {
        "name": "systerd-lite",
        "version": "3.0.0-full",
        "total_tools": len(handler.tools),
        "mcp_entry": "mcp_main.py",
        "transport": "stdio (subprocess)",
        "current_template": config.get("template", "full"),
        "current_mode": config.get("mode", "transparent"),
        "state_dir": str(STATE_DIR),
        "tool_categories": list(handler.MCP_TOOL_CATEGORIES.keys())
    }
    return json.dumps(info, indent=2)


def get_tool_list() -> str:
    """Get all available tools."""
    handler = get_handler()
    perm_mgr = get_context().permission_manager
    
    tools_by_category = {}
    for tool_name, tool in handler.tools.items():
        cat = "other"
        for category, tools in handler.MCP_TOOL_CATEGORIES.items():
            if tool_name in tools:
                cat = category
                break
        
        if cat not in tools_by_category:
            tools_by_category[cat] = []
        
        perm = perm_mgr.check(tool_name)
        tools_by_category[cat].append({
            "name": tool_name,
            "description": tool.description[:80] + "..." if len(tool.description) > 80 else tool.description,
            "enabled": perm.name != "DISABLED"
        })
    
    result = {
        "total_tools": len(handler.tools),
        "categories": {}
    }
    
    for cat in sorted(tools_by_category.keys()):
        tools = tools_by_category[cat]
        enabled = sum(1 for t in tools if t["enabled"])
        result["categories"][cat] = {
            "count": len(tools),
            "enabled": enabled,
            "tools": sorted(tools, key=lambda x: x["name"])
        }
    
    return json.dumps(result, indent=2)


def get_tool_categories() -> str:
    """Get available tool categories with counts."""
    handler = get_handler()
    
    categories = {}
    for cat, tools in handler.MCP_TOOL_CATEGORIES.items():
        categories[cat] = {
            "tool_count": len(tools),
            "example_tools": tools[:5]
        }
    
    return json.dumps(categories, indent=2)


# ===== Template Functions =====
def apply_template(template_name: str) -> str:
    """Apply a permission template and save to config."""
    handler = get_handler()
    
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(handler.tool_apply_mcp_template(template_name))
        loop.close()
        
        # Save to config
        config = load_config()
        config["template"] = template_name
        save_config(config)
        
        result["saved_to_config"] = True
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)}, indent=2)


def get_templates() -> str:
    """Get available templates."""
    handler = get_handler()
    
    templates = []
    for key, info in handler.MCP_TEMPLATES.items():
        templates.append({
            "id": key,
            "name": info["name"],
            "description": info["description"],
            "categories": info["categories"],
            "estimated_tool_count": info["tool_count"]
        })
    
    return json.dumps({"templates": templates}, indent=2)


# ===== Calculator Functions =====
def run_calculator(expression: str) -> str:
    """Evaluate a mathematical expression."""
    try:
        result = _calculator.evaluate(expression)
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)}, indent=2)


def convert_units(value: float, from_unit: str, to_unit: str) -> str:
    """Convert between units."""
    try:
        result = _calculator.convert_units(value, from_unit, to_unit)
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)}, indent=2)


def calculate_statistics(data_str: str) -> str:
    """Calculate statistics from comma-separated numbers."""
    try:
        data = [float(x.strip()) for x in data_str.split(",") if x.strip()]
        result = _calculator.statistics(data)
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)}, indent=2)


# ===== System Info Functions =====
def get_system_info() -> str:
    """Get system information."""
    try:
        import platform
        import psutil
        import time
        
        info = {
            "platform": platform.system(),
            "platform_release": platform.release(),
            "platform_version": platform.version(),
            "architecture": platform.machine(),
            "hostname": platform.node(),
            "processor": platform.processor(),
            "python_version": platform.python_version(),
            "cpu_count": psutil.cpu_count(),
            "cpu_percent": psutil.cpu_percent(interval=0.1),
            "memory": {
                "total_gb": round(psutil.virtual_memory().total / (1024**3), 2),
                "available_gb": round(psutil.virtual_memory().available / (1024**3), 2),
                "percent": psutil.virtual_memory().percent
            },
            "boot_time": datetime.fromtimestamp(psutil.boot_time()).isoformat(),
            "uptime_hours": round((time.time() - psutil.boot_time()) / 3600, 2)
        }
        return json.dumps(info, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)}, indent=2)


def get_process_list(search: str = "", sort_by: str = "cpu", limit: int = 50) -> str:
    """
    Get processes with flexible filtering and sorting.
    
    Args:
        search: Filter by process name (case-insensitive, partial match)
        sort_by: Sort by 'cpu', 'memory', 'pid', or 'name'
        limit: Maximum number of results
    """
    try:
        import psutil
        
        procs = []
        for p in psutil.process_iter(['pid', 'name', 'username', 'cpu_percent', 'memory_percent', 'cmdline', 'status']):
            try:
                info = p.info
                # Add command line as string
                cmdline = info.get('cmdline') or []
                info['cmdline_str'] = ' '.join(cmdline) if cmdline else ''
                procs.append(info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        # Filter by search term (name or cmdline)
        if search:
            search_lower = search.lower()
            procs = [
                p for p in procs 
                if search_lower in (p.get('name') or '').lower() 
                or search_lower in (p.get('cmdline_str') or '').lower()
            ]
        
        # Sort
        sort_keys = {
            'cpu': lambda x: x.get('cpu_percent', 0) or 0,
            'memory': lambda x: x.get('memory_percent', 0) or 0,
            'pid': lambda x: x.get('pid', 0),
            'name': lambda x: (x.get('name') or '').lower()
        }
        sort_key = sort_keys.get(sort_by, sort_keys['cpu'])
        reverse = sort_by in ['cpu', 'memory']  # Descending for cpu/memory
        procs.sort(key=sort_key, reverse=reverse)
        
        result = {
            "total_found": len(procs),
            "showing": min(limit, len(procs)),
            "filter": search or "(none)",
            "sort_by": sort_by,
            "processes": procs[:limit]
        }
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)}, indent=2)


# ===== Error Message Helpers =====
def format_error_response(error: Exception, tool_name: str = None) -> Dict[str, Any]:
    """Format an error with helpful hints for users."""
    error_str = str(error)
    
    response = {
        "status": "error",
        "error": error_str,
    }
    
    # Add specific hints based on error type
    if "permission" in error_str.lower() or "access denied" in error_str.lower():
        response["hint"] = "This operation requires elevated permissions. Try running with appropriate privileges or check permission settings."
        response["suggestion"] = "Use 'Templates' tab to adjust tool permissions, or run systerd-lite with elevated privileges."
    
    elif "not found" in error_str.lower() or "no such file" in error_str.lower():
        response["hint"] = "The requested resource was not found."
        response["suggestion"] = "Check the file path or resource name and try again."
    
    elif "timeout" in error_str.lower():
        response["hint"] = "The operation timed out."
        response["suggestion"] = "The service may be slow or unavailable. Try again later or check the service status."
    
    elif "connection" in error_str.lower() or "refused" in error_str.lower():
        response["hint"] = "Could not establish a connection."
        response["suggestion"] = "Check if the target service (Ollama, systemd, etc.) is running and accessible."
    
    elif "ollama" in error_str.lower():
        response["hint"] = "Ollama AI service is not available."
        response["suggestion"] = "Configure Ollama URL in the 'Ollama Settings' tab, or start Ollama with: ollama serve"
    
    elif "disabled" in error_str.lower():
        response["hint"] = "This tool is currently disabled."
        response["suggestion"] = "Enable it using the 'Templates' tab or set_mcp_tool_permission tool."
    
    if tool_name:
        response["tool"] = tool_name
    
    return response


# ===== Tool Execution =====
def execute_tool(tool_name: str, arguments_json: str) -> str:
    """Execute an MCP tool directly with improved error handling."""
    handler = get_handler()
    
    if tool_name not in handler.tools:
        return json.dumps({
            "status": "error",
            "error": f"Tool not found: {tool_name}",
            "hint": "Check the tool name spelling or use 'All Tools' button to see available tools.",
            "available_tools_count": len(handler.tools)
        }, indent=2)
    
    # Check permission
    perm_mgr = get_context().permission_manager
    perm = perm_mgr.check(tool_name)
    if perm.name == "DISABLED":
        return json.dumps({
            "status": "error",
            "error": f"Tool '{tool_name}' is disabled",
            "permission": perm.name,
            "hint": "This tool is currently disabled by permission settings.",
            "suggestion": "Use 'Templates' tab to apply a template that enables this tool, or use set_mcp_tool_permission."
        }, indent=2)
    
    try:
        args = json.loads(arguments_json) if arguments_json.strip() else {}
    except json.JSONDecodeError as e:
        return json.dumps({
            "status": "error",
            "error": f"Invalid JSON arguments: {e}",
            "hint": "Please provide valid JSON format for arguments.",
            "example": '{"key": "value"} or {} for no arguments'
        }, indent=2)
    
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(handler.tools[tool_name].handler(**args))
        loop.close()
        return json.dumps(result, indent=2, default=str)
    except Exception as e:
        return json.dumps(format_error_response(e, tool_name), indent=2)


def get_tool_schema(tool_name: str) -> str:
    """Get the schema for a specific tool."""
    handler = get_handler()
    
    if tool_name not in handler.tools:
        return json.dumps({
            "status": "error",
            "error": f"Tool not found: {tool_name}",
            "hint": "Check the tool name or browse available tools."
        }, indent=2)
    
    tool = handler.tools[tool_name]
    
    # Get permission status
    perm_mgr = get_context().permission_manager
    perm = perm_mgr.check(tool_name)
    
    return json.dumps({
        "name": tool.name,
        "description": tool.description,
        "permission": perm.name,
        "enabled": perm.name != "DISABLED",
        "inputSchema": tool.parameters
    }, indent=2)


# ===== Build Gradio App =====
def create_app():
    """Create the Gradio application."""
    handler = get_handler()
    tool_names = sorted(handler.tools.keys())
    config = load_config()
    
    # Gradio 6.x compatible - no theme in Blocks constructor
    with gr.Blocks(title="systerd-lite - AI-Native OS Core") as demo:
        
        # ===== HOME PAGE =====
        gr.Markdown(f"""
# 🎛️ systerd-lite - AI-Native OS Core

## What is systerd-lite?

**systerd-lite** is an AI-Native OS Core that enables LLMs to autonomously monitor, 
control, and optimize Linux systems through the **Model Context Protocol (MCP)**.

### ✨ Key Features

| Feature | Description |
|---------|-------------|
| 🔧 **{len(handler.tools)} Tools** | System monitoring, process control, network, security, containers |
| 🤖 **LLM Self-Editing** | AI can read, write, and modify its own environment |
| 📡 **MCP Protocol** | stdio transport for VS Code and other MCP clients |
| 🔐 **Permission System** | Fine-grained control (DISABLED, READ_ONLY, AI_ASK, AI_AUTO) |

### 🚀 Quick Start

**For VS Code / MCP Clients:**
```bash
# Add to .vscode/mcp.json
{{"servers": {{"systerd-stdio": {{"type": "stdio", "command": "python3", "args": ["mcp_main.py"], "cwd": "huggingface_space"}}}}}}
```

**CLI Test:**
```bash
echo '{{"jsonrpc":"2.0","id":1,"method":"tools/list"}}' | python3 mcp_main.py
```

### 📁 Current Configuration

- **State Directory:** `{STATE_DIR}`
- **Active Template:** `{config.get('template', 'full')}`
- **Mode:** `{config.get('mode', 'transparent')}`

---
Use the tabs above to explore tools, apply templates, and execute commands.
        """)
        
        with gr.Tab("📡 MCP Server"):
            gr.Markdown("### MCP Server Status & Configuration")
            
            with gr.Row():
                info_btn = gr.Button("🔍 Server Info", variant="primary")
                tools_btn = gr.Button("📋 All Tools")
                cat_btn = gr.Button("📂 Categories")
            
            mcp_output = gr.Code(label="MCP Information", language="json", lines=20)
            
            info_btn.click(get_mcp_info, outputs=[mcp_output])
            tools_btn.click(get_tool_list, outputs=[mcp_output])
            cat_btn.click(get_tool_categories, outputs=[mcp_output])
        
        with gr.Tab("⚙️ Templates"):
            gr.Markdown("### Permission Templates")
            gr.Markdown("""
Configure which tools are enabled. Settings are **saved automatically** to `.state/config.json`.

| Template | Description | Tools |
|----------|-------------|-------|
| `minimal` | Basic monitoring only | ~18 |
| `monitoring` | System monitoring | ~18 |
| `development` | Dev tools + containers + self-modification | ~109 |
| `security` | Security audit tools | ~47 |
| `full` | **ALL tools enabled** | **201** |
            """)
            
            with gr.Row():
                template_dropdown = gr.Dropdown(
                    label="Select Template",
                    choices=["minimal", "monitoring", "development", "security", "full"],
                    value=config.get("template", "full")
                )
                apply_btn = gr.Button("💾 Apply & Save", variant="primary")
                list_btn = gr.Button("📄 Show Templates")
            
            template_output = gr.Code(label="Result", language="json", lines=15)
            apply_btn.click(apply_template, inputs=[template_dropdown], outputs=[template_output])
            list_btn.click(get_templates, outputs=[template_output])
        
        with gr.Tab("🤖 Ollama Settings"):
            gr.Markdown("### Ollama AI Configuration")
            gr.Markdown("""
Configure the Ollama AI backend connection. Settings are **saved automatically** to `.state/config.json`.

**Note:** Ollama is optional. If not available, AI tools will return helpful error messages.
            """)
            
            with gr.Row():
                ollama_url = gr.Textbox(
                    label="Ollama URL",
                    placeholder="http://localhost:11434",
                    value=config.get("ollama_url", "http://localhost:11434"),
                    scale=2
                )
                ollama_model = gr.Textbox(
                    label="Default Model",
                    placeholder="gemma3:12b",
                    value=config.get("ollama_model", "gemma3:12b"),
                    scale=1
                )
            
            with gr.Row():
                ollama_save_btn = gr.Button("💾 Save Settings", variant="primary")
                ollama_test_btn = gr.Button("🔍 Test Connection")
                ollama_status_btn = gr.Button("📊 Current Status")
            
            ollama_output = gr.Code(label="Result", language="json", lines=10)
            
            def save_ollama_settings(url: str, model: str) -> str:
                """Save Ollama settings to config"""
                config = load_config()
                config["ollama_url"] = url.strip() or "http://localhost:11434"
                config["ollama_model"] = model.strip() or "gemma3:12b"
                save_config(config)
                
                # Update the handler's Ollama manager
                handler = get_handler()
                result = handler.ollama.update_config(url=config["ollama_url"], model=config["ollama_model"])
                result["message"] = "Settings saved to .state/config.json"
                return json.dumps(result, indent=2)
            
            def test_ollama_connection() -> str:
                """Test Ollama connection"""
                handler = get_handler()
                config = handler.ollama.get_config()
                
                # Try to ping Ollama
                try:
                    import subprocess
                    result = subprocess.run(
                        ["curl", "-s", f"{config['base_url']}/api/tags"],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    if result.returncode == 0:
                        try:
                            models = json.loads(result.stdout)
                            return json.dumps({
                                "status": "connected",
                                "url": config["base_url"],
                                "available_models": [m.get("name") for m in models.get("models", [])],
                                "current_model": config["default_model"]
                            }, indent=2)
                        except:
                            return json.dumps({
                                "status": "connected",
                                "url": config["base_url"],
                                "raw_response": result.stdout[:500]
                            }, indent=2)
                    else:
                        return json.dumps({
                            "status": "error",
                            "message": f"Could not connect to Ollama at {config['base_url']}",
                            "hint": "Please ensure Ollama is running. Start with: ollama serve"
                        }, indent=2)
                except Exception as e:
                    return json.dumps({
                        "status": "error",
                        "message": str(e),
                        "hint": "Please ensure Ollama is installed and running"
                    }, indent=2)
            
            def get_ollama_status() -> str:
                """Get current Ollama status"""
                handler = get_handler()
                return json.dumps(handler.ollama.get_config(), indent=2)
            
            ollama_save_btn.click(save_ollama_settings, inputs=[ollama_url, ollama_model], outputs=[ollama_output])
            ollama_test_btn.click(test_ollama_connection, outputs=[ollama_output])
            ollama_status_btn.click(get_ollama_status, outputs=[ollama_output])
            
            gr.Markdown("""
### Popular Models

| Model | Size | Description |
|-------|------|-------------|
| `gemma3:12b` | 12B | Google's latest Gemma model |
| `llama3:8b` | 8B | Meta's Llama 3 |
| `mistral:7b` | 7B | Mistral AI's model |
| `codellama:13b` | 13B | Code-focused Llama |
| `deepseek-coder:6.7b` | 6.7B | DeepSeek Coder |

### MCP Tool Usage

You can also configure Ollama per-call using MCP tools:

```json
// ai_generate with custom URL/model
{"prompt": "Hello", "url": "http://custom:11434", "model": "llama3:8b"}

// ai_get_config - get current config
{}

// ai_set_config - update config
{"url": "http://localhost:11434", "model": "mistral:7b"}
```
            """)
        
        with gr.Tab("🔧 Tool Executor"):
            gr.Markdown("### Execute MCP Tools Directly")
            
            with gr.Row():
                tool_dropdown = gr.Dropdown(
                    label="Select Tool",
                    choices=tool_names,
                    value=tool_names[0] if tool_names else None
                )
                schema_btn = gr.Button("📖 Show Schema")
            
            args_input = gr.Textbox(
                label="Arguments (JSON)",
                placeholder='{"key": "value"} or leave empty for no arguments',
                lines=3
            )
            
            exec_btn = gr.Button("▶️ Execute Tool", variant="primary")
            tool_output = gr.Code(label="Result", language="json", lines=15)
            
            schema_btn.click(get_tool_schema, inputs=[tool_dropdown], outputs=[tool_output])
            exec_btn.click(execute_tool, inputs=[tool_dropdown, args_input], outputs=[tool_output])
        
        with gr.Tab("🧮 Calculator"):
            gr.Markdown("### Advanced Calculator")
            
            with gr.Row():
                calc_input = gr.Textbox(
                    label="Expression",
                    placeholder="e.g., 1 + 1, sin(pi/2), sqrt(2), 50 * 1024"
                )
                calc_btn = gr.Button("Calculate", variant="primary")
            
            calc_output = gr.Code(label="Result", language="json")
            calc_btn.click(run_calculator, inputs=[calc_input], outputs=[calc_output])
            
            gr.Examples(
                examples=[
                    ["1 + 1"],
                    ["sin(pi/2)"],
                    ["sqrt(2)"],
                    ["50 * 1024"],
                    ["log(100)"],
                    ["factorial(10)"],
                ],
                inputs=[calc_input]
            )
            
            gr.Markdown("### Unit Conversion")
            with gr.Row():
                conv_value = gr.Number(label="Value", value=100)
                conv_from = gr.Textbox(label="From Unit", placeholder="e.g., km, GB, hour")
                conv_to = gr.Textbox(label="To Unit", placeholder="e.g., m, MB, min")
            conv_btn = gr.Button("Convert")
            conv_output = gr.Code(label="Result", language="json")
            conv_btn.click(convert_units, inputs=[conv_value, conv_from, conv_to], outputs=[conv_output])
            
            gr.Markdown("### Statistics")
            stats_input = gr.Textbox(label="Data (comma-separated)", placeholder="1, 2, 3, 4, 5")
            stats_btn = gr.Button("Calculate Statistics")
            stats_output = gr.Code(label="Result", language="json")
            stats_btn.click(calculate_statistics, inputs=[stats_input], outputs=[stats_output])
        
        with gr.Tab("💻 System"):
            gr.Markdown("### System Information")
            
            sys_btn = gr.Button("🖥️ Get System Info", variant="primary")
            sys_output = gr.Code(label="System Info", language="json", lines=15)
            sys_btn.click(get_system_info, outputs=[sys_output])
            
            gr.Markdown("### 🔍 Process Search")
            gr.Markdown("""
Search for processes by name or command line. Supports partial matching.

**Examples:** `python`, `chrome`, `vscode`, `node`
            """)
            
            with gr.Row():
                proc_search = gr.Textbox(
                    label="Search Term",
                    placeholder="e.g., python, chrome, vscode (leave empty for all)",
                    scale=3
                )
                proc_sort = gr.Dropdown(
                    label="Sort By",
                    choices=["cpu", "memory", "pid", "name"],
                    value="cpu",
                    scale=1
                )
                proc_limit = gr.Slider(
                    label="Limit",
                    minimum=10,
                    maximum=200,
                    value=50,
                    step=10,
                    scale=1
                )
            
            proc_btn = gr.Button("🔎 Search Processes", variant="primary")
            proc_output = gr.Code(label="Processes", language="json", lines=20)
            proc_btn.click(
                get_process_list,
                inputs=[proc_search, proc_sort, proc_limit],
                outputs=[proc_output]
            )
            
            gr.Examples(
                examples=[
                    ["python", "cpu", 50],
                    ["chrome", "memory", 30],
                    ["", "cpu", 20],  # Top CPU usage
                    ["node", "memory", 50],
                ],
                inputs=[proc_search, proc_sort, proc_limit]
            )
        
        with gr.Tab("📖 About"):
            gr.Markdown(f"""
### About systerd-lite

**systerd-lite** is an AI-Native OS Core that allows LLMs to autonomously 
monitor, control, and optimize Linux systems.

#### Tool Categories ({len(handler.MCP_TOOL_CATEGORIES)} categories, {len(handler.tools)} tools)

{chr(10).join(f"- **{cat}**: {len(tools)} tools" for cat, tools in sorted(handler.MCP_TOOL_CATEGORIES.items()))}

#### Links

- [GitHub Repository](https://github.com/rintaro-s/sisterd_lite)
- [MCP Protocol](https://modelcontextprotocol.io/)

#### Files

| File | Purpose |
|------|---------|
| `app.py` | This Gradio UI (main entry point) |
| `mcp_main.py` | stdio MCP server for external clients |
| `systerd_lite/` | Core module with all tools |
| `.state/` | Persistent configuration and state |

#### License

Apache License 2.0
            """)
    
    return demo


# ===== Main Entry Point =====
if __name__ == "__main__":
    app = create_app()
    
    # Get port from environment (Hugging Face sets $PORT)
    port = int(os.environ.get("PORT", 7860))
    
    print(f"🎛️ systerd-lite Gradio UI starting on port {port}")
    print(f"📁 State directory: {STATE_DIR}")
    print(f"🔧 Tools loaded: {len(get_handler().tools)}")
    
    app.launch(
        server_name="0.0.0.0",
        server_port=port,
        share=False
    )
