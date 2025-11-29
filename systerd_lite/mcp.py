"""
MCP (Model Context Protocol) implementation for systerd.
Exposes system control and monitoring tools to LLMs.
"""

from __future__ import annotations

import json
import logging
import traceback
import os
import pwd
import grp
import subprocess
import psutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set
from urllib.parse import unquote, urlparse

from .context import SysterdContext
from .sensors import SystemSensors
from .tuner import SystemTuner
from .mcp_extended import ExtendedMCPTools
from .calculator import Calculator
from .scheduler import Scheduler
from .container import ContainerManager
from .ollama import OllamaManager
from .exceptions import (
    SysterdError,
    MCPError,
    ProcessError,
    ServiceError,
    ErrorCode,
    safe_execute,
    format_exception_details,
)

logger = logging.getLogger(__name__)


class MCPTool:
    def __init__(
        self,
        name: str,
        description: str,
        handler: Callable[..., Any],
        parameters: Dict[str, Any],
    ):
        self.name = name
        self.description = description
        self.handler = handler
        self.parameters = parameters

    def to_schema(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.parameters,
        }


class MCPHandler:
    def __init__(self, context: SysterdContext):
        self.context = context
        self.tools: Dict[str, MCPTool] = {}
        self.sensors = SystemSensors()
        self.tuner = SystemTuner()
        self.extended = ExtendedMCPTools(context)
        self.calculator = Calculator()
        self.scheduler = Scheduler(context.state_dir)
        self.container = ContainerManager()
        self.ollama = OllamaManager()
        self.workspace_root = Path(__file__).resolve().parents[1]
        self._subscriptions: Dict[str, Set[str]] = {}
        self._resources: List[Dict[str, Any]] = []
        self._resource_by_uri: Dict[str, Dict[str, Any]] = {}
        self._resource_templates: List[Dict[str, Any]] = []
        self._register_tools()
        self._setup_resources()

    def _register_tools(self):
        self.register_tool(
            "list_processes",
            "List running processes with details",
            self.tool_list_processes,
            {
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "description": "Max number of processes to return"},
                    "sort_by": {"type": "string", "enum": ["cpu", "memory", "pid"], "default": "cpu"},
                },
            },
        )
        self.register_tool(
            "manage_service",
            "Start, stop, or restart a systemd service",
            self.tool_manage_service,
            {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["start", "stop", "restart", "status"]},
                    "unit": {"type": "string", "description": "Name of the systemd unit (e.g. nginx.service)"},
                },
                "required": ["action", "unit"],
            },
        )
        self.register_tool(
            "read_neurobus",
            "Query the NeuroBus (system event log)",
            self.tool_read_neurobus,
            {
                "type": "object",
                "properties": {
                    "topic": {"type": "string", "description": "Filter by topic"},
                    "kind": {"type": "string", "description": "Filter by kind (event, command, etc)"},
                    "limit": {"type": "integer", "default": 50},
                },
            },
        )
        self.register_tool(
            "set_mode",
            "Change systerd operation mode",
            self.tool_set_mode,
            {
                "type": "object",
                "properties": {
                    "mode": {"type": "string", "enum": ["transparent", "hybrid", "dominant"]},
                },
                "required": ["mode"],
            },
        )
        self.register_tool(
            "get_mode",
            "Get current systerd operation mode",
            self.tool_get_mode,
            {"type": "object", "properties": {}},
        )
        self.register_tool(
            "get_permissions",
            "Get current permission configuration",
            self.tool_get_permissions,
            {"type": "object", "properties": {}},
        )
        self.register_tool(
            "list_devices",
            "List connected devices (e.g. ESP32)",
            self.tool_list_devices,
            {
                "type": "object",
                "properties": {},
            },
        )
        self.register_tool(
            "control_device",
            "Send a command to a connected device",
            self.tool_control_device,
            {
                "type": "object",
                "properties": {
                    "device_id": {"type": "string"},
                    "command": {"type": "string"},
                    "params": {"type": "object"},
                },
                "required": ["device_id", "command"],
            },
        )
        # ===== NEW: System Observation Tools =====
        self.register_tool(
            "get_system_metrics",
            "Get comprehensive system metrics (CPU, memory, disk, network, sensors)",
            self.tool_get_system_metrics,
            {"type": "object", "properties": {}},
        )
        self.register_tool(
            "get_service_health",
            "Get health status of a systemd service (restart count, failures)",
            self.tool_get_service_health,
            {
                "type": "object",
                "properties": {"unit": {"type": "string"}},
                "required": ["unit"],
            },
        )
        self.register_tool(
            "read_journald",
            "Read journald logs with filtering",
            self.tool_read_journald,
            {
                "type": "object",
                "properties": {
                    "unit": {"type": "string"},
                    "priority": {"type": "integer", "minimum": 0, "maximum": 7},
                    "lines": {"type": "integer", "default": 50},
                },
            },
        )
        # ===== NEW: System Tuning Tools =====
        self.register_tool(
            "tune_process_priority",
            "Set process nice level (-20 to 19, lower = higher priority)",
            self.tool_tune_process_priority,
            {
                "type": "object",
                "properties": {
                    "pid": {"type": "integer"},
                    "nice": {"type": "integer", "minimum": -20, "maximum": 19},
                },
                "required": ["pid", "nice"],
            },
        )
        self.register_tool(
            "set_cpu_governor",
            "Set CPU frequency governor (powersave, performance, etc.)",
            self.tool_set_cpu_governor,
            {
                "type": "object",
                "properties": {
                    "governor": {"type": "string", "enum": ["powersave", "performance", "ondemand", "conservative", "schedutil"]},
                },
                "required": ["governor"],
            },
        )
        self.register_tool(
            "get_sysctl",
            "Read a sysctl kernel parameter",
            self.tool_get_sysctl,
            {
                "type": "object",
                "properties": {"key": {"type": "string"}},
                "required": ["key"],
            },
        )
        self.register_tool(
            "set_sysctl",
            "Write a sysctl kernel parameter (requires root)",
            self.tool_set_sysctl,
            {
                "type": "object",
                "properties": {
                    "key": {"type": "string"},
                    "value": {"type": "string"},
                },
                "required": ["key", "value"],
            },
        )
        self.register_tool(
            "set_io_scheduler",
            "Set I/O scheduler for a block device",
            self.tool_set_io_scheduler,
            {
                "type": "object",
                "properties": {
                    "device": {"type": "string", "description": "Block device name (e.g. sda, nvme0n1)"},
                    "scheduler": {"type": "string", "enum": ["none", "mq-deadline", "kyber", "bfq"]},
                },
                "required": ["device", "scheduler"],
            },
        )
        
        # ===== CALCULATOR TOOLS (8 tools) =====
        self.register_tool(
            "calculate",
            "Evaluate mathematical expressions (supports: +, -, *, /, **, sqrt, sin, cos, tan, log, ln, etc.)",
            self.tool_calculate,
            {
                "type": "object",
                "properties": {"expression": {"type": "string", "description": "Mathematical expression to evaluate"}},
                "required": ["expression"],
            },
        )
        self.register_tool(
            "convert_units",
            "Convert between units (length, weight, temperature, data, time)",
            self.tool_convert_units,
            {
                "type": "object",
                "properties": {
                    "value": {"type": "number"},
                    "from_unit": {"type": "string"},
                    "to_unit": {"type": "string"},
                    "category": {"type": "string", "enum": ["length", "weight", "temperature", "data", "time"]},
                },
                "required": ["value", "from_unit", "to_unit"],
            },
        )
        self.register_tool(
            "matrix_operation",
            "Perform matrix operations (add, subtract, multiply, transpose, determinant, inverse)",
            self.tool_matrix_operation,
            {
                "type": "object",
                "properties": {
                    "operation": {"type": "string", "enum": ["add", "subtract", "multiply", "transpose", "determinant", "inverse"]},
                    "matrix_a": {"type": "array", "items": {"type": "array", "items": {"type": "number"}}},
                    "matrix_b": {"type": "array", "items": {"type": "array", "items": {"type": "number"}}},
                },
                "required": ["operation", "matrix_a"],
            },
        )
        self.register_tool(
            "statistics",
            "Calculate statistical measures (mean, median, stdev, variance, etc.)",
            self.tool_statistics,
            {
                "type": "object",
                "properties": {"data": {"type": "array", "items": {"type": "number"}}},
                "required": ["data"],
            },
        )
        self.register_tool(
            "solve_equation",
            "Solve algebraic equations symbolically",
            self.tool_solve_equation,
            {
                "type": "object",
                "properties": {
                    "equation": {"type": "string", "description": "Equation to solve (e.g., '2*x + 3 = 7')"},
                    "variable": {"type": "string", "default": "x"},
                },
                "required": ["equation"],
            },
        )
        self.register_tool(
            "convert_base",
            "Convert numbers between different bases (2-36)",
            self.tool_convert_base,
            {
                "type": "object",
                "properties": {
                    "number": {"type": "string"},
                    "from_base": {"type": "integer", "minimum": 2, "maximum": 36},
                    "to_base": {"type": "integer", "minimum": 2, "maximum": 36},
                },
                "required": ["number", "from_base", "to_base"],
            },
        )
        
        # ===== SCHEDULER TOOLS (10 tools) =====
        self.register_tool(
            "create_task",
            "Create a scheduled task",
            self.tool_create_task,
            {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "description": {"type": "string"},
                    "command": {"type": "string"},
                    "scheduled_time": {"type": "string", "description": "ISO format or relative time (+1h, +30m, +1d)"},
                    "repeat": {"type": "string", "enum": ["once", "daily", "weekly", "monthly", "custom"], "default": "once"},
                    "repeat_interval": {"type": "integer", "description": "For custom repeats, interval in seconds"},
                    "max_runs": {"type": "integer", "description": "Maximum number of runs (for repeating tasks)"},
                },
                "required": ["name", "description", "command", "scheduled_time"],
            },
        )
        self.register_tool(
            "list_tasks",
            "List scheduled tasks with optional filtering",
            self.tool_list_tasks,
            {
                "type": "object",
                "properties": {
                    "status": {"type": "string", "enum": ["pending", "running", "completed", "failed", "cancelled"]},
                    "enabled": {"type": "boolean"},
                },
            },
        )
        self.register_tool(
            "get_task",
            "Get detailed information about a specific task",
            self.tool_get_task,
            {
                "type": "object",
                "properties": {"task_id": {"type": "string"}},
                "required": ["task_id"],
            },
        )
        self.register_tool(
            "update_task",
            "Update task properties",
            self.tool_update_task,
            {
                "type": "object",
                "properties": {
                    "task_id": {"type": "string"},
                    "updates": {"type": "object"},
                },
                "required": ["task_id", "updates"],
            },
        )
        self.register_tool(
            "cancel_task",
            "Cancel a scheduled task",
            self.tool_cancel_task,
            {
                "type": "object",
                "properties": {"task_id": {"type": "string"}},
                "required": ["task_id"],
            },
        )
        self.register_tool(
            "delete_task",
            "Delete a task permanently",
            self.tool_delete_task,
            {
                "type": "object",
                "properties": {"task_id": {"type": "string"}},
                "required": ["task_id"],
            },
        )
        self.register_tool(
            "create_reminder",
            "Create a simple reminder",
            self.tool_create_reminder,
            {
                "type": "object",
                "properties": {
                    "message": {"type": "string"},
                    "remind_at": {"type": "string", "description": "ISO format or relative time (+1h, +30m, +1d)"},
                },
                "required": ["message", "remind_at"],
            },
        )
        self.register_tool(
            "get_upcoming_tasks",
            "Get upcoming scheduled tasks",
            self.tool_get_upcoming_tasks,
            {
                "type": "object",
                "properties": {"limit": {"type": "integer", "default": 10}},
            },
        )
        
        # ===== CONTAINER TOOLS (10 tools) =====
        self.register_tool(
            "create_python_container",
            "Create a Python container for isolated execution",
            self.tool_create_python_container,
            {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "python_version": {"type": "string", "enum": ["3.9", "3.10", "3.11", "3.12"], "default": "3.11"},
                    "packages": {"type": "array", "items": {"type": "string"}},
                    "persistent": {"type": "boolean", "default": False},
                },
                "required": ["name"],
            },
        )
        self.register_tool(
            "execute_code",
            "Execute Python code in a container",
            self.tool_execute_code,
            {
                "type": "object",
                "properties": {
                    "container_name": {"type": "string"},
                    "code": {"type": "string"},
                    "timeout": {"type": "integer", "default": 30},
                },
                "required": ["container_name", "code"],
            },
        )
        self.register_tool(
            "execute_script",
            "Execute a Python script file in a container",
            self.tool_execute_script,
            {
                "type": "object",
                "properties": {
                    "container_name": {"type": "string"},
                    "script_path": {"type": "string"},
                    "args": {"type": "array", "items": {"type": "string"}},
                    "timeout": {"type": "integer", "default": 30},
                },
                "required": ["container_name", "script_path"],
            },
        )
        self.register_tool(
            "list_containers",
            "List all managed Python containers",
            self.tool_list_containers,
            {"type": "object"},
        )
        self.register_tool(
            "stop_container",
            "Stop a running container",
            self.tool_stop_container,
            {
                "type": "object",
                "properties": {"container_name": {"type": "string"}},
                "required": ["container_name"],
            },
        )
        self.register_tool(
            "remove_container",
            "Remove a container permanently",
            self.tool_remove_container,
            {
                "type": "object",
                "properties": {"container_name": {"type": "string"}},
                "required": ["container_name"],
            },
        )
        self.register_tool(
            "install_container_packages",
            "Install additional packages in a running container",
            self.tool_install_container_packages,
            {
                "type": "object",
                "properties": {
                    "container_name": {"type": "string"},
                    "packages": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["container_name", "packages"],
            },
        )
        self.register_tool(
            "get_container_info",
            "Get detailed container information",
            self.tool_get_container_info,
            {
                "type": "object",
                "properties": {"container_name": {"type": "string"}},
                "required": ["container_name"],
            },
        )
        
        # ===== OLLAMA AI TOOLS (6 tools) =====
        self.register_tool(
            "ai_generate",
            "Generate text using Ollama AI",
            self.tool_ai_generate,
            {
                "type": "object",
                "properties": {
                    "prompt": {"type": "string"},
                    "model": {"type": "string", "enum": ["gemma3:12b"], "default": "gemma3:12b"},
                    "system": {"type": "string"},
                    "temperature": {"type": "number", "minimum": 0.0, "maximum": 2.0, "default": 0.7},
                },
                "required": ["prompt"],
            },
        )
        self.register_tool(
            "ai_chat",
            "Chat with Ollama AI",
            self.tool_ai_chat,
            {
                "type": "object",
                "properties": {
                    "messages": {"type": "array", "items": {"type": "object"}},
                    "model": {"type": "string", "enum": ["gemma3:12b"], "default": "gemma3:12b"},
                    "temperature": {"type": "number", "minimum": 0.0, "maximum": 2.0, "default": 0.7},
                },
                "required": ["messages"],
            },
        )
        self.register_tool(
            "ai_analyze_issue",
            "Analyze system issue using AI",
            self.tool_ai_analyze_issue,
            {
                "type": "object",
                "properties": {
                    "issue": {"type": "string"},
                    "context": {"type": "object"},
                },
                "required": ["issue"],
            },
        )
        self.register_tool(
            "ai_suggest_optimization",
            "Get AI suggestions for system optimization",
            self.tool_ai_suggest_optimization,
            {
                "type": "object",
                "properties": {
                    "metrics": {"type": "object"},
                },
            },
        )
        self.register_tool(
            "ai_set_model",
            "Set default AI model",
            self.tool_ai_set_model,
            {
                "type": "object",
                "properties": {
                    "model": {"type": "string", "enum": ["gemma3:12b"]},
                },
                "required": ["model"],
            },
        )
        self.register_tool(
            "ai_list_models",
            "List available AI models",
            self.tool_ai_list_models,
            {"type": "object"},
        )
        
        # ===== ADDITIONAL MONITORING TOOLS =====
        self.register_tool("get_cpu_info", "Get detailed CPU information", self.tool_get_cpu_info, {"type": "object"})
        self.register_tool("get_memory_info", "Get memory usage information", self.tool_get_memory_info, {"type": "object"})
        self.register_tool("get_temperature", "Get system temperature sensors", self.tool_get_temperature, {"type": "object"})
        self.register_tool("get_battery_status", "Get battery status", self.tool_get_battery_status, {"type": "object"})
        self.register_tool("get_top_processes", "Get top processes by resource usage", self.tool_get_top_processes, {"type": "object", "properties": {"limit": {"type": "integer"}}})
        self.register_tool("get_zombie_processes", "Get zombie processes", self.tool_get_zombie_processes, {"type": "object"})
        self.register_tool("get_system_info", "Get comprehensive system information", self.tool_get_system_info, {"type": "object"})
        
        # ===== ADDITIONAL SYSTEM TOOLS =====
        self.register_tool("get_environment_variables", "Get environment variables", self.tool_get_environment_variables, {"type": "object"})
        self.register_tool("get_kernel_modules", "Get loaded kernel modules", self.tool_get_kernel_modules, {"type": "object"})
        self.register_tool("get_hardware_info", "Get hardware information", self.tool_get_hardware_info, {"type": "object"})
        self.register_tool("get_pci_devices", "Get PCI devices", self.tool_get_pci_devices, {"type": "object"})
        self.register_tool("get_usb_devices", "Get USB devices", self.tool_get_usb_devices, {"type": "object"})
        self.register_tool("get_cron_jobs", "Get cron jobs", self.tool_get_cron_jobs, {"type": "object"})
        
        # ===== SECURITY TOOLS (7) =====
        self.register_tool("get_selinux_status", "Get SELinux status", self.tool_get_selinux_status, {"type": "object"})
        self.register_tool("get_apparmor_status", "Get AppArmor status", self.tool_get_apparmor_status, {"type": "object"})
        self.register_tool("list_sudo_rules", "List sudo rules", self.tool_list_sudo_rules, {"type": "object"})
        self.register_tool("audit_permissions", "Audit file/directory permissions", self.tool_audit_permissions, {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]})
        self.register_tool("scan_suid_files", "Scan for SUID/SGID files", self.tool_scan_suid_files, {"type": "object"})
        self.register_tool("get_failed_logins", "Get failed login attempts", self.tool_get_failed_logins, {"type": "object", "properties": {"limit": {"type": "integer"}}})
        self.register_tool("get_security_updates", "Get available security updates", self.tool_get_security_updates, {"type": "object"})
        
        # ===== SYSTEM INFO TOOLS (3) =====
        self.register_tool("list_sessions", "List active user sessions", self.tool_list_sessions, {"type": "object"})
        self.register_tool("get_boot_time", "Get system boot time", self.tool_get_boot_time, {"type": "object"})
        self.register_tool("get_system_state", "Get systemd system state", self.tool_get_system_state, {"type": "object"})
        
        # ===== LOGGING TOOLS (3) =====
        self.register_tool("get_log_size", "Get total log file sizes", self.tool_get_log_size, {"type": "object", "properties": {"log_path": {"type": "string"}}})
        self.register_tool("get_kernel_logs", "Get kernel logs (dmesg)", self.tool_get_kernel_logs, {"type": "object", "properties": {"lines": {"type": "integer"}}})
        self.register_tool("search_logs", "Search in log files", self.tool_search_logs, {"type": "object", "properties": {"pattern": {"type": "string"}, "log_file": {"type": "string"}, "limit": {"type": "integer"}}, "required": ["pattern"]})
        
        # ===== USER MANAGEMENT TOOLS (3) =====
        self.register_tool("get_group_info", "Get information about a group", self.tool_get_group_info, {"type": "object", "properties": {"groupname": {"type": "string"}}, "required": ["groupname"]})
        self.register_tool("list_logged_users", "List currently logged in users", self.tool_list_logged_users, {"type": "object"})
        self.register_tool("get_user_processes", "Get processes owned by a user", self.tool_get_user_processes, {"type": "object", "properties": {"username": {"type": "string"}}, "required": ["username"]})
        
        # ===== STORAGE TOOL (1) =====
        self.register_tool("get_smart_status", "Get SMART status of a disk", self.tool_get_smart_status, {"type": "object", "properties": {"device": {"type": "string"}}})
        
        # ===== MCP CONFIGURATION TOOLS (5) =====
        self.register_tool(
            "get_mcp_config",
            "Get current MCP server configuration including enabled tools, permissions, and mode settings",
            self.tool_get_mcp_config,
            {"type": "object"}
        )
        self.register_tool(
            "list_mcp_tools",
            "List all available MCP tools with their status (enabled/disabled/permission level)",
            self.tool_list_mcp_tools,
            {
                "type": "object",
                "properties": {
                    "category": {"type": "string", "description": "Filter by category (monitoring, security, system, container, network, etc.)"},
                    "status": {"type": "string", "enum": ["enabled", "disabled", "all"], "default": "all"}
                }
            }
        )
        self.register_tool(
            "set_mcp_tool_permission",
            "Set permission level for a specific MCP tool",
            self.tool_set_mcp_tool_permission,
            {
                "type": "object",
                "properties": {
                    "tool_name": {"type": "string", "description": "Name of the tool"},
                    "permission": {"type": "string", "enum": ["DISABLED", "READ_ONLY", "AI_ASK", "AI_AUTO"]}
                },
                "required": ["tool_name", "permission"]
            }
        )
        self.register_tool(
            "apply_mcp_template",
            "Apply a predefined template to enable/disable tools by category",
            self.tool_apply_mcp_template,
            {
                "type": "object",
                "properties": {
                    "template": {
                        "type": "string",
                        "enum": ["minimal", "monitoring", "development", "security", "full"],
                        "description": "Template name: minimal (basic only), monitoring (system stats), development (dev tools), security (security audit), full (all tools)"
                    }
                },
                "required": ["template"]
            }
        )
        self.register_tool(
            "get_mcp_templates",
            "Get available MCP tool configuration templates and their descriptions",
            self.tool_get_mcp_templates,
            {"type": "object"}
        )
        
        # Register 100+ extended tools
        logger.info("Registering extended tools (100+ system management tools)")
        self.extended.register_all(self)

    def _setup_resources(self):
        """Build a small catalog of workspace resources for MCP consumers."""
        candidates = [
            (self.workspace_root / "README.md", "Project README", "High-level overview of systerd-lite", "text/markdown"),
            (self.workspace_root / "MCP_document.md", "MCP Specification", "Draft MCP specification provided with the project", "text/markdown"),
            (self.workspace_root / "systerd-lite.py", "Launcher Script", "Entry point that boots the systerd-lite runtime", "text/x-python"),
            (self.workspace_root / "systerd_lite" / "app.py", "Core Application", "Primary systerd-lite application module", "text/x-python"),
            (self.workspace_root / ".vscode" / "mcp.json", "Local MCP Config", "LocalProcess configuration manifest", "application/json"),
        ]

        resources: List[Dict[str, Any]] = []
        for path, title, description, mime in candidates:
            if not path.exists():
                continue
            stat = path.stat()
            resources.append({
                "uri": path.resolve().as_uri(),
                "name": path.name,
                "title": title,
                "description": description,
                "mimeType": mime,
                "size": stat.st_size,
                "annotations": {
                    "audience": ["assistant", "user"],
                    "priority": 0.7,
                    "lastModified": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
                },
            })

        self._resources = resources
        self._resource_by_uri = {res["uri"]: res for res in resources}
        workspace_uri = self.workspace_root.as_uri().rstrip("/")
        self._resource_templates = [
            {
                "uriTemplate": f"{workspace_uri}/{{path}}",
                "name": "Workspace file",
                "title": "Workspace file reference",
                "description": "Reference any file in the systerd-lite workspace",
                "mimeType": "application/octet-stream",
                "annotations": {"audience": ["assistant"], "priority": 0.4},
            }
        ]

    def register_tool(
        self,
        name: str,
        description: str,
        handler: Callable[..., Any],
        parameters: Dict[str, Any],
    ):
        self.tools[name] = MCPTool(name, description, handler, parameters)

    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Any:
        """
        Execute a tool by name with arguments.
        Simplified interface for HTTP API (non JSON-RPC).
        """
        if name not in self.tools:
            raise MCPError(
                f"Tool not found: {name}",
                code=ErrorCode.TOOL_NOT_FOUND,
                details={"tool": name, "available": list(self.tools.keys())}
            )
        
        try:
            logger.debug(f"Executing MCP tool: {name} with args: {arguments}")
            result = await self.tools[name].handler(**arguments)
            logger.debug(f"Tool {name} completed successfully")
            return result
        except SysterdError:
            raise  # Re-raise SysterdError as-is
        except Exception as e:
            logger.exception(f"Unhandled error executing tool {name}")
            raise MCPError(
                f"Tool execution failed: {str(e)}",
                code=ErrorCode.TOOL_EXECUTION_FAILED,
                details=format_exception_details(e)
            )

    def _normalize_method(self, method: str | None) -> str:
        if not method:
            return ''
        normalized = method.strip()
        if normalized.startswith('mcp.'):
            normalized = normalized[4:]
        elif normalized.startswith('mcp/'):
            normalized = normalized[4:]
        normalized = normalized.replace('.', '/')
        return normalized

    def _json_error(self, msg_id: Any, code: int, message: str, data: Any | None = None) -> Dict[str, Any]:
        error = {"code": code, "message": message}
        if data is not None:
            error["data"] = data
        return {"jsonrpc": "2.0", "id": msg_id, "error": error}

    def _resolve_file_uri(self, uri: str) -> Path | None:
        parsed = urlparse(uri)
        if parsed.scheme != "file":
            return None
        candidate = Path(unquote(parsed.path))
        try:
            candidate = candidate.resolve()
        except Exception:
            return None
        if self.workspace_root not in candidate.parents and candidate != self.workspace_root:
            return None
        if not candidate.exists():
            return None
        return candidate

    async def process_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle a JSON-RPC request from an MCP client."""
        method = request_data.get("method")
        normalized = self._normalize_method(method)
        params = request_data.get("params") or {}
        msg_id = request_data.get("id")

        if normalized == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "capabilities": {
                        "resources": {"subscribe": True, "listChanged": False}
                    }
                },
            }

        if normalized == "tools/list":
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "tools": [t.to_schema() for t in self.tools.values()]
                },
            }

        if normalized == "tools/call":
            name = params.get("name")
            args = params.get("arguments", {})
            if name not in self.tools:
                return self._json_error(msg_id, -32601, f"Tool not found: {name}")
            
            try:
                logger.debug(f"Executing MCP tool: {name} with args: {args}")
                result = await self.tools[name].handler(**args)
                logger.debug(f"Tool {name} completed successfully")
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "content": [{"type": "text", "text": json.dumps(result, default=str)}]
                    },
                }
            except SysterdError as e:
                e.log(logging.ERROR)
                error_dict = e.to_dict()
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "error": {
                        "code": e.code.value,
                        "message": e.message,
                        "data": error_dict,
                    },
                }
            except Exception as e:
                logger.exception(f"Unhandled error executing tool {name}")
                details = format_exception_details(e)
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "error": {
                        "code": ErrorCode.TOOL_EXECUTION_FAILED.value,
                        "message": str(e),
                        "data": details,
                    },
                }

        if normalized == "resources/list":
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "resources": self._resources,
                    "nextCursor": None,
                },
            }

        if normalized == "resources/templates/list":
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {"resourceTemplates": self._resource_templates},
            }

        if normalized == "resources/read":
            uri = params.get("uri")
            if not uri:
                return self._json_error(msg_id, -32602, "Missing resource URI")
            path = self._resolve_file_uri(uri)
            if not path:
                return self._json_error(msg_id, -32002, "Resource not found", {"uri": uri})
            try:
                contents = path.read_text(encoding="utf-8", errors="replace")
            except Exception as exc:
                details = format_exception_details(exc)
                return self._json_error(msg_id, -32603, "Failed to read resource", details)
            metadata = self._resource_by_uri.get(uri, {})
            content_block = {
                "uri": uri,
                "mimeType": metadata.get("mimeType", "text/plain"),
                "text": contents,
            }
            if metadata.get("annotations"):
                content_block["annotations"] = metadata["annotations"]
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {"contents": [content_block]},
            }

        if normalized == "resources/subscribe":
            uri = params.get("uri")
            if not uri:
                return self._json_error(msg_id, -32602, "Missing URI for subscription")
            if uri not in self._resource_by_uri:
                return self._json_error(msg_id, -32002, "Resource not found", {"uri": uri})
            subscription_id = str(uuid.uuid4())
            self._subscriptions.setdefault(uri, set()).add(subscription_id)
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {"subscriptionId": subscription_id, "uri": uri},
            }

        logger.warning(f"Unsupported MCP method: {method!r} (normalized: {normalized})")
        return self._json_error(msg_id, -32601, "Method not found")

    # --- Tool Implementations ---

    async def tool_list_processes(self, limit: int = 50, sort_by: str = "cpu") -> List[Dict[str, Any]]:
        try:
            import psutil
        except ImportError as e:
            raise MCPError("psutil not available", code=ErrorCode.NOT_IMPLEMENTED, cause=e)
        
        if sort_by not in ["cpu", "memory", "pid"]:
            raise MCPError(
                f"Invalid sort_by value: {sort_by}",
                code=ErrorCode.INVALID_PARAMETERS,
                details={"valid_values": ["cpu", "memory", "pid"]},
            )
        
        procs = []
        errors = 0
        for p in psutil.process_iter(['pid', 'name', 'username', 'cpu_percent', 'memory_percent']):
            try:
                procs.append(p.info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                errors += 1
        
        if errors > 0:
            logger.debug(f"Skipped {errors} processes (no access or terminated)")
        
        if sort_by == "cpu":
            procs.sort(key=lambda x: x['cpu_percent'] or 0, reverse=True)
        elif sort_by == "memory":
            procs.sort(key=lambda x: x['memory_percent'] or 0, reverse=True)
        else:  # pid
            procs.sort(key=lambda x: x['pid'])
            
        return procs[:limit]

    async def tool_manage_service(self, action: str, unit: str) -> Dict[str, Any]:
        if not self.context.systemd_bridge:
            raise ServiceError(
                "Systemd bridge not available",
                code=ErrorCode.SYSTEMD_ERROR,
                details={"hint": "Check if D-Bus is running"},
            )
        
        if action not in ["start", "stop", "restart", "status"]:
            raise MCPError(
                f"Invalid action: {action}",
                code=ErrorCode.INVALID_PARAMETERS,
                details={"valid_actions": ["start", "stop", "restart", "status"]},
            )
        
        logger.info(f"Service management: {action} {unit}")
            
        bridge = self.context.systemd_bridge
        # Assuming bridge has these methods. If not, we'll need to add them or use what's available.
        # Based on previous context, bridge wraps D-Bus calls.
        
        try:
            if action == "start":
                await bridge.start_unit(unit)
            elif action == "stop":
                await bridge.stop_unit(unit)
            elif action == "restart":
                await bridge.restart_unit(unit)
            elif action == "status":
                # This might need implementation in bridge
                pass
            return {"status": "ok", "action": action, "unit": unit}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def tool_read_neurobus(self, topic: str = None, kind: str = None, limit: int = 50) -> List[Dict[str, Any]]:
        rows = list(self.context.neurobus.query(topic=topic, kind=kind, limit=limit))
        return rows

    async def tool_set_mode(self, mode: str) -> Dict[str, Any]:
        from .modes import SysterdMode
        try:
            new_mode = SysterdMode(mode)
            self.context.mode_controller.set_mode(new_mode)
            self.context.neurobus.record_command("mode", {"value": mode, "source": "mcp"})
            return {"status": "ok", "mode": mode}
        except ValueError:
            return {"status": "error", "message": "Invalid mode"}

    async def tool_get_mode(self) -> Dict[str, Any]:
        current_mode = self.context.mode_controller.mode
        return {
            "status": "ok",
            "mode": current_mode.value,
            "description": {
                "transparent": "All operations forwarded to systemd",
                "hybrid": "Selective AI intervention",
                "dominant": "Full AI control"
            }.get(current_mode.value, "Unknown")
        }

    async def tool_get_permissions(self) -> Dict[str, Any]:
        try:
            perm_mgr = self.context.permission_manager
            if not perm_mgr:
                return {"status": "error", "message": "Permission manager not initialized"}
            
            all_perms = {}
            for tool_name in self.tools.keys():
                perm = perm_mgr.get_permission(tool_name)
                all_perms[tool_name] = perm.value
            return {
                "status": "ok",
                "permissions": all_perms,
                "summary": {
                    "disabled": sum(1 for p in all_perms.values() if p == "disabled"),
                    "read_only": sum(1 for p in all_perms.values() if p == "read_only"),
                    "ai_ask": sum(1 for p in all_perms.values() if p == "ai_ask"),
                    "ai_auto": sum(1 for p in all_perms.values() if p == "ai_auto"),
                }
            }
        except Exception as e:
            return {"status": "error", "message": f"Failed to get permissions: {str(e)}"}

    async def tool_list_devices(self) -> List[Dict[str, Any]]:
        if not self.context.device_bridge:
            return []
        return self.context.device_bridge.list_devices()

    async def tool_control_device(self, device_id: str, command: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        if not self.context.device_bridge:
            return {"error": "Device bridge not available"}
        
        success = self.context.device_bridge.queue_command(device_id, command, params or {})
        if success:
            return {"status": "queued", "device_id": device_id}
        else:
            return {"status": "error", "message": "Device not found"}

    # ===== NEW: System Observation Tool Implementations =====

    async def tool_get_system_metrics(self) -> Dict[str, Any]:
        return self.sensors.get_all()

    async def tool_get_service_health(self, unit: str) -> Dict[str, Any]:
        # Fallback to systemctl if D-Bus bridge not available
        import subprocess
        try:
            result = subprocess.run(
                ["systemctl", "show", unit, "--no-pager"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode != 0:
                return {"error": f"Unit {unit} not found or systemctl failed"}
            
            # Parse output
            props = {}
            for line in result.stdout.splitlines():
                if "=" in line:
                    k, v = line.split("=", 1)
                    props[k] = v
            
            return {
                "unit": unit,
                "active_state": props.get("ActiveState", "unknown"),
                "sub_state": props.get("SubState", "unknown"),
                "load_state": props.get("LoadState", "unknown"),
            }
        except Exception as e:
            return {"error": f"Failed to get service health: {str(e)}"}

    async def tool_read_journald(self, unit: str = None, priority: int = None, lines: int = 50) -> List[str]:
        import subprocess
        
        cmd = ["journalctl", "-n", str(lines), "--no-pager"]
        if unit:
            cmd.extend(["-u", unit])
        if priority is not None:
            cmd.extend(["-p", str(priority)])
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            return result.stdout.splitlines()
        except Exception as e:
            return [f"Error: {e}"]

    # ===== NEW: System Tuning Tool Implementations =====

    async def tool_tune_process_priority(self, pid: int, nice: int) -> Dict[str, Any]:
        return self.tuner.set_process_priority(pid, nice)

    async def tool_set_cpu_governor(self, governor: str) -> Dict[str, Any]:
        return self.tuner.set_cpu_governor(governor)

    async def tool_get_sysctl(self, key: str) -> Dict[str, Any]:
        return self.tuner.get_sysctl(key)

    async def tool_set_sysctl(self, key: str, value: str) -> Dict[str, Any]:
        return self.tuner.set_sysctl(key, value)

    async def tool_set_io_scheduler(self, device: str, scheduler: str) -> Dict[str, Any]:
        return self.tuner.set_io_scheduler(device, scheduler)

    # ===== CALCULATOR TOOL IMPLEMENTATIONS =====

    async def tool_calculate(self, expression: str) -> Dict[str, Any]:
        return self.calculator.evaluate(expression)

    async def tool_convert_units(self, value: float, from_unit: str, to_unit: str, category: str = None) -> Dict[str, Any]:
        return self.calculator.convert_units(value, from_unit, to_unit, category)

    async def tool_matrix_operation(self, operation: str, matrix_a: List[List[float]], matrix_b: List[List[float]] = None) -> Dict[str, Any]:
        return self.calculator.matrix_operation(operation, matrix_a, matrix_b)

    async def tool_statistics(self, data: List[float]) -> Dict[str, Any]:
        return self.calculator.statistics(data)

    async def tool_solve_equation(self, equation: str, variable: str = "x") -> Dict[str, Any]:
        return self.calculator.solve_equation(equation, variable)

    async def tool_convert_base(self, number: str, from_base: int, to_base: int) -> Dict[str, Any]:
        return self.calculator.base_conversion(number, from_base, to_base)

    # ===== SCHEDULER TOOL IMPLEMENTATIONS =====

    async def tool_create_task(self, name: str, description: str, command: str, scheduled_time: str,
                               repeat: str = "once", repeat_interval: int = 0, max_runs: int = None) -> Dict[str, Any]:
        return self.scheduler.create_task(name, description, command, scheduled_time, repeat, repeat_interval, max_runs)

    async def tool_list_tasks(self, status: str = None, enabled: bool = None) -> List[Dict[str, Any]]:
        return self.scheduler.list_tasks(status, enabled)

    async def tool_get_task(self, task_id: str) -> Dict[str, Any]:
        return self.scheduler.get_task(task_id)

    async def tool_update_task(self, task_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        return self.scheduler.update_task(task_id, **updates)

    async def tool_cancel_task(self, task_id: str) -> Dict[str, Any]:
        return self.scheduler.cancel_task(task_id)

    async def tool_delete_task(self, task_id: str) -> Dict[str, Any]:
        return self.scheduler.delete_task(task_id)

    async def tool_create_reminder(self, message: str, remind_at: str) -> Dict[str, Any]:
        return self.scheduler.create_reminder(message, remind_at)

    async def tool_get_upcoming_tasks(self, limit: int = 10) -> List[Dict[str, Any]]:
        return self.scheduler.get_upcoming(limit)

    # ===== CONTAINER TOOL IMPLEMENTATIONS =====

    async def tool_create_python_container(self, name: str, python_version: str = "3.11",
                                          packages: List[str] = None, persistent: bool = False) -> Dict[str, Any]:
        return self.container.create_python_container(name, python_version, packages, persistent)

    async def tool_execute_code(self, container_name: str, code: str, timeout: int = 30) -> Dict[str, Any]:
        return self.container.execute_code(container_name, code, timeout)

    async def tool_execute_script(self, container_name: str, script_path: str,
                                  args: List[str] = None, timeout: int = 30) -> Dict[str, Any]:
        return self.container.execute_script(container_name, script_path, args, timeout)

    async def tool_list_containers(self) -> List[Dict[str, Any]]:
        return self.container.list_containers()

    async def tool_stop_container(self, container_name: str) -> Dict[str, Any]:
        return self.container.stop_container(container_name)

    async def tool_remove_container(self, container_name: str) -> Dict[str, Any]:
        return self.container.remove_container(container_name)

    async def tool_install_container_packages(self, container_name: str, packages: List[str]) -> Dict[str, Any]:
        return self.container.install_packages(container_name, packages)

    async def tool_get_container_info(self, container_name: str) -> Dict[str, Any]:
        return self.container.get_container_info(container_name)

    # ===== OLLAMA AI TOOL IMPLEMENTATIONS =====

    async def tool_ai_generate(self, prompt: str, model: str = "gemma3:12b",
                              system: str = None, temperature: float = 0.7) -> Dict[str, Any]:
        client = self.ollama.get_client(model)
        return await client.generate(prompt, system, temperature)

    async def tool_ai_chat(self, messages: List[Dict[str, str]], model: str = "gemma3:12b",
                          temperature: float = 0.7) -> Dict[str, Any]:
        client = self.ollama.get_client(model)
        return await client.chat(messages, temperature)

    async def tool_ai_analyze_issue(self, issue: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        client = self.ollama.get_client()
        return await client.analyze_system_issue(issue, context or {})

    async def tool_ai_suggest_optimization(self, metrics: Dict[str, Any] = None) -> Dict[str, Any]:
        if metrics is None:
            metrics = self.sensors.get_all()
        client = self.ollama.get_client()
        return await client.suggest_optimization(metrics)

    async def tool_ai_set_model(self, model: str) -> Dict[str, Any]:
        await self.ollama.set_default_model(model)
        return {"status": "ok", "model": model}

    async def tool_ai_list_models(self) -> List[str]:
        return self.ollama.list_available_models()


    # ===== ADDITIONAL MONITORING TOOL IMPLEMENTATIONS =====
    
    async def tool_get_cpu_info(self) -> Dict[str, Any]:
        return self.sensors.get_cpu_metrics()
    
    async def tool_get_memory_info(self) -> Dict[str, Any]:
        return self.sensors.get_memory_metrics()
    
    async def tool_get_temperature(self) -> Dict[str, Any]:
        sensors = self.sensors.get_sensors()
        return {"temperature": sensors.get("temperature", {})}
    
    async def tool_get_battery_status(self) -> Dict[str, Any]:
        sensors = self.sensors.get_sensors()
        return sensors.get("battery", {})
    
    async def tool_get_top_processes(self, limit: int = 10) -> List[Dict[str, Any]]:
        import psutil
        procs = []
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
            try:
                procs.append(proc.info)
            except:
                pass
        procs.sort(key=lambda x: x.get('cpu_percent', 0), reverse=True)
        return procs[:limit]
    
    async def tool_get_zombie_processes(self) -> List[Dict[str, Any]]:
        import psutil
        zombies = []
        for proc in psutil.process_iter(['pid', 'name', 'status']):
            try:
                if proc.info['status'] == psutil.STATUS_ZOMBIE:
                    zombies.append(proc.info)
            except:
                pass
        return zombies
    
    async def tool_get_system_info(self) -> Dict[str, Any]:
        import platform
        import psutil
        import time
        return {
            "platform": platform.system(),
            "platform_release": platform.release(),
            "platform_version": platform.version(),
            "architecture": platform.machine(),
            "hostname": platform.node(),
            "processor": platform.processor(),
            "boot_time": psutil.boot_time(),
            "uptime_seconds": time.time() - psutil.boot_time()
        }
    
    # ===== ADDITIONAL SYSTEM TOOL IMPLEMENTATIONS =====
    
    async def tool_get_environment_variables(self) -> Dict[str, str]:
        import os
        return dict(os.environ)
    
    async def tool_get_kernel_modules(self) -> List[str]:
        try:
            with open('/proc/modules', 'r') as f:
                return [line.split()[0] for line in f.readlines()]
        except:
            return []
    
    async def tool_get_hardware_info(self) -> Dict[str, Any]:
        import subprocess
        try:
            result = subprocess.run(['lscpu'], capture_output=True, text=True)
            return {"lscpu_output": result.stdout}
        except:
            return {"error": "lscpu not available"}
    
    async def tool_get_pci_devices(self) -> List[str]:
        import subprocess
        try:
            result = subprocess.run(['lspci'], capture_output=True, text=True)
            return result.stdout.strip().split('\n')
        except:
            return []
    
    async def tool_get_usb_devices(self) -> List[str]:
        import subprocess
        try:
            result = subprocess.run(['lsusb'], capture_output=True, text=True)
            return result.stdout.strip().split('\n')
        except:
            return []
    
    async def tool_get_cron_jobs(self) -> Dict[str, Any]:
        import subprocess
        try:
            result = subprocess.run(['crontab', '-l'], capture_output=True, text=True)
            return {"user_crontab": result.stdout.strip().split('\n')}
        except:
            return {"error": "No crontab or permission denied"}

    # ===== MISSING TOOLS STUB IMPLEMENTATIONS (17 tools) =====
    
    # Security Tools (7)
    async def tool_get_selinux_status(self) -> Dict[str, Any]:
        try:
            result = subprocess.run(['getenforce'], capture_output=True, text=True, timeout=5)
            return {"status": result.stdout.strip(), "enabled": result.returncode == 0}
        except:
            return {"status": "not available", "enabled": False}
    
    async def tool_get_apparmor_status(self) -> Dict[str, Any]:
        try:
            result = subprocess.run(['aa-status'], capture_output=True, text=True, timeout=5)
            return {"status": "loaded" if result.returncode == 0 else "not loaded", "profiles": []}
        except:
            return {"status": "not available", "profiles": []}
    
    async def tool_list_sudo_rules(self) -> List[Dict[str, Any]]:
        try:
            result = subprocess.run(['sudo', '-l'], capture_output=True, text=True, timeout=5)
            return {"rules": result.stdout.strip().split('\n') if result.returncode == 0 else []}
        except:
            return {"rules": []}
    
    async def tool_audit_permissions(self, path: str) -> Dict[str, Any]:
        try:
            import stat
            st = os.stat(path)
            return {
                "path": path,
                "mode": oct(st.st_mode),
                "uid": st.st_uid,
                "gid": st.st_gid,
                "owner": pwd.getpwuid(st.st_uid).pw_name,
                "group": grp.getgrgid(st.st_gid).gr_name
            }
        except Exception as e:
            return {"error": str(e)}
    
    async def tool_scan_suid_files(self) -> List[Dict[str, Any]]:
        try:
            result = subprocess.run(['find', '/', '-perm', '-4000', '-type', 'f', '2>/dev/null'], 
                                  capture_output=True, text=True, timeout=30)
            files = [{"path": f} for f in result.stdout.strip().split('\n') if f]
            return {"suid_files": files[:100]}  # Limit to 100
        except:
            return {"suid_files": []}
    
    async def tool_get_failed_logins(self, limit: int = 10) -> List[Dict[str, Any]]:
        try:
            result = subprocess.run(['lastb', '-n', str(limit)], capture_output=True, text=True, timeout=5)
            return {"failed_logins": result.stdout.strip().split('\n')}
        except:
            return {"failed_logins": []}
    
    async def tool_get_security_updates(self) -> Dict[str, Any]:
        try:
            # Debian/Ubuntu style
            result = subprocess.run(['apt', 'list', '--upgradable'], capture_output=True, text=True, timeout=10)
            updates = [line for line in result.stdout.split('\n') if 'security' in line.lower()]
            return {"security_updates": len(updates), "packages": updates[:20]}
        except:
            return {"security_updates": 0, "packages": []}
    
    # System Info Tools (3)
    async def tool_list_sessions(self) -> List[Dict[str, Any]]:
        try:
            result = subprocess.run(['who'], capture_output=True, text=True, timeout=5)
            sessions = []
            for line in result.stdout.strip().split('\n'):
                if line:
                    parts = line.split()
                    if len(parts) >= 5:
                        sessions.append({"user": parts[0], "tty": parts[1], "time": " ".join(parts[2:5])})
            return {"sessions": sessions}
        except:
            return {"sessions": []}
    
    async def tool_get_boot_time(self) -> Dict[str, Any]:
        return {"boot_time": datetime.fromtimestamp(psutil.boot_time()).isoformat()}
    
    async def tool_get_system_state(self) -> Dict[str, Any]:
        try:
            result = subprocess.run(['systemctl', 'is-system-running'], capture_output=True, text=True, timeout=5)
            return {"state": result.stdout.strip(), "degraded": "degraded" in result.stdout}
        except:
            return {"state": "unknown", "degraded": False}
    
    # Logging Tools (3)
    async def tool_get_log_size(self, log_path: str = "/var/log") -> Dict[str, Any]:
        try:
            total = 0
            for root, dirs, files in os.walk(log_path):
                for f in files:
                    fp = os.path.join(root, f)
                    if os.path.isfile(fp):
                        total += os.path.getsize(fp)
            return {"path": log_path, "size_bytes": total, "size_mb": total / (1024*1024)}
        except Exception as e:
            return {"error": str(e)}
    
    async def tool_get_kernel_logs(self, lines: int = 100) -> List[str]:
        try:
            result = subprocess.run(['dmesg', '-T', '--level=err,warn', '-n', str(lines)], 
                                  capture_output=True, text=True, timeout=5)
            return {"logs": result.stdout.strip().split('\n')[-lines:]}
        except:
            return {"logs": []}
    
    async def tool_search_logs(self, pattern: str, log_file: str = "/var/log/syslog", limit: int = 100) -> List[str]:
        try:
            result = subprocess.run(['grep', '-i', pattern, log_file], capture_output=True, text=True, timeout=10)
            lines = result.stdout.strip().split('\n')
            return {"matches": len(lines), "lines": lines[:limit]}
        except:
            return {"matches": 0, "lines": []}
    
    # User Management Tools (3)
    async def tool_get_group_info(self, groupname: str) -> Dict[str, Any]:
        try:
            import grp
            g = grp.getgrnam(groupname)
            return {"name": g.gr_name, "gid": g.gr_gid, "members": g.gr_mem}
        except KeyError:
            return {"error": f"Group {groupname} not found"}
    
    async def tool_list_logged_users(self) -> List[Dict[str, Any]]:
        try:
            users = psutil.users()
            return {"users": [{"name": u.name, "terminal": u.terminal, "host": u.host, "started": u.started} for u in users]}
        except:
            return {"users": []}
    
    async def tool_get_user_processes(self, username: str) -> List[Dict[str, Any]]:
        try:
            import pwd
            uid = pwd.getpwnam(username).pw_uid
            procs = []
            for proc in psutil.process_iter(['pid', 'name', 'username', 'uids']):
                try:
                    if proc.info['uids'].real == uid:
                        procs.append({"pid": proc.info['pid'], "name": proc.info['name']})
                except:
                    pass
            return {"username": username, "processes": procs}
        except Exception as e:
            return {"error": str(e)}
    
    # Storage Tool (1)
    async def tool_get_smart_status(self, device: str = "/dev/sda") -> Dict[str, Any]:
        try:
            result = subprocess.run(['smartctl', '-H', device], capture_output=True, text=True, timeout=10)
            health = "PASSED" if "PASSED" in result.stdout else "UNKNOWN"
            return {"device": device, "health": health, "available": result.returncode != 127}
        except:
            return {"device": device, "health": "UNKNOWN", "available": False}

    # ===== MCP Configuration Tools =====
    
    # Tool category mapping
    MCP_TOOL_CATEGORIES = {
        "monitoring": [
            "get_uptime", "get_load_average", "get_disk_usage", "get_cpu_info", "get_memory_info",
            "get_temperature", "get_battery_status", "get_top_processes", "get_zombie_processes",
            "get_system_info", "list_processes", "monitor_realtime", "get_network_stats"
        ],
        "security": [
            "get_selinux_status", "get_apparmor_status", "list_sudo_rules", "audit_permissions",
            "scan_suid_files", "get_failed_logins", "get_security_updates", "add_firewall_rule",
            "list_firewall_rules", "set_apparmor_mode", "check_system_integrity",
            "analyze_security_exposure", "check_open_ports"
        ],
        "system": [
            "manage_service", "list_units", "get_system_state", "get_kernel_logs",
            "get_environment_variables", "get_kernel_modules", "get_hardware_info",
            "get_pci_devices", "get_usb_devices", "get_cron_jobs", "list_sessions",
            "get_boot_time", "show_unit_dependencies", "isolate_target"
        ],
        "network": [
            "list_interfaces", "ping_host", "list_routes", "add_route", "delete_route",
            "list_dns", "set_dns", "trace_route", "get_listening_sockets"
        ],
        "container": [
            "list_containers", "start_container", "stop_container", "restart_container",
            "remove_container", "run_container", "inspect_container", "get_container_logs",
            "list_images", "pull_image", "remove_image", "inspect_image", "tag_image", "list_volumes"
        ],
        "user": [
            "create_user", "list_logged_users", "get_user_processes", "get_group_info"
        ],
        "storage": [
            "list_lvm_volumes", "create_lvm_volume", "extend_lvm_volume",
            "list_mounts", "mount_filesystem", "get_smart_status"
        ],
        "scheduler": [
            "create_scheduled_task", "get_upcoming_tasks", "create_reminder", "delete_task"
        ],
        "tuning": [
            "set_cpu_governor", "tune_process_priority", "set_io_scheduler",
            "tune_filesystem", "set_nice_level", "interface_up", "interface_down"
        ],
        "ai": [
            "ai_chat", "ai_analyze_issue", "ai_suggest_optimization",
            "ai_generate_text", "ai_list_models", "set_ai_model"
        ],
        "calculator": [
            "calc_evaluate", "calc_solve", "calc_convert_base", "calc_convert_units", "calc_matrix"
        ],
        "mcp": [
            "get_mcp_config", "list_mcp_tools", "set_mcp_tool_permission",
            "apply_mcp_template", "get_mcp_templates"
        ]
    }
    
    MCP_TEMPLATES = {
        "minimal": {
            "name": "Minimal",
            "description": "Basic system information only - safe for any environment",
            "categories": ["monitoring"],
            "tool_count": 13
        },
        "monitoring": {
            "name": "Monitoring",
            "description": "System monitoring and diagnostics - read-only operations",
            "categories": ["monitoring", "mcp"],
            "tool_count": 18
        },
        "development": {
            "name": "Development",
            "description": "Development focused - monitoring, containers, and basic system tools",
            "categories": ["monitoring", "container", "calculator", "mcp"],
            "tool_count": 35
        },
        "security": {
            "name": "Security Audit",
            "description": "Security auditing and compliance checking",
            "categories": ["monitoring", "security", "mcp"],
            "tool_count": 31
        },
        "full": {
            "name": "Full Access",
            "description": "All tools enabled - requires appropriate permissions",
            "categories": list(MCP_TOOL_CATEGORIES.keys()),
            "tool_count": 182
        }
    }
    
    async def tool_get_mcp_config(self) -> Dict[str, Any]:
        """Get current MCP server configuration."""
        perm_mgr = self.context.permission_manager
        
        # Count tools by permission level
        permission_counts = {"DISABLED": 0, "READ_ONLY": 0, "AI_ASK": 0, "AI_AUTO": 0}
        for tool_name in self.tools:
            perm = perm_mgr.check(tool_name)
            permission_counts[perm.name] += 1
        
        return {
            "server_version": "3.0-complete",
            "total_tools": len(self.tools),
            "enabled_tools": len(self.tools) - permission_counts["DISABLED"],
            "permission_counts": permission_counts,
            "mode": self.context.mode_controller.mode.value,
            "state_dir": str(self.context.state_dir),
            "categories": list(self.MCP_TOOL_CATEGORIES.keys()),
            "available_templates": list(self.MCP_TEMPLATES.keys())
        }
    
    async def tool_list_mcp_tools(self, category: str = None, status: str = "all") -> Dict[str, Any]:
        """List MCP tools with their status."""
        perm_mgr = self.context.permission_manager
        
        # Build tool list
        tools_list = []
        for tool_name, tool in self.tools.items():
            perm = perm_mgr.check(tool_name)
            is_enabled = perm.name != "DISABLED"
            
            # Apply category filter
            if category:
                category_tools = self.MCP_TOOL_CATEGORIES.get(category, [])
                if tool_name not in category_tools:
                    continue
            
            # Apply status filter
            if status == "enabled" and not is_enabled:
                continue
            if status == "disabled" and is_enabled:
                continue
            
            # Find tool category
            tool_category = "other"
            for cat, cat_tools in self.MCP_TOOL_CATEGORIES.items():
                if tool_name in cat_tools:
                    tool_category = cat
                    break
            
            tools_list.append({
                "name": tool_name,
                "description": tool.description,
                "category": tool_category,
                "permission": perm.name,
                "enabled": is_enabled
            })
        
        # Sort by category, then name
        tools_list.sort(key=lambda x: (x["category"], x["name"]))
        
        return {
            "total": len(tools_list),
            "filter": {"category": category, "status": status},
            "tools": tools_list
        }
    
    async def tool_set_mcp_tool_permission(self, tool_name: str, permission: str) -> Dict[str, Any]:
        """Set permission level for a specific tool."""
        from .permissions import Permission
        
        if tool_name not in self.tools:
            return {"error": f"Tool '{tool_name}' not found", "available_tools": len(self.tools)}
        
        try:
            perm_level = Permission[permission]
        except KeyError:
            return {"error": f"Invalid permission '{permission}'", "valid_permissions": ["DISABLED", "READ_ONLY", "AI_ASK", "AI_AUTO"]}
        
        perm_mgr = self.context.permission_manager
        old_perm = perm_mgr.check(tool_name)
        perm_mgr.set_permission(tool_name, perm_level)
        
        return {
            "tool": tool_name,
            "old_permission": old_perm.name,
            "new_permission": perm_level.name,
            "success": True
        }
    
    async def tool_apply_mcp_template(self, template: str) -> Dict[str, Any]:
        """Apply a predefined template to configure tool permissions."""
        from .permissions import Permission
        
        if template not in self.MCP_TEMPLATES:
            return {"error": f"Template '{template}' not found", "available": list(self.MCP_TEMPLATES.keys())}
        
        template_info = self.MCP_TEMPLATES[template]
        enabled_categories = template_info["categories"]
        perm_mgr = self.context.permission_manager
        
        enabled_count = 0
        disabled_count = 0
        
        for tool_name in self.tools:
            # Find tool's category
            tool_category = None
            for cat, cat_tools in self.MCP_TOOL_CATEGORIES.items():
                if tool_name in cat_tools:
                    tool_category = cat
                    break
            
            # Enable if category is in template, disable otherwise
            if tool_category in enabled_categories:
                perm_mgr.set_permission(tool_name, Permission.AI_AUTO)
                enabled_count += 1
            else:
                perm_mgr.set_permission(tool_name, Permission.DISABLED)
                disabled_count += 1
        
        return {
            "template": template,
            "name": template_info["name"],
            "description": template_info["description"],
            "enabled_categories": enabled_categories,
            "enabled_tools": enabled_count,
            "disabled_tools": disabled_count,
            "success": True
        }
    
    async def tool_get_mcp_templates(self) -> Dict[str, Any]:
        """Get available MCP templates and their descriptions."""
        templates = []
        for key, info in self.MCP_TEMPLATES.items():
            templates.append({
                "id": key,
                "name": info["name"],
                "description": info["description"],
                "categories": info["categories"],
                "estimated_tool_count": info["tool_count"]
            })
        return {"templates": templates}
