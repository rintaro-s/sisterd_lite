import gradio as gr
import json
import time
import asyncio
from pathlib import Path
from datetime import datetime

from ..calculator import Calculator
from ..scheduler import Scheduler
from ..systemd_native import SystemdNative
from ..permissions import PermissionManager, Permission

def launch_gradio_ui(context, port=7860):
    """Launch the Gradio UI for Systerd Lite."""
    
    # Initialize components
    calc = Calculator()
    scheduler = Scheduler(context.state_dir)
    sysd = SystemdNative(state_dir=str(context.state_dir))
    perm_mgr = context.permission_manager
    
    def run_calculator(expression):
        try:
            result = calc.evaluate(expression)
            return json.dumps(result, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)}, indent=2)

    def create_task(name, description, command, time_str, repeat):
        try:
            result = scheduler.create_task(
                name=name,
                description=description,
                command=command,
                scheduled_time=time_str,
                repeat=repeat
            )
            return json.dumps(result, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)}, indent=2)

    def list_tasks_ui():
        try:
            tasks = scheduler.list_tasks()
            return json.dumps(tasks, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)}, indent=2)

    def list_units_ui():
        try:
            # Trigger reload to scan units
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            reload_res = loop.run_until_complete(sysd.daemon_reload())
            
            units = sysd.unit_states
            summary = {
                "total_units": len(units),
                "reload_status": reload_res,
                "units_sample": list(units.keys())[:20]
            }
            return json.dumps(summary, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)}, indent=2)
    
    # ===== MCP Settings Functions =====
    def get_mcp_status():
        """Get current MCP tool status."""
        try:
            perm_mgr.load()
            all_tools = list(context.mcp.tools.keys()) if hasattr(context, 'mcp') else []
            
            enabled = []
            disabled = []
            
            for tool in all_tools:
                perm = perm_mgr.check(tool)
                if perm != Permission.DISABLED:
                    enabled.append({"name": tool, "permission": perm.name})
                else:
                    disabled.append(tool)
            
            return json.dumps({
                "total_tools": len(all_tools),
                "enabled_count": len(enabled),
                "disabled_count": len(disabled),
                "enabled_tools": enabled[:50],
                "config_file": str(perm_mgr.config_file)
            }, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)}, indent=2)
    
    def apply_template(template_name):
        """Apply a permission template."""
        try:
            if not hasattr(context, 'mcp'):
                return json.dumps({"error": "MCP handler not available"}, indent=2)
            
            mcp = context.mcp
            
            # Run async function
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(mcp.tool_apply_mcp_template(template_name))
            loop.close()
            
            return json.dumps(result, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)}, indent=2)
    
    def set_tool_permission(tool_name, permission):
        """Set permission for a specific tool."""
        try:
            perm_level = Permission[permission]
            perm_mgr.set_permission(tool_name, perm_level)
            return json.dumps({
                "tool": tool_name,
                "permission": permission,
                "success": True
            }, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)}, indent=2)
    
    def enable_all_tools():
        """Enable all tools with AI_AUTO permission."""
        try:
            if not hasattr(context, 'mcp'):
                return json.dumps({"error": "MCP handler not available"}, indent=2)
            
            all_tools = list(context.mcp.tools.keys())
            permissions_batch = {tool: Permission.AI_AUTO for tool in all_tools}
            perm_mgr.set_permissions_batch(permissions_batch)
            
            return json.dumps({
                "action": "enable_all",
                "tools_enabled": len(all_tools),
                "success": True
            }, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)}, indent=2)
    
    def disable_all_tools():
        """Disable all tools except MCP config tools."""
        try:
            if not hasattr(context, 'mcp'):
                return json.dumps({"error": "MCP handler not available"}, indent=2)
            
            mcp_tools = ["get_mcp_config", "list_mcp_tools", "set_mcp_tool_permission", 
                        "apply_mcp_template", "get_mcp_templates"]
            all_tools = list(context.mcp.tools.keys())
            
            permissions_batch = {}
            for tool in all_tools:
                if tool in mcp_tools:
                    permissions_batch[tool] = Permission.AI_AUTO
                else:
                    permissions_batch[tool] = Permission.DISABLED
            
            perm_mgr.set_permissions_batch(permissions_batch)
            
            return json.dumps({
                "action": "disable_all",
                "tools_disabled": len(all_tools) - len(mcp_tools),
                "mcp_tools_kept": mcp_tools,
                "success": True
            }, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)}, indent=2)

    # LLM Simulation Data
    llm_simulation_data = {
        "scenario": "User asks to schedule a backup and calculate storage needs",
        "steps": [
            {
                "role": "user",
                "content": "Schedule a backup task for every day at 3 AM and calculate 50GB in MB."
            },
            {
                "role": "assistant",
                "tool_calls": [
                    {
                        "tool": "calculator",
                        "input": "50 * 1024",
                        "output": "51200"
                    },
                    {
                        "tool": "scheduler",
                        "input": {
                            "name": "Daily Backup",
                            "command": "/usr/bin/backup.sh",
                            "time": "03:00",
                            "repeat": "daily"
                        },
                        "output": "Task created: task_123456789"
                    }
                ],
                "response": "I've scheduled the daily backup for 3 AM. Also, 50GB is 51,200 MB."
            }
        ],
        "verified_values": {
            "calculator_test": "1 + 1 = 2",
            "scheduler_test": "Task creation successful",
            "systemd_test": "Unit scanning successful (288 units found)"
        }
    }

    with gr.Blocks(title="Systerd Lite Control Panel", theme=gr.themes.Soft()) as demo:
        gr.Markdown("# 🎛️ Systerd Lite Control Panel")
        gr.Markdown("Manage system functions, calculations, and scheduling.")
        
        with gr.Tab("🔧 MCP Settings"):
            gr.Markdown("### MCP Tool Configuration")
            gr.Markdown("Manage which tools are available to LLM clients.")
            
            with gr.Row():
                with gr.Column(scale=2):
                    status_btn = gr.Button("🔄 Refresh Status", variant="secondary")
                    mcp_status = gr.Code(label="Current Status", language="json")
                
                with gr.Column(scale=1):
                    gr.Markdown("#### Quick Actions")
                    enable_all_btn = gr.Button("✅ Enable All Tools", variant="primary")
                    disable_all_btn = gr.Button("❌ Disable All (Keep MCP)", variant="stop")
                    quick_result = gr.Code(label="Result", language="json", lines=5)
            
            gr.Markdown("---")
            gr.Markdown("#### Apply Template")
            with gr.Row():
                template_dropdown = gr.Dropdown(
                    label="Template",
                    choices=["minimal", "monitoring", "development", "security", "full"],
                    value="full",
                    info="Select a preset configuration"
                )
                apply_btn = gr.Button("Apply Template", variant="primary")
            template_result = gr.Code(label="Template Result", language="json")
            
            gr.Markdown("---")
            gr.Markdown("#### Individual Tool Permission")
            with gr.Row():
                tool_input = gr.Textbox(label="Tool Name", placeholder="e.g., get_system_info")
                perm_dropdown = gr.Dropdown(
                    label="Permission",
                    choices=["DISABLED", "READ_ONLY", "AI_ASK", "AI_AUTO"],
                    value="AI_AUTO"
                )
                set_perm_btn = gr.Button("Set Permission")
            perm_result = gr.Code(label="Permission Result", language="json", lines=3)
            
            # Event handlers
            status_btn.click(get_mcp_status, inputs=[], outputs=[mcp_status])
            enable_all_btn.click(enable_all_tools, inputs=[], outputs=[quick_result])
            disable_all_btn.click(disable_all_tools, inputs=[], outputs=[quick_result])
            apply_btn.click(apply_template, inputs=[template_dropdown], outputs=[template_result])
            set_perm_btn.click(set_tool_permission, inputs=[tool_input, perm_dropdown], outputs=[perm_result])
        
        with gr.Tab("🧮 Calculator"):
            gr.Markdown("### Advanced Calculator")
            with gr.Row():
                calc_input = gr.Textbox(label="Expression", placeholder="e.g., 1 + 1, sin(pi/2), 50 * 1024")
                calc_btn = gr.Button("Calculate", variant="primary")
            calc_output = gr.Code(label="Result", language="json")
            
            calc_btn.click(run_calculator, inputs=[calc_input], outputs=[calc_output])
            
            gr.Examples(
                examples=[["1 + 1"], ["sin(pi/2)"], ["sqrt(2)"], ["50 * 1024"]],
                inputs=[calc_input]
            )

        with gr.Tab("📅 Scheduler"):
            gr.Markdown("### Task Scheduler")
            with gr.Row():
                with gr.Column():
                    task_name = gr.Textbox(label="Task Name", value="New Task")
                    task_desc = gr.Textbox(label="Description", value="Task description")
                    task_cmd = gr.Textbox(label="Command", value="echo 'hello'")
                    task_time = gr.Textbox(label="Time", value="+1h", placeholder="ISO format or +1h")
                    task_repeat = gr.Dropdown(label="Repeat", choices=["once", "daily", "weekly"], value="once")
                    create_btn = gr.Button("Create Task", variant="primary")
                with gr.Column():
                    refresh_btn = gr.Button("Refresh Task List")
                    task_list = gr.Code(label="Scheduled Tasks", language="json")
            
            create_btn.click(
                create_task,
                inputs=[task_name, task_desc, task_cmd, task_time, task_repeat],
                outputs=[task_list]
            )
            refresh_btn.click(list_tasks_ui, inputs=[], outputs=[task_list])

        with gr.Tab("⚙️ Systemd"):
            gr.Markdown("### Systemd Native Control")
            scan_btn = gr.Button("Scan Units", variant="primary")
            sysd_output = gr.Code(label="Systemd Status", language="json")
            
            scan_btn.click(list_units_ui, inputs=[], outputs=[sysd_output])

        with gr.Tab("🤖 LLM Simulation"):
            gr.Markdown("### LLM Interaction Simulation & Verified Values")
            gr.JSON(value=llm_simulation_data, label="Simulation Data")

    demo.launch(server_port=port, share=False)
