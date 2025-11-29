#!/usr/bin/env python3
"""
systerd-lite - AI-Native OS Core (Complete Edition)
All 114 MCP tools + Full system management in one executable

Usage:
    ./systerd-lite.py                    # Start with defaults
    ./systerd-lite.py --port 8089        # Custom HTTP port
    ./systerd-lite.py --gradio 7861      # Enable Gradio UI
    ./systerd-lite.py --no-ui            # Headless mode
    ./systerd-lite.py --debug            # Enable debug logging
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import signal
import sys
import os
from pathlib import Path
from typing import Any, Dict

# Try to use venv first, fall back to system Python
script_dir = Path(__file__).parent.resolve()
venv_python = script_dir / ".venv" / "bin" / "python"
venv_site_packages = script_dir / ".venv" / "lib"

# If venv exists and is not the current interpreter, inject venv into path
if venv_site_packages.exists():
    import site
    site_packages = list(venv_site_packages.glob("python*/site-packages"))
    if site_packages:
        sys.path.insert(0, str(site_packages[0]))

# Add systerd_lite to path
sys.path.insert(0, str(Path(__file__).parent / "systerd_lite"))

try:
    import aiohttp.web
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False
    print("ERROR: aiohttp not available. Install with: pip install aiohttp")
    sys.exit(1)

try:
    from systerd_lite.context import SysterdContext
    from systerd_lite.modes import ModeController, SysterdMode
    from systerd_lite.neurobus import NeuroBus
    from systerd_lite.mcp import MCPHandler
    from systerd_lite.permissions import PermissionManager
except ImportError as e:
    print(f"ERROR: Failed to import systerd modules: {e}")
    print("Make sure systerd_lite/ directory exists with all modules")
    sys.exit(1)

try:
    import gradio as gr
    GRADIO_AVAILABLE = True
except ImportError:
    GRADIO_AVAILABLE = False

# ============================================================================
# LOGGING SETUP
# ============================================================================

class ColoredFormatter(logging.Formatter):
    """Colored log formatter"""
    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m', # Magenta
    }
    RESET = '\033[0m'

    def format(self, record):
        levelname = record.levelname
        if levelname in self.COLORS:
            record.levelname = f"{self.COLORS[levelname]}{levelname}{self.RESET}"
        return super().format(record)

def setup_logging(debug: bool = False):
    """Setup colored logging"""
    level = logging.DEBUG if debug else logging.INFO
    handler = logging.StreamHandler()
    handler.setFormatter(ColoredFormatter(
        '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%H:%M:%S'
    ))
    logging.root.handlers = [handler]
    logging.root.setLevel(level)

logger = logging.getLogger('systerd-lite')

# ============================================================================
# HTTP SERVER
# ============================================================================

class HTTPServer:
    """HTTP server for MCP endpoints"""
    
    def __init__(self, mcp: MCPHandler, neurobus: NeuroBus, 
                 mode_controller: ModeController, permissions: PermissionManager, 
                 port: int):
        self.mcp = mcp
        self.neurobus = neurobus
        self.mode_controller = mode_controller
        self.permissions = permissions
        self.port = port
        self.app = aiohttp.web.Application()
        self._setup_routes()
    
    def _setup_routes(self):
        """Setup HTTP routes"""
        self.app.add_routes([
            # Accept root GET for simple health/info checks and
            # root POST to support clients that POST messages to '/'.
            aiohttp.web.get('/', self.handle_root),
            aiohttp.web.post('/', self.handle_mcp_call),
            aiohttp.web.get('/health', self.handle_health),
            aiohttp.web.get('/mcp/tools', self.handle_mcp_tools),
            aiohttp.web.post('/mcp/call', self.handle_mcp_call),
            aiohttp.web.get('/neurobus', self.handle_neurobus),
            aiohttp.web.get('/mode', self.handle_mode_get),
            aiohttp.web.post('/mode', self.handle_mode_set),
            aiohttp.web.get('/permissions', self.handle_permissions_get),
            aiohttp.web.post('/permissions', self.handle_permissions_set),
        ])
    
    async def handle_health(self, request) -> aiohttp.web.Response:
        """Health check"""
        return aiohttp.web.json_response({
            'status': 'healthy',
            'version': '3.0-complete',
            'tools': len(self.mcp.tools),
            'mode': self.mode_controller.mode.value
        })
    
    async def handle_mcp_tools(self, request) -> aiohttp.web.Response:
        """List all MCP tools"""
        tools = sorted(self.mcp.tools.keys())
        return aiohttp.web.json_response({
            'tools': tools,
            'count': len(tools)
        })
    
    async def handle_mcp_call(self, request) -> aiohttp.web.Response:
        """Execute MCP tool"""
        try:
            data = await request.json()
            if not isinstance(data, dict):
                raise ValueError("MCP request must be a JSON object")

            if 'method' not in data and 'name' in data:
                data = {
                    'jsonrpc': '2.0',
                    'id': data.get('id'),
                    'method': 'tools/call',
                    'params': {
                        'name': data.get('name'),
                        'arguments': data.get('arguments', {}),
                    },
                }

            method = data.get('method')
            if method:
                logger.info(f"JSON-RPC request method={method}")
            mcp_response = await self.mcp.process_request(data)
            return aiohttp.web.json_response(mcp_response)
        
        except json.JSONDecodeError:
            logger.info("Received non-JSON MCP request")
            return aiohttp.web.json_response({'error': 'Invalid JSON'}, status=400)
        except ValueError as e:
            logger.info(f"Invalid MCP request: {e}")
            return aiohttp.web.json_response({'error': str(e)}, status=400)
        except Exception as e:
            logger.error(f"MCP call error: {e}", exc_info=True)
            return aiohttp.web.json_response(
                {'error': str(e)},
                status=500
            )
    
    async def handle_neurobus(self, request) -> aiohttp.web.Response:
        """Query NeuroBus events"""
        limit = int(request.query.get('limit', 100))
        events = list(self.neurobus.query(limit=limit))
        return aiohttp.web.json_response({'events': events})

    async def handle_root(self, request) -> aiohttp.web.Response:
        """Root endpoint: mirror health for simple checks or basic clients

        Some clients (or extensions) attempt to POST to `/` or expect a
        simple health response at `/`. To improve compatibility we accept
        POST at `/` (forwarded to the MCP call handler) and respond to GET
        with the same payload as `/health`.
        """
        if request.method == 'GET':
            return await self.handle_health(request)

        # For POST, attempt to read the body and handle a few common
        # compatibility cases. Log the incoming request payload for debugging.
        try:
            raw = await request.text()
        except Exception:
            raw = ''

        log_payload = raw.strip()
        if log_payload:
            logger.info(f"POST / payload: {log_payload}")
        else:
            logger.info("POST / received empty body")

        # Try to parse JSON and detect JSON-RPC 'initialize' (VS Code expects this)
        try:
            payload = json.loads(raw) if raw else {}
        except Exception:
            payload = None

        if isinstance(payload, dict) and ('method' in payload or 'name' in payload):
            class _FakeReq:
                def __init__(self, payload):
                    self._payload = payload
                async def json(self):
                    return self._payload
            return await self.handle_mcp_call(_FakeReq(payload))

        return aiohttp.web.json_response(
            {'error': 'Unsupported request on /'},
            status=400
        )
    
    async def handle_mode_get(self, request) -> aiohttp.web.Response:
        """Get current mode"""
        return aiohttp.web.json_response({
            'mode': self.mode_controller.mode.value
        })
    
    async def handle_mode_set(self, request) -> aiohttp.web.Response:
        """Set mode"""
        data = await request.json()
        mode = data.get('mode')
        
        try:
            new_mode = SysterdMode(mode)
            self.mode_controller.set_mode(new_mode)
            return aiohttp.web.json_response({
                'status': 'ok',
                'mode': mode
            })
        except ValueError:
            return aiohttp.web.json_response(
                {'error': f'Invalid mode: {mode}'},
                status=400
            )
    
    async def handle_permissions_get(self, request) -> aiohttp.web.Response:
        """Get all permissions"""
        return aiohttp.web.json_response(self.permissions.get_all())
    
    async def handle_permissions_set(self, request) -> aiohttp.web.Response:
        """Set permission"""
        data = await request.json()
        tool = data.get('tool')
        level = data.get('level')
        
        result = self.permissions.set_permission(tool, level)
        return aiohttp.web.json_response(result)
    
    async def start(self):
        """Start HTTP server"""
        runner = aiohttp.web.AppRunner(self.app)
        await runner.setup()
        site = aiohttp.web.TCPSite(runner, '0.0.0.0', self.port)
        await site.start()
        logger.info(f"HTTP server started on port {self.port}")

# ============================================================================
# GRADIO UI (Optional)
# ============================================================================

def create_gradio_ui(mcp: MCPHandler, neurobus: NeuroBus, 
                     mode_controller: ModeController,
                     permissions: PermissionManager, http_port: int, gradio_port: int):
    """Create Gradio UI - Complete systerd-lite Control Panel"""
    if not GRADIO_AVAILABLE:
        logger.warning("Gradio not available. Skipping UI.")
        return None
    
    # Store ports for UI updates
    port_state = {'http': http_port, 'gradio': gradio_port}
    
    with gr.Blocks(title="systerd-lite Control Panel") as demo:
        gr.Markdown("# systerd-lite - AI-Native OS Core Control Panel")
        gr.Markdown(f"Total MCP Tools: {len(mcp.tools)} | HTTP API: http://localhost:{port_state['http']}")
        
        # ================================================================
        # TAB 1: QUICK ACTIONS
        # ================================================================
        with gr.Tab("Quick Actions"):
            gr.Markdown("## Common Operations")
            
            with gr.Row():
                with gr.Column():
                    gr.Markdown("### System Information")
                    sys_info_btn = gr.Button("Get System Info", scale=1)
                    sys_info_output = gr.JSON(label="System Info")
                    
                    async def get_sys_info():
                        return await mcp.call_tool("get_system_info", {})
                    sys_info_btn.click(get_sys_info, outputs=[sys_info_output])
                
                with gr.Column():
                    gr.Markdown("### Running Processes")
                    proc_btn = gr.Button("Get Top 10 Processes", scale=1)
                    proc_output = gr.JSON(label="Processes")
                    
                    async def get_procs():
                        return await mcp.call_tool("get_top_processes", {"limit": 10})
                    proc_btn.click(get_procs, outputs=[proc_output])
                
                with gr.Column():
                    gr.Markdown("### Disk Usage")
                    disk_btn = gr.Button("Get Disk Usage", scale=1)
                    disk_output = gr.JSON(label="Disk Info")
                    
                    async def get_disk():
                        return await mcp.call_tool("get_disk_usage", {"path": "/"})
                    disk_btn.click(get_disk, outputs=[disk_output])
        
        # ================================================================
        # TAB 2: MCP TOOLS EXECUTOR
        # ================================================================
        with gr.Tab("MCP Tools"):
            gr.Markdown("## Execute Any MCP Tool")
            gr.Markdown("Select a tool and provide arguments as JSON. Results appear below.")
            
            tool_select = gr.Dropdown(
                choices=sorted(mcp.tools.keys()),
                label="Select MCP Tool",
                value="list_processes",
                info="Choose the tool to execute"
            )
            
            tool_args = gr.Textbox(
                label="Tool Arguments (JSON format)",
                value='{}',
                lines=4,
                info="Enter arguments as valid JSON. Empty {} means no arguments."
            )
            
            with gr.Row():
                tool_exec_btn = gr.Button("Execute Tool", variant="primary")
                tool_clear_btn = gr.Button("Clear Results")
            
            tool_result = gr.JSON(label="Execution Result")
            
            async def execute_tool(tool_name, args_json):
                try:
                    import json
                    args = json.loads(args_json) if args_json.strip() else {}
                    result = await mcp.call_tool(tool_name, args)
                    return result
                except json.JSONDecodeError as e:
                    return {"error": f"Invalid JSON: {e}"}
                except Exception as e:
                    return {"error": str(e)}
            
            def clear_tool_result():
                return {}
            
            tool_exec_btn.click(
                execute_tool,
                inputs=[tool_select, tool_args],
                outputs=[tool_result]
            )
            tool_clear_btn.click(clear_tool_result, outputs=[tool_result])
        
        # ================================================================
        # TAB 3: SYSTEM ADMINISTRATION
        # ================================================================
        with gr.Tab("System Admin"):
            gr.Markdown("## System Management & Configuration")
            
            with gr.Group():
                gr.Markdown("### Operating Mode")
                gr.Markdown("Control how systerd-lite makes decisions and executes commands.")
                
                current_mode = gr.Textbox(
                    label="Current Mode",
                    value=mode_controller.mode.value,
                    interactive=False,
                    info="Read-only: displays the current operating mode"
                )
                
                new_mode = gr.Radio(
                    choices=["transparent", "hybrid", "dominant"],
                    label="Select New Mode",
                    value=mode_controller.mode.value,
                    info=("transparent: Ask before any action | "
                          "hybrid: Auto-execute safe actions, ask for risky ones | "
                          "dominant: Execute most actions automatically")
                )
                
                mode_set_btn = gr.Button("Apply Mode Change")
                mode_result = gr.Textbox(label="Change Status", interactive=False)
                
                def apply_mode(new_m):
                    try:
                        mode_obj = SysterdMode(new_m)
                        mode_controller.set_mode(mode_obj)
                        return f"Mode successfully changed to: {new_m}", new_m
                    except Exception as e:
                        return f"Error changing mode: {e}", mode_controller.mode.value
                
                mode_set_btn.click(
                    apply_mode,
                    inputs=[new_mode],
                    outputs=[mode_result, current_mode]
                )
            
            with gr.Group():
                gr.Markdown("### Service Management")
                
                service_action = gr.Radio(
                    choices=["list", "start", "stop", "restart", "enable", "disable"],
                    label="Action",
                    value="list",
                    info="Action to perform on systemd services"
                )
                
                service_name = gr.Textbox(
                    label="Service Name",
                    placeholder="e.g., ssh, nginx, systemd-resolved",
                    info="Leave empty for 'list' action"
                )
                
                service_exec_btn = gr.Button("Execute Service Action")
                service_result = gr.JSON(label="Result")
                
                async def manage_service(action, service):
                    if action == "list":
                        return await mcp.call_tool("list_units", {})
                    else:
                        tool_map = {
                            "start": "start_unit",
                            "stop": "stop_unit",
                            "restart": "restart_unit",
                            "enable": "enable_unit",
                            "disable": "disable_unit"
                        }
                        tool_name = tool_map.get(action)
                        if tool_name and service:
                            return await mcp.call_tool(tool_name, {"name": f"{service}.service"})
                        return {"error": f"Cannot {action} without service name"}
                
                service_exec_btn.click(
                    manage_service,
                    inputs=[service_action, service_name],
                    outputs=[service_result]
                )
        
        # ================================================================
        # TAB 4: SECURITY & PERMISSIONS
        # ================================================================
        with gr.Tab("Security"):
            gr.Markdown("## Permission Management & Security Settings")
            
            with gr.Group():
                gr.Markdown("### Tool Permissions")
                gr.Markdown("Control what each MCP tool is allowed to do: disabled, read-only, ask for approval, or automatic.")
                
                perm_tool = gr.Dropdown(
                    choices=sorted(mcp.tools.keys()),
                    label="Select Tool",
                    value="list_processes",
                    info="Choose which tool to configure"
                )
                
                perm_level = gr.Radio(
                    choices=["disabled", "read_only", "ai_ask", "ai_auto"],
                    label="Permission Level",
                    value="ai_auto",
                    info=("disabled: Tool cannot run | "
                          "read_only: Can only query/read, no modifications | "
                          "ai_ask: AI asks before executing | "
                          "ai_auto: AI executes automatically if confident")
                )
                
                perm_set_btn = gr.Button("Set Permission")
                perm_status = gr.Textbox(label="Status", interactive=False)
                
                def set_tool_permission(tool_name, perm):
                    try:
                        result = permissions.set_permission(tool_name, perm)
                        return f"Permission set: {tool_name} = {perm}"
                    except Exception as e:
                        return f"Error: {e}"
                
                perm_set_btn.click(
                    set_tool_permission,
                    inputs=[perm_tool, perm_level],
                    outputs=[perm_status]
                )
            
            with gr.Group():
                gr.Markdown("### All Permissions")
                perm_view_btn = gr.Button("Refresh Permission List")
                perm_all_display = gr.JSON(label="Permission Matrix")
                
                def view_all_perms():
                    return permissions.get_all()
                
                perm_view_btn.click(view_all_perms, outputs=[perm_all_display])
                perm_view_btn.click(view_all_perms, outputs=[perm_all_display])
            
            with gr.Group():
                gr.Markdown("### Security Features")
                
                enable_apparmor = gr.Checkbox(
                    label="Enable AppArmor Enforcement",
                    value=False,
                    info="Enforce AppArmor profiles for system calls"
                )
                
                enable_selinux = gr.Checkbox(
                    label="Enable SELinux Enforcement",
                    value=False,
                    info="Enforce SELinux policies"
                )
                
                security_btn = gr.Button("Apply Security Settings")
                security_result = gr.Textbox(label="Status", interactive=False)
                
                def apply_security(apparmor, selinux):
                    msg = []
                    if apparmor:
                        msg.append("AppArmor enforcement enabled")
                    if selinux:
                        msg.append("SELinux enforcement enabled")
                    return "Security settings updated: " + ", ".join(msg) if msg else "No changes"
                
                security_btn.click(
                    apply_security,
                    inputs=[enable_apparmor, enable_selinux],
                    outputs=[security_result]
                )
        
        # ================================================================
        # TAB 5: MCP TOOL MANAGEMENT
        # ================================================================
        with gr.Tab("MCP Settings"):
            gr.Markdown("## MCP Tool Configuration & Templates")
            gr.Markdown("Manage which MCP tools are enabled and apply configuration templates to quickly configure tool sets.")
            
            with gr.Group():
                gr.Markdown("### Quick Templates")
                gr.Markdown("Apply a predefined template to enable/disable tools by category. Useful for VS Code's MCP tool limit.")
                
                template_select = gr.Radio(
                    choices=["minimal", "monitoring", "development", "security", "full"],
                    label="Select Template",
                    value="development",
                    info=("minimal: Basic monitoring only (13 tools) | "
                          "monitoring: System stats + MCP config (18 tools) | "
                          "development: Dev focused with containers (35 tools) | "
                          "security: Security audit tools (31 tools) | "
                          "full: All 182+ tools enabled")
                )
                
                template_apply_btn = gr.Button("Apply Template", variant="primary")
                template_result = gr.JSON(label="Template Application Result")
                
                async def apply_template(template_name):
                    try:
                        result = await mcp.call_tool("apply_mcp_template", {"template": template_name})
                        return result
                    except Exception as e:
                        return {"error": str(e)}
                
                template_apply_btn.click(
                    apply_template,
                    inputs=[template_select],
                    outputs=[template_result]
                )
            
            with gr.Group():
                gr.Markdown("### Current Configuration")
                
                config_refresh_btn = gr.Button("Refresh MCP Config")
                mcp_config_display = gr.JSON(label="Current MCP Configuration")
                
                async def get_mcp_config():
                    try:
                        return await mcp.call_tool("get_mcp_config", {})
                    except Exception as e:
                        return {"error": str(e)}
                
                config_refresh_btn.click(get_mcp_config, outputs=[mcp_config_display])
            
            with gr.Group():
                gr.Markdown("### Tool List by Category")
                
                category_select = gr.Dropdown(
                    choices=["all", "monitoring", "security", "system", "network", 
                             "container", "user", "storage", "scheduler", "tuning", 
                             "ai", "calculator", "mcp"],
                    label="Filter by Category",
                    value="all"
                )
                
                status_filter = gr.Radio(
                    choices=["all", "enabled", "disabled"],
                    label="Filter by Status",
                    value="all"
                )
                
                tools_list_btn = gr.Button("List Tools")
                tools_list_display = gr.JSON(label="Tools List")
                
                async def list_tools(category, status):
                    try:
                        args = {"status": status}
                        if category != "all":
                            args["category"] = category
                        return await mcp.call_tool("list_mcp_tools", args)
                    except Exception as e:
                        return {"error": str(e)}
                
                tools_list_btn.click(
                    list_tools,
                    inputs=[category_select, status_filter],
                    outputs=[tools_list_display]
                )
            
            with gr.Group():
                gr.Markdown("### Individual Tool Permission")
                
                ind_tool_select = gr.Dropdown(
                    choices=sorted(mcp.tools.keys()),
                    label="Select Tool",
                    value="get_uptime"
                )
                
                ind_perm_select = gr.Radio(
                    choices=["DISABLED", "READ_ONLY", "AI_ASK", "AI_AUTO"],
                    label="Permission Level",
                    value="AI_AUTO",
                    info=("DISABLED: Tool cannot run | "
                          "READ_ONLY: Read-only operations | "
                          "AI_ASK: Ask before executing | "
                          "AI_AUTO: Execute automatically")
                )
                
                ind_perm_btn = gr.Button("Set Tool Permission")
                ind_perm_result = gr.JSON(label="Result")
                
                async def set_individual_permission(tool_name, perm):
                    try:
                        return await mcp.call_tool("set_mcp_tool_permission", {
                            "tool_name": tool_name,
                            "permission": perm
                        })
                    except Exception as e:
                        return {"error": str(e)}
                
                ind_perm_btn.click(
                    set_individual_permission,
                    inputs=[ind_tool_select, ind_perm_select],
                    outputs=[ind_perm_result]
                )
            
            with gr.Group():
                gr.Markdown("### Bulk Tool Actions")
                
                with gr.Row():
                    bulk_category = gr.Dropdown(
                        choices=["monitoring", "security", "system", "network", 
                                 "container", "user", "storage", "scheduler", 
                                 "tuning", "ai", "calculator", "mcp"],
                        label="Category to Modify",
                        value="monitoring"
                    )
                    
                    bulk_action = gr.Radio(
                        choices=["Enable All", "Disable All"],
                        label="Action",
                        value="Enable All"
                    )
                
                bulk_action_btn = gr.Button("Apply Bulk Action")
                bulk_result = gr.JSON(label="Bulk Action Result")
                
                async def bulk_tool_action(category, action):
                    from systerd_lite.permissions import Permission
                    
                    # Get tools in this category
                    tool_list_result = await mcp.call_tool("list_mcp_tools", {"category": category})
                    if "error" in tool_list_result:
                        return tool_list_result
                    
                    target_perm = Permission.AI_AUTO if action == "Enable All" else Permission.DISABLED
                    permissions_batch = {}
                    
                    for tool_info in tool_list_result.get("tools", []):
                        tool_name = tool_info["name"]
                        permissions_batch[tool_name] = target_perm
                    
                    # Save all at once
                    permissions.set_permissions_batch(permissions_batch)
                    
                    return {
                        "category": category,
                        "action": action,
                        "new_permission": target_perm.name,
                        "tools_updated": len(permissions_batch),
                        "tools": list(permissions_batch.keys()),
                        "saved": True
                    }
                
                bulk_action_btn.click(
                    bulk_tool_action,
                    inputs=[bulk_category, bulk_action],
                    outputs=[bulk_result]
                )
            
            with gr.Group():
                gr.Markdown("### Available Templates")
                
                templates_btn = gr.Button("Show Templates")
                templates_display = gr.JSON(label="Template Definitions")
                
                async def show_templates():
                    try:
                        return await mcp.call_tool("get_mcp_templates", {})
                    except Exception as e:
                        return {"error": str(e)}
                
                templates_btn.click(show_templates, outputs=[templates_display])
        
        # ================================================================
        # TAB 6: MONITORING & EVENTS
        # ================================================================
        with gr.Tab("Monitoring"):
            gr.Markdown("## System Event Stream & NeuroBus")
            gr.Markdown("View recent system events and activity logs.")
            
            with gr.Group():
                gr.Markdown("### System Events")
                
                event_limit = gr.Slider(
                    minimum=10,
                    maximum=500,
                    value=50,
                    step=10,
                    label="Number of Events to Display",
                    info="Retrieve the last N system events"
                )
                
                event_filter = gr.Textbox(
                    label="Filter Events (Optional)",
                    placeholder="e.g., system, error, warning",
                    info="Leave empty to show all events"
                )
                
                event_fetch_btn = gr.Button("Fetch Events")
                events_display = gr.JSON(label="System Events")
                
                def fetch_events(limit, filter_str):
                    events = list(neurobus.query(limit=int(limit)))
                    if filter_str and filter_str.strip():
                        filter_lower = filter_str.lower()
                        events = [e for e in events if filter_lower in str(e).lower()]
                    return events
                
                event_fetch_btn.click(
                    fetch_events,
                    inputs=[event_limit, event_filter],
                    outputs=[events_display]
                )
            
            with gr.Group():
                gr.Markdown("### NeuroBus Statistics")
                
                stats_btn = gr.Button("Get Event Statistics")
                stats_display = gr.JSON(label="Statistics")
                
                def get_stats():
                    total = len(list(neurobus.query(limit=10000)))
                    return {
                        "total_events": total,
                        "database": str(neurobus.db_path),
                        "retention_days": 30
                    }
                
                stats_btn.click(get_stats, outputs=[stats_display])
        
        # ================================================================
        # TAB 7: CONFIGURATION
        # ================================================================
        with gr.Tab("Configuration"):
            gr.Markdown("## Server Configuration & Settings")
            gr.Markdown("Configure ports, scheduler, AI integration, and other server parameters.")
            
            with gr.Group():
                gr.Markdown("### Network Ports")
                
                http_port_display = gr.Number(
                    value=port_state['http'],
                    label="HTTP API Port",
                    precision=0,
                    minimum=1024,
                    maximum=65535,
                    info="Port for the HTTP REST API (requires restart)"
                )
                
                gradio_port_display = gr.Number(
                    value=port_state['gradio'],
                    label="Gradio UI Port",
                    precision=0,
                    minimum=1024,
                    maximum=65535,
                    info="Port for this web interface (requires restart)"
                )
                
                port_validate_result = gr.Textbox(label="Port Status", interactive=False)
                
                def check_ports(http_p, grad_p):
                    http_p = int(http_p)
                    grad_p = int(grad_p)
                    if http_p == grad_p:
                        return "ERROR: HTTP and Gradio ports must be different"
                    return f"VALID: HTTP on {http_p}, Gradio on {grad_p} (restart required for changes)"
                
                http_port_display.change(
                    check_ports,
                    inputs=[http_port_display, gradio_port_display],
                    outputs=[port_validate_result]
                )
                gradio_port_display.change(
                    check_ports,
                    inputs=[http_port_display, gradio_port_display],
                    outputs=[port_validate_result]
                )
            
            with gr.Group():
                gr.Markdown("### Task Scheduler")
                
                scheduler_enabled = gr.Checkbox(
                    label="Enable Background Task Scheduler",
                    value=True,
                    info="Runs scheduled tasks in the background"
                )
                
                scheduler_interval = gr.Slider(
                    minimum=5,
                    maximum=60,
                    value=10,
                    step=5,
                    label="Check Interval (seconds)",
                    info="How often to check for scheduled tasks"
                )
            
            with gr.Group():
                gr.Markdown("### Event Database (NeuroBus)")
                
                neurobus_retention = gr.Slider(
                    minimum=1,
                    maximum=90,
                    value=30,
                    step=1,
                    label="Event Retention Period (days)",
                    info="Delete events older than this"
                )
                
                neurobus_max = gr.Slider(
                    minimum=1000,
                    maximum=1000000,
                    value=100000,
                    step=10000,
                    label="Maximum Events to Keep",
                    info="Stop storing events when database reaches this size"
                )
            
            with gr.Group():
                gr.Markdown("### AI Integration (Ollama)")
                
                ai_enabled = gr.Checkbox(
                    label="Enable AI Features",
                    value=True,
                    info="Allow systerd to use Ollama for AI decision-making"
                )
                
                ai_model = gr.Dropdown(
                    choices=["gemma3:12b", "disabled"],
                    label="Ollama Model",
                    value="gemma3:12b",
                    info="Which model to use for AI tasks (or disabled)"
                )
                
                ai_auto_decisions = gr.Checkbox(
                    label="AI Auto-Decisions",
                    value=False,
                    info="Allow AI to make decisions without explicit confirmation"
                )
                
                ai_confidence = gr.Slider(
                    minimum=0.0,
                    maximum=1.0,
                    value=0.8,
                    step=0.05,
                    label="AI Confidence Threshold",
                    info="Minimum confidence level (0.0-1.0) for auto-decisions"
                )
            
            with gr.Group():
                gr.Markdown("### Apply Changes")
                
                config_save_btn = gr.Button("Save Configuration", variant="primary")
                config_result = gr.Textbox(label="Result", interactive=False)
                
                def save_config(sched_en, sched_int, nb_ret, nb_max, ai_en, ai_mod, ai_auto, ai_conf):
                    changes = []
                    if sched_en:
                        changes.append(f"Scheduler enabled (interval: {int(sched_int)}s)")
                    if nb_ret:
                        changes.append(f"Event retention: {int(nb_ret)} days")
                    if ai_en:
                        changes.append(f"AI model: {ai_mod}")
                    
                    msg = "Configuration changes queued:\n" + "\n".join(f"  - {c}" for c in changes)
                    msg += "\n\nNote: Some changes require server restart to take effect"
                    return msg
                
                config_save_btn.click(
                    save_config,
                    inputs=[scheduler_enabled, scheduler_interval, neurobus_retention,
                           neurobus_max, ai_enabled, ai_model, ai_auto_decisions, ai_confidence],
                    outputs=[config_result]
                )
        
        # ================================================================
        # TAB 8: EXAMPLES & DOCUMENTATION
        # ================================================================
        with gr.Tab("Examples"):
            gr.Markdown("## MCP Tool Usage Examples")
            gr.Markdown("Learn how to use common MCP tools with real request/response examples.")
            
            example_tabs = gr.Tabs()
            with example_tabs:
                # Example 1: get_system_info
                with gr.TabItem("System Information"):
                    gr.Markdown("""### get_system_info - Retrieve System Details

