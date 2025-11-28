import gradio as gr
import json
import time
from pathlib import Path
from datetime import datetime

from ..calculator import Calculator
from ..scheduler import Scheduler
from ..systemd_native import SystemdNative

def launch_gradio_ui(context, port=7860):
    """Launch the Gradio UI for Systerd Lite."""
    
    # Initialize components
    calc = Calculator()
    scheduler = Scheduler(context.state_dir)
    sysd = SystemdNative(state_dir=str(context.state_dir))
    
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
            import asyncio
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
