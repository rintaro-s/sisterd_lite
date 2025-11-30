"""
Permission Manager for MCP tools.
Controls which tools AI can use autonomously.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Any, Set
from enum import Enum


class Permission(str, Enum):
    DISABLED = "disabled"  # Tool cannot be used
    READ_ONLY = "read_only"  # Can observe but not modify
    AI_ASK = "ai_ask"  # AI must ask human via Gradio
    AI_AUTO = "ai_auto"  # AI can execute autonomously


class PermissionManager:
    def __init__(self, config_file: Path):
        self.config_file = config_file
        self.permissions: Dict[str, Permission] = {}
        self.load()

    def load(self):
        if self.config_file.exists():
            data = json.loads(self.config_file.read_text())
            self.permissions = {
                k: Permission(v) for k, v in data.items()
            }
        else:
            # Default permissions
            self.permissions = self.get_defaults()
            self.save()

    def save(self):
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        self.config_file.write_text(
            json.dumps({k: v.value for k, v in self.permissions.items()}, indent=2)
        )

    def get_defaults(self) -> Dict[str, Permission]:
        """Default permission policy: permissive for development/testing."""
        # Default to AI_AUTO for all observation/query tools
        # Default to AI_ASK for modification tools
        # Default to DISABLED for dangerous system-level operations
        return {
            # === OBSERVATION TOOLS (AI_AUTO) ===
            # Process & System
            "tool_list_processes": Permission.AI_AUTO,
            "tool_get_system_metrics": Permission.AI_AUTO,
            "tool_get_service_health": Permission.AI_AUTO,
            "tool_read_journald": Permission.AI_AUTO,
            
            # Systemd Units
            "tool_list_units": Permission.AI_AUTO,
            "tool_list_enabled_units": Permission.AI_AUTO,
            "tool_list_failed_units": Permission.AI_AUTO,
            
            # Network
            "tool_list_interfaces": Permission.AI_AUTO,
            "tool_get_interface_details": Permission.AI_AUTO,
            "tool_ping_host": Permission.AI_AUTO,
            
            # Storage
            "tool_get_disk_usage": Permission.AI_AUTO,
            "tool_list_block_devices": Permission.AI_AUTO,
            "tool_list_mounts": Permission.AI_AUTO,
            
            # Packages
            "tool_list_installed_packages": Permission.AI_AUTO,
            "tool_search_package": Permission.AI_AUTO,
            
            # Users
            "tool_list_users": Permission.AI_AUTO,
            "tool_list_groups": Permission.AI_AUTO,
            
            # Security
            "tool_list_open_ports": Permission.AI_AUTO,
            "tool_list_firewall_rules": Permission.AI_AUTO,
            
            # Kernel
            "tool_get_kernel_info": Permission.AI_AUTO,
            "tool_list_loaded_modules": Permission.AI_AUTO,
            
            # NeuroBus & Devices
            "tool_read_neurobus": Permission.AI_AUTO,
            "tool_list_devices": Permission.AI_AUTO,
            
            # Sysctl read
            "tool_get_sysctl": Permission.AI_AUTO,
            
            # === MODIFICATION TOOLS (AI_ASK) ===
            # Service control
            "tool_manage_service": Permission.AI_ASK,
            "tool_enable_unit": Permission.AI_ASK,
            "tool_disable_unit": Permission.AI_ASK,
            "tool_mask_unit": Permission.AI_ASK,
            "tool_unmask_unit": Permission.AI_ASK,
            
            # Device control
            "tool_control_device": Permission.AI_ASK,
            
            # Package management
            "tool_install_package": Permission.AI_ASK,
            "tool_remove_package": Permission.AI_ASK,
            "tool_update_package": Permission.AI_ASK,
            
            # Network control
            "tool_set_interface_state": Permission.AI_ASK,
            
            # Mode control
            "tool_set_mode": Permission.AI_ASK,
            
            # === SYSTEM TUNING (AI_ASK for testing) ===
            "tool_tune_process_priority": Permission.AI_ASK,
            "tool_set_cpu_governor": Permission.AI_ASK,
            "tool_set_sysctl": Permission.AI_ASK,
            "tool_set_io_scheduler": Permission.AI_ASK,
            "tool_load_kernel_module": Permission.DISABLED,
            "tool_unload_kernel_module": Permission.DISABLED,
            
            # === DANGEROUS OPERATIONS (DISABLED) ===
            "tool_reboot": Permission.DISABLED,
            "tool_reboot_system": Permission.AI_ASK,  # For testing
            "tool_shutdown": Permission.DISABLED,
            "tool_kill_process": Permission.DISABLED,
            "tool_delete_user": Permission.AI_ASK,  # For testing
        }

    def check(self, tool_name: str) -> Permission:
        """
        Check permission for a tool.
        If tool not in config, default to AI_AUTO for observation tools,
        AI_ASK for modification tools, DISABLED for dangerous operations.
        """
        if tool_name in self.permissions:
            return self.permissions[tool_name]
        
        # Smart defaults based on tool name patterns
        lower_name = tool_name.lower()
        
        # Observation verbs: auto-allow
        if any(verb in lower_name for verb in ['list', 'get', 'read', 'query', 'show', 'check', 'ping']):
            return Permission.AI_AUTO
        
        # Modification verbs: ask human
        if any(verb in lower_name for verb in ['set', 'enable', 'disable', 'start', 'stop', 'restart', 'install', 'remove', 'update']):
            return Permission.AI_ASK
        
        # Dangerous verbs: disabled
        if any(verb in lower_name for verb in ['reboot', 'shutdown', 'kill', 'delete', 'destroy', 'format']):
            return Permission.DISABLED
        
        # Unknown: conservative default
        return Permission.AI_ASK

    def set_permission(self, tool_name: str, permission: Permission, auto_save: bool = True):
        """Set permission for a single tool."""
        self.permissions[tool_name] = permission
        if auto_save:
            self.save()

    def set_permissions_batch(self, permissions_dict: Dict[str, Permission], replace: bool = True):
        """Set multiple permissions at once and save only once.
        
        Args:
            permissions_dict: Dictionary of tool names to permissions
            replace: If True, replace all permissions. If False, merge with existing.
        """
        if replace:
            self.permissions = permissions_dict.copy()
        else:
            self.permissions.update(permissions_dict)
        self.save()

    def get_all(self) -> Dict[str, str]:
        return {k: v.value for k, v in self.permissions.items()}

    def get_enabled_tools(self) -> list:
        """Get list of tools that are NOT disabled."""
        return [name for name, perm in self.permissions.items() if perm != Permission.DISABLED]

    def get_disabled_tools(self) -> list:
        """Get list of disabled tools."""
        return [name for name, perm in self.permissions.items() if perm == Permission.DISABLED]