**What it does:** Returns information about the operating system and hardware.

**Required arguments:** None

**Example request:**
```json
{
  "name": "get_system_info",
  "arguments": {}
}
```

**Example response:**
```json
{
  "platform": "Linux",
  "platform_release": "6.14.0-33-generic",
  "architecture": "x86_64",
  "hostname": "systerd-server",
  "processor": "Intel(R) Core(TM) i7-9700K CPU @ 3.60GHz",
  "boot_time": 1764222329.0,
  "uptime_seconds": 86400.5
}
```

**Use cases:**
- Verify the server platform before executing platform-specific commands
- Display system information in monitoring dashboards
- Check uptime and boot time for system health analysis
""")
                    ex1_btn = gr.Button("Execute Now")
                    ex1_result = gr.JSON(label="Result")
                    
                    async def ex1():
                        return await mcp.call_tool("get_system_info", {})
                    
                    ex1_btn.click(ex1, outputs=[ex1_result])
                
                # Example 2: get_top_processes
                with gr.TabItem("Process Monitoring"):
                    gr.Markdown("""### get_top_processes - List Resource-Hungry Processes

**What it does:** Returns processes using the most CPU and memory.

**Required arguments:**
- limit: Number of top processes to return (default: 10)

**Example request:**
```json
{
  "name": "get_top_processes",
  "arguments": {
    "limit": 5
  }
}
```

**Example response:**
```json
{
  "processes": [
    {
      "pid": 1234,
      "name": "python",
      "cpu_percent": 25.5,
      "memory_percent": 10.2,
      "memory_mb": 512,
      "status": "running"
    }
  ]
}
```

**Use cases:**
- Identify resource-intensive processes
- Monitor system performance
- Trigger automated scaling or service restarts
""")
                    ex2_btn = gr.Button("Execute Now")
                    ex2_result = gr.JSON(label="Result")
                    
                    async def ex2():
                        return await mcp.call_tool("get_top_processes", {"limit": 5})
                    
                    ex2_btn.click(ex2, outputs=[ex2_result])
                
                # Example 3: list_interfaces
                with gr.TabItem("Network Interfaces"):
                    gr.Markdown("""### list_interfaces - Show Network Adapters

**What it does:** Lists all network interfaces and their IP addresses.

**Required arguments:** None

**Example request:**
```json
{
  "name": "list_interfaces",
  "arguments": {}
}
```

**Example response:**
```json
{
  "interfaces": [
    {
      "name": "eth0",
      "ipv4": "192.168.1.100",
      "ipv6": "fe80::1",
      "status": "UP",
      "mtu": 1500,
      "mac_address": "00:1A:2B:3C:4D:5E"
    },
    {
      "name": "lo",
      "ipv4": "127.0.0.1",
      "ipv6": "::1",
      "status": "UP",
      "mtu": 65536
    }
  ]
}
```

**Use cases:**
- Verify network connectivity
- Configure networking or firewall rules
- Troubleshoot connectivity issues
""")
                    ex3_btn = gr.Button("Execute Now")
                    ex3_result = gr.JSON(label="Result")
                    
                    async def ex3():
                        return await mcp.call_tool("list_interfaces", {})
                    
                    ex3_btn.click(ex3, outputs=[ex3_result])
                
                # Example 4: get_disk_usage
                with gr.TabItem("Disk Usage"):
                    gr.Markdown("""### get_disk_usage - Check Storage Space

**What it does:** Returns storage capacity and usage for a filesystem.

**Required arguments:**
- path: Directory path to check (e.g., "/", "/home")

**Example request:**
```json
{
  "name": "get_disk_usage",
  "arguments": {
    "path": "/"
  }
}
```

**Example response:**
```json
{
  "path": "/",
  "filesystem": "/dev/sda1",
  "total_bytes": 536870912000,
  "used_bytes": 268435456000,
  "free_bytes": 268435456000,
  "percent": 50.0
}
```

**Use cases:**
- Monitor disk space before operations
- Alert when disk usage exceeds thresholds
- Plan storage cleanup activities
""")
                    ex4_btn = gr.Button("Execute Now")
                    ex4_result = gr.JSON(label="Result")
                    
                    async def ex4():
                        return await mcp.call_tool("get_disk_usage", {"path": "/"})
                    
                    ex4_btn.click(ex4, outputs=[ex4_result])
                
                # Example 5: list_units
                with gr.TabItem("Service Status"):
                    gr.Markdown("""### list_units - Show systemd Services

**What it does:** Lists systemd units (services, targets, etc.) and their status.

**Required arguments:** None

**Example request:**
```json
{
  "name": "list_units",
  "arguments": {}
}
```

**Example response:**
```json
{
  "units": [
    {
      "name": "sshd.service",
      "load": "loaded",
      "active": "active",
      "running": "running",
      "description": "OpenSSH server"
    },
    {
      "name": "nginx.service",
      "load": "loaded",
      "active": "inactive",
      "running": "dead"
    }
  ]
}
```

**Use cases:**
- Check if services are running
- Start, stop, or restart services
- Manage service boot behavior
""")
                    ex5_btn = gr.Button("Execute Now")
                    ex5_result = gr.JSON(label="Result")
                    
                    async def ex5():
                        return await mcp.call_tool("list_units", {})
                    
                    ex5_btn.click(ex5, outputs=[ex5_result])
    
    return demo

# ============================================================================
# MAIN APPLICATION
# ============================================================================

class SysterdLite:
    """Main systerd-lite application"""
    
    def __init__(self, state_dir: Path, http_port: int, gradio_port: int, 
                 enable_ui: bool, debug: bool):
        self.state_dir = state_dir
        self.http_port = http_port
        self.gradio_port = gradio_port
        self.enable_ui = enable_ui
        self.debug = debug
        
        # Initialize components
        self.neurobus = NeuroBus(state_dir / 'neurobus.db')
        self.mode_controller = ModeController(
            state_file=state_dir / 'mode.state',
            acl_file=state_dir / 'acl.json'
        )
        self.permissions = PermissionManager(
            config_file=state_dir / 'permissions.json'
        )
        
        # Create context
        self.context = SysterdContext(
            state_dir=state_dir,
            socket_path=state_dir / 'systerd.sock',
            mode_controller=self.mode_controller,
            neurobus=self.neurobus,
            acl_file=state_dir / 'acl.json',
            permission_manager=self.permissions
        )
        
        # Initialize MCP handler (loads all 114 tools)
        self.mcp = MCPHandler(self.context)
        
        # HTTP server
        self.http_server = HTTPServer(
            self.mcp, self.neurobus, self.mode_controller,
            self.permissions, http_port
        )
        
        # Gradio UI (optional)
        self.gradio_demo = None
        if enable_ui:
            self.gradio_demo = create_gradio_ui(
                self.mcp, self.neurobus, self.mode_controller,
                self.permissions, http_port, gradio_port
            )
        
        # Record startup
        self.neurobus.record_event(
            'system/startup',
            {
                'version': '3.0-complete',
                'tools': len(self.mcp.tools),
                'mode': self.mode_controller.mode.value,
                'http_port': http_port,
                'gradio_port': gradio_port if enable_ui else None
            }
        )
        
        logger.info(f"systerd-lite initialized with {len(self.mcp.tools)} tools")
        logger.info(f"State directory: {state_dir}")
    
    async def start(self):
        """Start all services"""
        # Start HTTP server
        await self.http_server.start()
        
        # Start scheduler loop
        logger.info("Starting task scheduler")
        asyncio.create_task(self.mcp.scheduler.run_scheduler(self._execute_scheduled_command))
        
        # Start Gradio UI if enabled
        if self.gradio_demo:
            logger.info(f"Starting Gradio UI on port {self.gradio_port}")
            
            # Launch Gradio in background
            import threading
            def run_gradio():
                try:
                    # Try with show_api parameter (older gradio versions)
                    self.gradio_demo.launch(
                        server_name="0.0.0.0",
                        server_port=self.gradio_port,
                        show_api=False,
                        quiet=True
                    )
                except TypeError:
                    # Fallback for newer gradio versions without show_api
                    self.gradio_demo.launch(
                        server_name="0.0.0.0",
                        server_port=self.gradio_port,
                        quiet=True
                    )
            
            gradio_thread = threading.Thread(target=run_gradio, daemon=True)
            gradio_thread.start()
        
        logger.info("✓ systerd-lite started successfully")
        logger.info(f"  HTTP API: http://localhost:{self.http_port}")
        if self.enable_ui:
            logger.info(f"  Gradio UI: http://localhost:{self.gradio_port}")
    
    async def _execute_scheduled_command(self, command: str):
        """Execute a scheduled command (used by scheduler)"""
        import subprocess
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=300
            )
            logger.info(f"Scheduled command executed: {command[:50]}... (exit={result.returncode})")
            return {
                'status': 'ok',
                'exit_code': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr
            }
        except Exception as e:
            logger.error(f"Scheduled command failed: {e}")
            return {'status': 'error', 'error': str(e)}
    
    async def run_forever(self):
        """Run until interrupted"""
        try:
            while True:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            logger.info("Shutting down gracefully...")
            self.mcp.scheduler.stop_scheduler()

# ============================================================================
# CLI
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='systerd-lite - AI-Native OS Core (Complete Edition)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  ./systerd-lite.py                    # Start with defaults
  ./systerd-lite.py --port 8089        # Custom HTTP port
  ./systerd-lite.py --gradio 7861      # Enable Gradio UI
  ./systerd-lite.py --no-ui            # Headless mode
  ./systerd-lite.py --debug            # Enable debug logging
        """
    )
    
    parser.add_argument('--port', type=int, default=8089,
                        help='HTTP server port (default: 8089)')
    parser.add_argument('--gradio', type=int, default=7861,
                        help='Gradio UI port (default: 7861)')
    parser.add_argument('--no-ui', action='store_true',
                        help='Disable Gradio UI')
    parser.add_argument('--debug', action='store_true',
                        help='Enable debug logging')
    parser.add_argument('--state-dir', type=Path, default=Path('.state'),
                        help='State directory (default: .state)')
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.debug)
    
    # Create state directory
    args.state_dir.mkdir(exist_ok=True)
    
    # Create application
    app = SysterdLite(
        state_dir=args.state_dir,
        http_port=args.port,
        gradio_port=args.gradio,
        enable_ui=(args.gradio is not None or GRADIO_AVAILABLE) and not args.no_ui,
        debug=args.debug
    )
    
    # Setup signal handlers
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    def signal_handler(sig, frame):
        logger.info("Received interrupt signal, shutting down...")
        for task in asyncio.all_tasks(loop):
            task.cancel()
        loop.stop()
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Run
    try:
        loop.run_until_complete(app.start())
        loop.run_until_complete(app.run_forever())
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    finally:
        loop.close()

if __name__ == '__main__':
    main()
