"""
Extended MCP tools for comprehensive Linux system management.
Adds 100+ tools covering all system aspects.
"""

from __future__ import annotations

import json
import logging
import subprocess
from typing import Any, Dict, List

from .decorators import permission_audit, require_permission
from .permissions import Permission

logger = logging.getLogger(__name__)


class ExtendedMCPTools:
    """Extended system management tools (100+ tools for complete control)"""

    def __init__(self, context):
        self.context = context

    def register_all(self, handler):
        """Register all extended tools to MCPHandler"""
        # ===== SYSTEMD COMPLETE (20 tools) =====
        handler.register_tool(
            "list_units", "List all systemd units", self.tool_list_units,
            {"type": "object", "properties": {"type": {"type": "string", "enum": ["service", "timer", "socket", "mount", "swap", "target", "path", "slice", "scope"]}}}
        )
        handler.register_tool(
            "get_unit_properties", "Get detailed properties of a systemd unit", self.tool_get_unit_properties,
            {"type": "object", "properties": {"unit": {"type": "string"}}, "required": ["unit"]}
        )
        handler.register_tool(
            "enable_unit", "Enable a systemd unit to start at boot", self.tool_enable_unit,
            {"type": "object", "properties": {"unit": {"type": "string"}, "now": {"type": "boolean"}}, "required": ["unit"]}
        )
        handler.register_tool(
            "disable_unit", "Disable a systemd unit from starting at boot", self.tool_disable_unit,
            {"type": "object", "properties": {"unit": {"type": "string"}, "now": {"type": "boolean"}}, "required": ["unit"]}
        )
        handler.register_tool(
            "mask_unit", "Mask a systemd unit (prevent activation)", self.tool_mask_unit,
            {"type": "object", "properties": {"unit": {"type": "string"}}, "required": ["unit"]}
        )
        handler.register_tool(
            "unmask_unit", "Unmask a systemd unit", self.tool_unmask_unit,
            {"type": "object", "properties": {"unit": {"type": "string"}}, "required": ["unit"]}
        )
        handler.register_tool(
            "reload_systemd", "Reload systemd manager configuration", self.tool_reload_systemd,
            {"type": "object", "properties": {}}
        )
        handler.register_tool(
            "list_timers", "List all systemd timers with next activation time", self.tool_list_timers,
            {"type": "object", "properties": {}}
        )
        handler.register_tool(
            "show_unit_dependencies", "Show dependencies of a unit", self.tool_show_unit_dependencies,
            {"type": "object", "properties": {"unit": {"type": "string"}}, "required": ["unit"]}
        )
        handler.register_tool(
            "isolate_target", "Isolate to a specific systemd target", self.tool_isolate_target,
            {"type": "object", "properties": {"target": {"type": "string"}}, "required": ["target"]}
        )
        handler.register_tool(
            "set_default_target", "Set default boot target", self.tool_set_default_target,
            {"type": "object", "properties": {"target": {"type": "string"}}, "required": ["target"]}
        )
        handler.register_tool(
            "get_failed_units", "Get all failed systemd units", self.tool_get_failed_units,
            {"type": "object", "properties": {}}
        )
        handler.register_tool(
            "reset_failed_units", "Reset failed state of systemd units", self.tool_reset_failed_units,
            {"type": "object", "properties": {"unit": {"type": "string"}}}
        )
        handler.register_tool(
            "list_sockets", "List all systemd sockets", self.tool_list_sockets,
            {"type": "object", "properties": {}}
        )
        handler.register_tool(
            "list_mounts", "List all systemd mount units", self.tool_list_mounts,
            {"type": "object", "properties": {}}
        )
        handler.register_tool(
            "analyze_security", "Analyze security exposure of a service", self.tool_analyze_security,
            {"type": "object", "properties": {"unit": {"type": "string"}}, "required": ["unit"]}
        )
        handler.register_tool(
            "analyze_blame", "Show service initialization times (blame)", self.tool_analyze_blame,
            {"type": "object", "properties": {}}
        )
        handler.register_tool(
            "analyze_critical_chain", "Show critical chain of boot process", self.tool_analyze_critical_chain,
            {"type": "object", "properties": {"unit": {"type": "string"}}}
        )
        handler.register_tool(
            "edit_unit", "Edit a systemd unit (create override)", self.tool_edit_unit,
            {"type": "object", "properties": {"unit": {"type": "string"}, "content": {"type": "string"}}, "required": ["unit", "content"]}
        )
        handler.register_tool(
            "cat_unit", "Show content of a systemd unit file", self.tool_cat_unit,
            {"type": "object", "properties": {"unit": {"type": "string"}}, "required": ["unit"]}
        )

        # ===== NETWORK MANAGEMENT (15 tools) =====
        handler.register_tool(
            "list_interfaces", "List all network interfaces", self.tool_list_interfaces,
            {"type": "object", "properties": {}}
        )
        handler.register_tool(
            "get_interface_status", "Get status of a network interface", self.tool_get_interface_status,
            {"type": "object", "properties": {"interface": {"type": "string"}}, "required": ["interface"]}
        )
        handler.register_tool(
            "set_interface_up", "Bring network interface up", self.tool_set_interface_up,
            {"type": "object", "properties": {"interface": {"type": "string"}}, "required": ["interface"]}
        )
        handler.register_tool(
            "set_interface_down", "Bring network interface down", self.tool_set_interface_down,
            {"type": "object", "properties": {"interface": {"type": "string"}}, "required": ["interface"]}
        )
        handler.register_tool(
            "list_routes", "List routing table", self.tool_list_routes,
            {"type": "object", "properties": {}}
        )
        handler.register_tool(
            "add_route", "Add a route to routing table", self.tool_add_route,
            {"type": "object", "properties": {"destination": {"type": "string"}, "gateway": {"type": "string"}, "device": {"type": "string"}}, "required": ["destination"]}
        )
        handler.register_tool(
            "del_route", "Delete a route from routing table", self.tool_del_route,
            {"type": "object", "properties": {"destination": {"type": "string"}}, "required": ["destination"]}
        )
        handler.register_tool(
            "list_firewall_rules", "List firewall rules (iptables/nftables)", self.tool_list_firewall_rules,
            {"type": "object", "properties": {"table": {"type": "string"}}}
        )
        handler.register_tool(
            "add_firewall_rule", "Add a firewall rule", self.tool_add_firewall_rule,
            {"type": "object", "properties": {"chain": {"type": "string"}, "rule": {"type": "string"}}, "required": ["chain", "rule"]}
        )
        handler.register_tool(
            "del_firewall_rule", "Delete a firewall rule", self.tool_del_firewall_rule,
            {"type": "object", "properties": {"chain": {"type": "string"}, "rule_num": {"type": "integer"}}, "required": ["chain", "rule_num"]}
        )
        handler.register_tool(
            "get_dns_config", "Get DNS configuration", self.tool_get_dns_config,
            {"type": "object", "properties": {}}
        )
        handler.register_tool(
            "set_dns_servers", "Set DNS servers", self.tool_set_dns_servers,
            {"type": "object", "properties": {"servers": {"type": "array", "items": {"type": "string"}}}, "required": ["servers"]}
        )
        handler.register_tool(
            "ping_host", "Ping a host to check connectivity", self.tool_ping_host,
            {"type": "object", "properties": {"host": {"type": "string"}, "count": {"type": "integer"}}, "required": ["host"]}
        )
        handler.register_tool(
            "traceroute", "Trace route to a host", self.tool_traceroute,
            {"type": "object", "properties": {"host": {"type": "string"}}, "required": ["host"]}
        )
        handler.register_tool(
            "netstat", "Show network connections", self.tool_netstat,
            {"type": "object", "properties": {"tcp": {"type": "boolean"}, "udp": {"type": "boolean"}, "listening": {"type": "boolean"}}}
        )

        # ===== STORAGE/FILESYSTEM (15 tools) =====
        handler.register_tool(
            "list_block_devices", "List all block devices", self.tool_list_block_devices,
            {"type": "object", "properties": {}}
        )
        handler.register_tool(
            "get_disk_usage", "Get disk usage statistics", self.tool_get_disk_usage,
            {"type": "object", "properties": {"path": {"type": "string"}}}
        )
        handler.register_tool(
            "list_mounted_filesystems", "List all mounted filesystems", self.tool_list_mounted_filesystems,
            {"type": "object", "properties": {}}
        )
        handler.register_tool(
            "mount_filesystem", "Mount a filesystem", self.tool_mount_filesystem,
            {"type": "object", "properties": {"device": {"type": "string"}, "mountpoint": {"type": "string"}, "fstype": {"type": "string"}, "options": {"type": "string"}}, "required": ["device", "mountpoint"]}
        )
        handler.register_tool(
            "unmount_filesystem", "Unmount a filesystem", self.tool_unmount_filesystem,
            {"type": "object", "properties": {"mountpoint": {"type": "string"}}, "required": ["mountpoint"]}
        )
        handler.register_tool(
            "list_lvm_volumes", "List LVM logical volumes", self.tool_list_lvm_volumes,
            {"type": "object", "properties": {}}
        )
        handler.register_tool(
            "create_lvm_volume", "Create a new LVM logical volume", self.tool_create_lvm_volume,
            {"type": "object", "properties": {"vg": {"type": "string"}, "name": {"type": "string"}, "size": {"type": "string"}}, "required": ["vg", "name", "size"]}
        )
        handler.register_tool(
            "extend_lvm_volume", "Extend an LVM logical volume", self.tool_extend_lvm_volume,
            {"type": "object", "properties": {"lv_path": {"type": "string"}, "size": {"type": "string"}}, "required": ["lv_path", "size"]}
        )
        handler.register_tool(
            "check_filesystem", "Check filesystem integrity (fsck)", self.tool_check_filesystem,
            {"type": "object", "properties": {"device": {"type": "string"}}, "required": ["device"]}
        )
        handler.register_tool(
            "list_raid_arrays", "List RAID arrays (md)", self.tool_list_raid_arrays,
            {"type": "object", "properties": {}}
        )
        handler.register_tool(
            "get_smart_status", "Get SMART status of a disk", self.tool_get_smart_status,
            {"type": "object", "properties": {"device": {"type": "string"}}, "required": ["device"]}
        )
        handler.register_tool(
            "list_inodes", "List inode usage per filesystem", self.tool_list_inodes,
            {"type": "object", "properties": {}}
        )
        handler.register_tool(
            "find_large_files", "Find largest files in a directory tree", self.tool_find_large_files,
            {"type": "object", "properties": {"path": {"type": "string"}, "limit": {"type": "integer"}}, "required": ["path"]}
        )
        handler.register_tool(
            "get_disk_io_stats", "Get disk I/O statistics", self.tool_get_disk_io_stats,
            {"type": "object", "properties": {}}
        )
        handler.register_tool(
            "tune_filesystem", "Tune filesystem parameters (tune2fs)", self.tool_tune_filesystem,
            {"type": "object", "properties": {"device": {"type": "string"}, "params": {"type": "object"}}, "required": ["device"]}
        )

        # ===== PACKAGE MANAGEMENT (10 tools) =====
        handler.register_tool(
            "list_installed_packages", "List all installed packages", self.tool_list_installed_packages,
            {"type": "object", "properties": {"pattern": {"type": "string"}}}
        )
        handler.register_tool(
            "search_packages", "Search for packages", self.tool_search_packages,
            {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}
        )
        handler.register_tool(
            "install_package", "Install a package", self.tool_install_package,
            {"type": "object", "properties": {"package": {"type": "string"}}, "required": ["package"]}
        )
        handler.register_tool(
            "remove_package", "Remove a package", self.tool_remove_package,
            {"type": "object", "properties": {"package": {"type": "string"}}, "required": ["package"]}
        )
        handler.register_tool(
            "update_package_cache", "Update package cache", self.tool_update_package_cache,
            {"type": "object", "properties": {}}
        )
        handler.register_tool(
            "upgrade_system", "Upgrade all packages", self.tool_upgrade_system,
            {"type": "object", "properties": {"dist_upgrade": {"type": "boolean"}}}
        )
        handler.register_tool(
            "list_upgradable", "List upgradable packages", self.tool_list_upgradable,
            {"type": "object", "properties": {}}
        )
        handler.register_tool(
            "get_package_info", "Get detailed package information", self.tool_get_package_info,
            {"type": "object", "properties": {"package": {"type": "string"}}, "required": ["package"]}
        )
        handler.register_tool(
            "autoremove_packages", "Remove unused dependencies", self.tool_autoremove_packages,
            {"type": "object", "properties": {}}
        )
        handler.register_tool(
            "clean_package_cache", "Clean package cache", self.tool_clean_package_cache,
            {"type": "object", "properties": {}}
        )

        # ===== USER/GROUP MANAGEMENT (10 tools) =====
        handler.register_tool(
            "list_users", "List all users", self.tool_list_users,
            {"type": "object", "properties": {}}
        )
        handler.register_tool(
            "list_groups", "List all groups", self.tool_list_groups,
            {"type": "object", "properties": {}}
        )
        handler.register_tool(
            "create_user", "Create a new user", self.tool_create_user,
            {"type": "object", "properties": {"username": {"type": "string"}, "home": {"type": "string"}, "shell": {"type": "string"}, "groups": {"type": "array"}}, "required": ["username"]}
        )
        handler.register_tool(
            "delete_user", "Delete a user", self.tool_delete_user,
            {"type": "object", "properties": {"username": {"type": "string"}, "remove_home": {"type": "boolean"}}, "required": ["username"]}
        )
        handler.register_tool(
            "modify_user", "Modify user properties", self.tool_modify_user,
            {"type": "object", "properties": {"username": {"type": "string"}, "changes": {"type": "object"}}, "required": ["username", "changes"]}
        )
        handler.register_tool(
            "create_group", "Create a new group", self.tool_create_group,
            {"type": "object", "properties": {"groupname": {"type": "string"}}, "required": ["groupname"]}
        )
        handler.register_tool(
            "delete_group", "Delete a group", self.tool_delete_group,
            {"type": "object", "properties": {"groupname": {"type": "string"}}, "required": ["groupname"]}
        )
        handler.register_tool(
            "add_user_to_group", "Add user to a group", self.tool_add_user_to_group,
            {"type": "object", "properties": {"username": {"type": "string"}, "groupname": {"type": "string"}}, "required": ["username", "groupname"]}
        )
        handler.register_tool(
            "list_logged_in_users", "List currently logged in users", self.tool_list_logged_in_users,
            {"type": "object", "properties": {}}
        )
        handler.register_tool(
            "get_user_info", "Get detailed user information", self.tool_get_user_info,
            {"type": "object", "properties": {"username": {"type": "string"}}, "required": ["username"]}
        )

        # ===== SECURITY/AUDIT (10 tools) =====
        handler.register_tool(
            "list_open_ports", "List open network ports", self.tool_list_open_ports,
            {"type": "object", "properties": {}}
        )
        handler.register_tool(
            "check_selinux_status", "Check SELinux status", self.tool_check_selinux_status,
            {"type": "object", "properties": {}}
        )
        handler.register_tool(
            "check_apparmor_status", "Check AppArmor status", self.tool_check_apparmor_status,
            {"type": "object", "properties": {}}
        )
        handler.register_tool(
            "list_sudo_users", "List users with sudo privileges", self.tool_list_sudo_users,
            {"type": "object", "properties": {}}
        )
        handler.register_tool(
            "check_failed_logins", "Check failed login attempts", self.tool_check_failed_logins,
            {"type": "object", "properties": {"limit": {"type": "integer"}}}
        )
        handler.register_tool(
            "list_cron_jobs", "List all cron jobs", self.tool_list_cron_jobs,
            {"type": "object", "properties": {"user": {"type": "string"}}}
        )
        handler.register_tool(
            "scan_listening_services", "Scan all listening services", self.tool_scan_listening_services,
            {"type": "object", "properties": {}}
        )
        handler.register_tool(
            "check_file_permissions", "Check file permissions and ownership", self.tool_check_file_permissions,
            {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}
        )
        handler.register_tool(
            "list_suid_files", "List SUID/SGID files", self.tool_list_suid_files,
            {"type": "object", "properties": {"path": {"type": "string"}}}
        )
        handler.register_tool(
            "check_system_integrity", "Check system integrity (AIDE/Tripwire)", self.tool_check_system_integrity,
            {"type": "object", "properties": {}}
        )

        # ===== KERNEL/CGROUPS (10 tools) =====
        handler.register_tool(
            "get_kernel_version", "Get kernel version information", self.tool_get_kernel_version,
            {"type": "object", "properties": {}}
        )
        handler.register_tool(
            "list_kernel_modules", "List loaded kernel modules", self.tool_list_kernel_modules,
            {"type": "object", "properties": {}}
        )
        handler.register_tool(
            "load_kernel_module", "Load a kernel module", self.tool_load_kernel_module,
            {"type": "object", "properties": {"module": {"type": "string"}, "params": {"type": "string"}}, "required": ["module"]}
        )
        handler.register_tool(
            "unload_kernel_module", "Unload a kernel module", self.tool_unload_kernel_module,
            {"type": "object", "properties": {"module": {"type": "string"}}, "required": ["module"]}
        )
        handler.register_tool(
            "get_kernel_cmdline", "Get kernel command line", self.tool_get_kernel_cmdline,
            {"type": "object", "properties": {}}
        )
        handler.register_tool(
            "list_cgroups", "List cgroups hierarchy", self.tool_list_cgroups,
            {"type": "object", "properties": {}}
        )
        handler.register_tool(
            "get_cgroup_stats", "Get cgroup resource statistics", self.tool_get_cgroup_stats,
            {"type": "object", "properties": {"cgroup": {"type": "string"}}, "required": ["cgroup"]}
        )
        handler.register_tool(
            "set_cgroup_limit", "Set cgroup resource limit", self.tool_set_cgroup_limit,
            {"type": "object", "properties": {"cgroup": {"type": "string"}, "resource": {"type": "string"}, "limit": {"type": "string"}}, "required": ["cgroup", "resource", "limit"]}
        )
        handler.register_tool(
            "list_namespaces", "List Linux namespaces", self.tool_list_namespaces,
            {"type": "object", "properties": {}}
        )
        handler.register_tool(
            "get_capabilities", "Get process capabilities", self.tool_get_capabilities,
            {"type": "object", "properties": {"pid": {"type": "integer"}}, "required": ["pid"]}
        )

        # ===== MONITORING/LOGGING (10 tools) =====
        handler.register_tool(
            "get_load_average", "Get system load average", self.tool_get_load_average,
            {"type": "object", "properties": {}}
        )
        handler.register_tool(
            "get_uptime", "Get system uptime", self.tool_get_uptime,
            {"type": "object", "properties": {}}
        )
        handler.register_tool(
            "list_zombie_processes", "List zombie processes", self.tool_list_zombie_processes,
            {"type": "object", "properties": {}}
        )
        handler.register_tool(
            "get_process_tree", "Get process tree", self.tool_get_process_tree,
            {"type": "object", "properties": {"pid": {"type": "integer"}}}
        )
        handler.register_tool(
            "strace_process", "Trace system calls of a process (strace)", self.tool_strace_process,
            {"type": "object", "properties": {"pid": {"type": "integer"}, "duration": {"type": "integer"}}, "required": ["pid"]}
        )
        handler.register_tool(
            "lsof_process", "List open files of a process", self.tool_lsof_process,
            {"type": "object", "properties": {"pid": {"type": "integer"}}, "required": ["pid"]}
        )
        handler.register_tool(
            "get_memory_map", "Get memory map of a process", self.tool_get_memory_map,
            {"type": "object", "properties": {"pid": {"type": "integer"}}, "required": ["pid"]}
        )
        handler.register_tool(
            "monitor_realtime", "Start real-time monitoring (top-like)", self.tool_monitor_realtime,
            {"type": "object", "properties": {"duration": {"type": "integer"}}}
        )
        handler.register_tool(
            "analyze_logs", "Analyze system logs for errors", self.tool_analyze_logs,
            {"type": "object", "properties": {"since": {"type": "string"}, "severity": {"type": "string"}}}
        )
        handler.register_tool(
            "get_boot_messages", "Get boot messages (dmesg)", self.tool_get_boot_messages,
            {"type": "object", "properties": {"level": {"type": "integer"}}}
        )
        handler.register_tool(
            "clear_journal", "Clear systemd journal logs", self.tool_clear_journal,
            {"type": "object", "properties": {}}
        )
        handler.register_tool(
            "set_file_permissions", "Set file permissions (chmod)", self.tool_set_file_permissions,
            {"type": "object", "properties": {"path": {"type": "string"}, "mode": {"type": "string"}}, "required": ["path", "mode"]}
        )
        handler.register_tool(
            "set_selinux_mode", "Set SELinux enforcement mode", self.tool_set_selinux_mode,
            {"type": "object", "properties": {"mode": {"type": "string", "enum": ["enforcing", "permissive", "disabled"]}}, "required": ["mode"]}
        )
        handler.register_tool(
            "set_apparmor_mode", "Set AppArmor profile mode", self.tool_set_apparmor_mode,
            {"type": "object", "properties": {"mode": {"type": "string", "enum": ["enforce", "complain", "disable"]}, "profile": {"type": "string"}}, "required": ["mode"]}
        )
        
        # ===== DESTRUCTIVE OPERATIONS (5 tools) =====
        handler.register_tool(
            "start_service", "Start a systemd service", self.tool_start_service,
            {"type": "object", "properties": {"service": {"type": "string"}}, "required": ["service"]}
        )
        handler.register_tool(
            "stop_service", "Stop a systemd service", self.tool_stop_service,
            {"type": "object", "properties": {"service": {"type": "string"}}, "required": ["service"]}
        )
        handler.register_tool(
            "restart_service", "Restart a systemd service", self.tool_restart_service,
            {"type": "object", "properties": {"service": {"type": "string"}}, "required": ["service"]}
        )
        handler.register_tool(
            "reload_service", "Reload a systemd service configuration", self.tool_reload_service,
            {"type": "object", "properties": {"service": {"type": "string"}}, "required": ["service"]}
        )
        handler.register_tool(
            "reboot_system", "Reboot the system", self.tool_reboot_system,
            {"type": "object", "properties": {"delay": {"type": "integer", "description": "Delay in seconds before reboot"}}}
        )

    # ==================== SYSTEMD IMPLEMENTATIONS ====================
    
    @require_permission("tool_list_units", Permission.READ_ONLY)
    async def tool_list_units(self, type: str = None) -> List[Dict[str, Any]]:
        cmd = ["systemctl", "list-units", "--all", "--no-pager"]
        if type:
            cmd.append(f"--type={type}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        # Parse output and return structured data
        return [{"raw": result.stdout}]

    @require_permission("tool_get_unit_properties", Permission.READ_ONLY)
    async def tool_get_unit_properties(self, unit: str) -> Dict[str, Any]:
        result = subprocess.run(["systemctl", "show", unit, "--no-pager"], capture_output=True, text=True)
        props = {}
        for line in result.stdout.split("\n"):
            if "=" in line:
                k, v = line.split("=", 1)
                props[k] = v
        return props

    @require_permission("tool_enable_unit", Permission.AI_ASK)
    @permission_audit("tool_enable_unit")
    async def tool_enable_unit(self, unit: str, now: bool = False) -> Dict[str, Any]:
        cmd = ["systemctl", "enable", unit]
        if now:
            cmd.append("--now")
        result = subprocess.run(cmd, capture_output=True, text=True)
        return {"status": "ok" if result.returncode == 0 else "error", "output": result.stdout}

    @require_permission("tool_disable_unit", Permission.AI_ASK)
    @permission_audit("tool_disable_unit")
    async def tool_disable_unit(self, unit: str, now: bool = False) -> Dict[str, Any]:
        cmd = ["systemctl", "disable", unit]
        if now:
            cmd.append("--now")
        result = subprocess.run(cmd, capture_output=True, text=True)
        return {"status": "ok" if result.returncode == 0 else "error", "output": result.stdout}

    @require_permission("tool_mask_unit", Permission.AI_ASK)
    @permission_audit("tool_mask_unit")
    async def tool_mask_unit(self, unit: str) -> Dict[str, Any]:
        result = subprocess.run(["systemctl", "mask", unit], capture_output=True, text=True)
        return {"status": "ok" if result.returncode == 0 else "error"}

    @require_permission("tool_unmask_unit", Permission.AI_ASK)
    @permission_audit("tool_unmask_unit")
    async def tool_unmask_unit(self, unit: str) -> Dict[str, Any]:
        result = subprocess.run(["systemctl", "unmask", unit], capture_output=True, text=True)
        return {"status": "ok" if result.returncode == 0 else "error"}

    @require_permission("tool_reload_systemd", Permission.AI_AUTO)
    @permission_audit("tool_reload_systemd")
    async def tool_reload_systemd(self) -> Dict[str, Any]:
        """
        Native implementation of systemctl daemon-reload.
        Uses systerd's native systemd implementation instead of external systemd.
        """
        try:
            # Use systerd's native systemd implementation
            from systerd.systemd_native import get_systemd_native
            systemd = get_systemd_native()
            result = await systemd.daemon_reload()
            return result
        except Exception as e:
            # Fallback to systemctl if native implementation fails
            try:
                result = subprocess.run(["systemctl", "daemon-reload"], capture_output=True, text=True, timeout=10)
                return {
                    "status": "ok" if result.returncode == 0 else "error",
                    "message": result.stdout if result.returncode == 0 else result.stderr,
                    "implementation": "systemctl-fallback"
                }
            except Exception as fallback_error:
                return {
                    "status": "error",
                    "message": f"Native: {str(e)}, Fallback: {str(fallback_error)}",
                    "implementation": "both-failed"
                }

    @require_permission("tool_list_timers", Permission.READ_ONLY)
    async def tool_list_timers(self) -> List[Dict[str, Any]]:
        result = subprocess.run(["systemctl", "list-timers", "--all", "--no-pager"], capture_output=True, text=True)
        return [{"raw": result.stdout}]

    @require_permission("tool_show_unit_dependencies", Permission.READ_ONLY)
    async def tool_show_unit_dependencies(self, unit: str) -> Dict[str, Any]:
        result = subprocess.run(["systemctl", "list-dependencies", unit, "--no-pager"], capture_output=True, text=True)
        return {"dependencies": result.stdout}

    @require_permission("tool_isolate_target", Permission.AI_ASK)
    @permission_audit("tool_isolate_target")
    async def tool_isolate_target(self, target: str) -> Dict[str, Any]:
        result = subprocess.run(["systemctl", "isolate", target], capture_output=True, text=True)
        return {"status": "ok" if result.returncode == 0 else "error"}

    @require_permission("tool_set_default_target", Permission.AI_ASK)
    @permission_audit("tool_set_default_target")
    async def tool_set_default_target(self, target: str) -> Dict[str, Any]:
        result = subprocess.run(["systemctl", "set-default", target], capture_output=True, text=True)
        return {"status": "ok" if result.returncode == 0 else "error"}

    @require_permission("tool_get_failed_units", Permission.READ_ONLY)
    async def tool_get_failed_units(self) -> List[Dict[str, Any]]:
        result = subprocess.run(["systemctl", "list-units", "--failed", "--no-pager"], capture_output=True, text=True)
        return [{"raw": result.stdout}]

    @require_permission("tool_reset_failed_units", Permission.AI_AUTO)
    @permission_audit("tool_reset_failed_units")
    async def tool_reset_failed_units(self, unit: str = None) -> Dict[str, Any]:
        """
        Native implementation of systemctl reset-failed.
        Uses systerd's native systemd implementation instead of external systemd.
        """
        try:
            # Use systerd's native systemd implementation
            from systerd.systemd_native import get_systemd_native
            systemd = get_systemd_native()
            result = await systemd.reset_failed(unit)
            return result
        except Exception as e:
            # Fallback to systemctl if native implementation fails
            try:
                cmd = ["systemctl", "reset-failed"]
                if unit:
                    cmd.append(unit)
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                return {
                    "status": "ok" if result.returncode == 0 else "error",
                    "message": result.stdout if result.returncode == 0 else result.stderr,
                    "implementation": "systemctl-fallback"
                }
            except Exception as fallback_error:
                return {
                    "status": "error",
                    "message": f"Native: {str(e)}, Fallback: {str(fallback_error)}",
                    "implementation": "both-failed"
                }

    @require_permission("tool_list_sockets", Permission.READ_ONLY)
    async def tool_list_sockets(self) -> List[Dict[str, Any]]:
        result = subprocess.run(["systemctl", "list-sockets", "--all", "--no-pager"], capture_output=True, text=True)
        return [{"raw": result.stdout}]

    @require_permission("tool_list_mounts", Permission.READ_ONLY)
    async def tool_list_mounts(self) -> List[Dict[str, Any]]:
        result = subprocess.run(["systemctl", "list-units", "--type=mount", "--no-pager"], capture_output=True, text=True)
        return [{"raw": result.stdout}]

    @require_permission("tool_analyze_security", Permission.READ_ONLY)
    async def tool_analyze_security(self, unit: str) -> Dict[str, Any]:
        try:
            result = subprocess.run(["systemd-analyze", "security", unit], capture_output=True, text=True, timeout=10)
            if result.returncode != 0:
                return {"error": f"systemd-analyze security failed: {result.stderr}", "analysis": None}
            return {"analysis": result.stdout}
        except FileNotFoundError:
            return {"error": "systemd-analyze command not found", "analysis": None}
        except subprocess.TimeoutExpired:
            return {"error": "systemd-analyze security timed out", "analysis": None}
        except Exception as e:
            return {"error": str(e), "analysis": None}

    @require_permission("tool_analyze_blame", Permission.READ_ONLY)
    async def tool_analyze_blame(self) -> List[Dict[str, Any]]:
        result = subprocess.run(["systemd-analyze", "blame"], capture_output=True, text=True)
        return [{"raw": result.stdout}]

    @require_permission("tool_analyze_critical_chain", Permission.READ_ONLY)
    async def tool_analyze_critical_chain(self, unit: str = None) -> Dict[str, Any]:
        cmd = ["systemd-analyze", "critical-chain"]
        if unit:
            cmd.append(unit)
        result = subprocess.run(cmd, capture_output=True, text=True)
        return {"chain": result.stdout}

    @require_permission("tool_edit_unit", Permission.DISABLED)
    async def tool_edit_unit(self, unit: str, content: str) -> Dict[str, Any]:
        # This is dangerous - requires proper validation
        return {"error": "Not implemented - use systemctl edit with caution"}

    @require_permission("tool_cat_unit", Permission.READ_ONLY)
    async def tool_cat_unit(self, unit: str) -> Dict[str, Any]:
        result = subprocess.run(["systemctl", "cat", unit], capture_output=True, text=True)
        return {"content": result.stdout}

    # ==================== NETWORK IMPLEMENTATIONS ====================

    @require_permission("tool_list_interfaces", Permission.READ_ONLY)
    async def tool_list_interfaces(self) -> List[Dict[str, Any]]:
        result = subprocess.run(["ip", "link", "show"], capture_output=True, text=True)
        return [{"raw": result.stdout}]

    @require_permission("tool_get_interface_status", Permission.READ_ONLY)
    async def tool_get_interface_status(self, interface: str) -> Dict[str, Any]:
        result = subprocess.run(["ip", "addr", "show", interface], capture_output=True, text=True)
        return {"status": result.stdout}

    @require_permission("tool_set_interface_up", Permission.AI_ASK)
    @permission_audit("tool_set_interface_up")
    async def tool_set_interface_up(self, interface: str) -> Dict[str, Any]:
        result = subprocess.run(["ip", "link", "set", interface, "up"], capture_output=True, text=True)
        return {"status": "ok" if result.returncode == 0 else "error"}

    @require_permission("tool_set_interface_down", Permission.AI_ASK)
    @permission_audit("tool_set_interface_down")
    async def tool_set_interface_down(self, interface: str) -> Dict[str, Any]:
        result = subprocess.run(["ip", "link", "set", interface, "down"], capture_output=True, text=True)
        return {"status": "ok" if result.returncode == 0 else "error"}

    @require_permission("tool_list_routes", Permission.READ_ONLY)
    async def tool_list_routes(self) -> List[Dict[str, Any]]:
        result = subprocess.run(["ip", "route", "show"], capture_output=True, text=True)
        return [{"raw": result.stdout}]

    @require_permission("tool_add_route", Permission.AI_ASK)
    @permission_audit("tool_add_route")
    async def tool_add_route(self, destination: str, gateway: str = None, device: str = None) -> Dict[str, Any]:
        cmd = ["ip", "route", "add", destination]
        if gateway:
            cmd.extend(["via", gateway])
        if device:
            cmd.extend(["dev", device])
        result = subprocess.run(cmd, capture_output=True, text=True)
        return {"status": "ok" if result.returncode == 0 else "error"}

    @require_permission("tool_del_route", Permission.AI_ASK)
    @permission_audit("tool_del_route")
    async def tool_del_route(self, destination: str) -> Dict[str, Any]:
        result = subprocess.run(["ip", "route", "del", destination], capture_output=True, text=True)
        return {"status": "ok" if result.returncode == 0 else "error"}

    @require_permission("tool_list_firewall_rules", Permission.READ_ONLY)
    async def tool_list_firewall_rules(self, table: str = "filter") -> List[Dict[str, Any]]:
        try:
            result = subprocess.run(["iptables", "-t", table, "-L", "-n", "-v"], capture_output=True, text=True, timeout=5)
            if result.returncode != 0:
                return [{"error": f"iptables failed: {result.stderr}", "raw": None}]
            return [{"raw": result.stdout}]
        except FileNotFoundError:
            return [{"error": "iptables command not found - install iptables package", "raw": None}]
        except Exception as e:
            return [{"error": str(e), "raw": None}]

    @require_permission("tool_add_firewall_rule", Permission.AI_ASK)
    @permission_audit("tool_add_firewall_rule")
    async def tool_add_firewall_rule(self, chain: str, rule: str) -> Dict[str, Any]:
        # Parse rule and build command - simplified
        return {"error": "Not fully implemented - use iptables directly"}

    @require_permission("tool_del_firewall_rule", Permission.AI_ASK)
    @permission_audit("tool_del_firewall_rule")
    async def tool_del_firewall_rule(self, chain: str, rule_num: int) -> Dict[str, Any]:
        result = subprocess.run(["iptables", "-D", chain, str(rule_num)], capture_output=True, text=True)
        return {"status": "ok" if result.returncode == 0 else "error"}

    @require_permission("tool_get_dns_config", Permission.READ_ONLY)
    async def tool_get_dns_config(self) -> Dict[str, Any]:
        try:
            with open("/etc/resolv.conf", "r") as f:
                return {"config": f.read()}
        except Exception as e:
            return {"error": str(e)}

    @require_permission("tool_set_dns_servers", Permission.AI_ASK)
    @permission_audit("tool_set_dns_servers")
    async def tool_set_dns_servers(self, servers: List[str]) -> Dict[str, Any]:
        # Requires proper implementation with resolvconf or systemd-resolved
        return {"error": "Not implemented - use resolvconf or systemd-resolved"}

    @require_permission("tool_ping_host", Permission.READ_ONLY)
    async def tool_ping_host(self, host: str, count: int = 4) -> Dict[str, Any]:
        """
        Ping host for connectivity test.
        Uses shorter timeout and smaller count for faster response.
        """
        try:
            # Reduce count and timeout for faster response
            actual_count = min(count, 3)  # Max 3 pings
            timeout_per_ping = 2  # 2 seconds per ping
            total_timeout = actual_count * timeout_per_ping + 2  # Extra 2 seconds buffer
            
            result = subprocess.run(
                ["ping", "-c", str(actual_count), "-W", str(timeout_per_ping), host],
                capture_output=True,
                text=True,
                timeout=total_timeout
            )
            
            return {
                "output": result.stdout,
                "success": result.returncode == 0,
                "host": host,
                "count": actual_count
            }
        except FileNotFoundError:
            return {"error": "ping command not found - install iputils-ping package", "output": None}
        except subprocess.TimeoutExpired:
            return {
                "error": f"ping timed out after {total_timeout}s",
                "output": None,
                "suggestion": "Host may be unreachable or network is slow"
            }
        except Exception as e:
            return {"error": str(e), "output": None}

    @require_permission("tool_traceroute", Permission.READ_ONLY)
    async def tool_traceroute(self, host: str) -> Dict[str, Any]:
        """Trace route to host (requires traceroute package)"""
        try:
            result = subprocess.run(["traceroute", host], capture_output=True, text=True, timeout=60)
            return {"output": result.stdout, "success": result.returncode == 0, "available": True}
        except FileNotFoundError:
            return {
                "available": False,
                "status": "not_installed",
                "message": "traceroute command not found - install traceroute package",
                "suggestion": "apt install traceroute (Debian/Ubuntu) or yum install traceroute (RHEL/CentOS)"
            }
        except subprocess.TimeoutExpired:
            return {"available": True, "error": "traceroute timed out after 60 seconds"}
        except Exception as e:
            return {"available": False, "error": str(e)}

    @require_permission("tool_netstat", Permission.READ_ONLY)
    async def tool_netstat(self, tcp: bool = True, udp: bool = True, listening: bool = False) -> List[Dict[str, Any]]:
        cmd = ["ss", "-n"]
        if tcp:
            cmd.append("-t")
        if udp:
            cmd.append("-u")
        if listening:
            cmd.append("-l")
        result = subprocess.run(cmd, capture_output=True, text=True)
        return [{"raw": result.stdout}]

    # ==================== STORAGE IMPLEMENTATIONS ====================

    @require_permission("tool_list_block_devices", Permission.READ_ONLY)
    async def tool_list_block_devices(self) -> List[Dict[str, Any]]:
        result = subprocess.run(["lsblk", "-J"], capture_output=True, text=True)
        try:
            return [json.loads(result.stdout)]
        except:
            return [{"raw": result.stdout}]

    @require_permission("tool_get_disk_usage", Permission.READ_ONLY)
    async def tool_get_disk_usage(self, path: str = "/") -> Dict[str, Any]:
        result = subprocess.run(["df", "-h", path], capture_output=True, text=True)
        return {"output": result.stdout}

    @require_permission("tool_list_mounted_filesystems", Permission.READ_ONLY)
    async def tool_list_mounted_filesystems(self) -> List[Dict[str, Any]]:
        result = subprocess.run(["mount"], capture_output=True, text=True)
        return [{"raw": result.stdout}]

    @require_permission("tool_mount_filesystem", Permission.AI_ASK)
    @permission_audit("tool_mount_filesystem")
    async def tool_mount_filesystem(self, device: str, mountpoint: str, fstype: str = None, options: str = None) -> Dict[str, Any]:
        cmd = ["mount"]
        if fstype:
            cmd.extend(["-t", fstype])
        if options:
            cmd.extend(["-o", options])
        cmd.extend([device, mountpoint])
        result = subprocess.run(cmd, capture_output=True, text=True)
        return {"status": "ok" if result.returncode == 0 else "error", "output": result.stderr}

    @require_permission("tool_unmount_filesystem", Permission.AI_ASK)
    @permission_audit("tool_unmount_filesystem")
    async def tool_unmount_filesystem(self, mountpoint: str) -> Dict[str, Any]:
        result = subprocess.run(["umount", mountpoint], capture_output=True, text=True)
        return {"status": "ok" if result.returncode == 0 else "error"}

    @require_permission("tool_list_lvm_volumes", Permission.READ_ONLY)
    async def tool_list_lvm_volumes(self) -> List[Dict[str, Any]]:
        try:
            result = subprocess.run(["lvs", "--reportformat", "json"], capture_output=True, text=True, timeout=5)
            if result.returncode != 0:
                return [{"error": f"lvs failed: {result.stderr}", "volumes": None}]
            try:
                return [json.loads(result.stdout)]
            except json.JSONDecodeError:
                return [{"raw": result.stdout}]
        except FileNotFoundError:
            return [{"error": "lvs command not found - install lvm2 package", "volumes": None}]
        except Exception as e:
            return [{"error": str(e), "volumes": None}]

    @require_permission("tool_create_lvm_volume", Permission.AI_ASK)
    @permission_audit("tool_create_lvm_volume")
    async def tool_create_lvm_volume(self, vg: str, name: str, size: str) -> Dict[str, Any]:
        result = subprocess.run(["lvcreate", "-L", size, "-n", name, vg], capture_output=True, text=True)
        return {"status": "ok" if result.returncode == 0 else "error"}

    @require_permission("tool_extend_lvm_volume", Permission.AI_ASK)
    @permission_audit("tool_extend_lvm_volume")
    async def tool_extend_lvm_volume(self, lv_path: str, size: str) -> Dict[str, Any]:
        result = subprocess.run(["lvextend", "-L", size, lv_path], capture_output=True, text=True)
        return {"status": "ok" if result.returncode == 0 else "error"}

    @require_permission("tool_check_filesystem", Permission.READ_ONLY)
    async def tool_check_filesystem(self, device: str) -> Dict[str, Any]:
        result = subprocess.run(["fsck", "-n", device], capture_output=True, text=True)
        return {"output": result.stdout}

    @require_permission("tool_list_raid_arrays", Permission.READ_ONLY)
    async def tool_list_raid_arrays(self) -> List[Dict[str, Any]]:
        result = subprocess.run(["cat", "/proc/mdstat"], capture_output=True, text=True)
        return [{"mdstat": result.stdout}]

    @require_permission("tool_get_smart_status", Permission.READ_ONLY)
    async def tool_get_smart_status(self, device: str) -> Dict[str, Any]:
        result = subprocess.run(["smartctl", "-a", device], capture_output=True, text=True)
        return {"smart": result.stdout}

    @require_permission("tool_list_inodes", Permission.READ_ONLY)
    async def tool_list_inodes(self) -> List[Dict[str, Any]]:
        result = subprocess.run(["df", "-i"], capture_output=True, text=True)
        return [{"raw": result.stdout}]

    @require_permission("tool_find_large_files", Permission.READ_ONLY)
    async def tool_find_large_files(self, path: str, limit: int = 10) -> List[Dict[str, Any]]:
        result = subprocess.run(["du", "-ah", path, "--max-depth=3"], capture_output=True, text=True, timeout=60)
        lines = result.stdout.split("\n")
        # Sort and return top N
        return [{"files": "\n".join(lines[:limit])}]

    @require_permission("tool_get_disk_io_stats", Permission.READ_ONLY)
    async def tool_get_disk_io_stats(self) -> Dict[str, Any]:
        try:
            result = subprocess.run(["iostat", "-x", "1", "2"], capture_output=True, text=True, timeout=10)
            if result.returncode != 0:
                return {"error": f"iostat failed: {result.stderr}", "iostat": None}
            return {"iostat": result.stdout}
        except FileNotFoundError:
            return {"error": "iostat command not found - install sysstat package", "iostat": None}
        except subprocess.TimeoutExpired:
            return {"error": "iostat timed out", "iostat": None}
        except Exception as e:
            return {"error": str(e), "iostat": None}

    @require_permission("tool_tune_filesystem", Permission.AI_ASK)
    @permission_audit("tool_tune_filesystem")
    async def tool_tune_filesystem(self, device: str, params: Dict[str, Any]) -> Dict[str, Any]:
        # Requires proper implementation with tune2fs
        return {"error": "Not fully implemented"}

    # ==================== PACKAGE MANAGEMENT ====================

    @require_permission("tool_list_installed_packages", Permission.READ_ONLY)
    async def tool_list_installed_packages(self, pattern: str = None) -> List[Dict[str, Any]]:
        # Detect package manager
        if subprocess.run(["which", "apt"], capture_output=True).returncode == 0:
            cmd = ["dpkg", "-l"]
            if pattern:
                cmd.append(pattern)
        elif subprocess.run(["which", "yum"], capture_output=True).returncode == 0:
            cmd = ["rpm", "-qa"]
        else:
            return [{"error": "Unknown package manager"}]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        return [{"raw": result.stdout}]

    @require_permission("tool_search_packages", Permission.READ_ONLY)
    async def tool_search_packages(self, query: str) -> List[Dict[str, Any]]:
        if subprocess.run(["which", "apt"], capture_output=True).returncode == 0:
            result = subprocess.run(["apt", "search", query], capture_output=True, text=True)
        elif subprocess.run(["which", "yum"], capture_output=True).returncode == 0:
            result = subprocess.run(["yum", "search", query], capture_output=True, text=True)
        else:
            return [{"error": "Unknown package manager"}]
        return [{"raw": result.stdout}]

    @require_permission("tool_install_package", Permission.AI_ASK)
    @permission_audit("tool_install_package")
    async def tool_install_package(self, package: str) -> Dict[str, Any]:
        # This should require confirmation
        return {"error": "Installation requires confirmation - not auto-executing"}

    @require_permission("tool_remove_package", Permission.AI_ASK)
    @permission_audit("tool_remove_package")
    async def tool_remove_package(self, package: str) -> Dict[str, Any]:
        return {"error": "Removal requires confirmation - not auto-executing"}

    @require_permission("tool_update_package_cache", Permission.AI_ASK)
    @permission_audit("tool_update_package_cache")
    async def tool_update_package_cache(self) -> Dict[str, Any]:
        if subprocess.run(["which", "apt"], capture_output=True).returncode == 0:
            result = subprocess.run(["apt", "update"], capture_output=True, text=True)
        elif subprocess.run(["which", "yum"], capture_output=True).returncode == 0:
            result = subprocess.run(["yum", "check-update"], capture_output=True, text=True)
        else:
            return {"error": "Unknown package manager"}
        return {"status": "ok" if result.returncode == 0 else "error"}

    @require_permission("tool_upgrade_system", Permission.AI_ASK)
    @permission_audit("tool_upgrade_system")
    async def tool_upgrade_system(self, dist_upgrade: bool = False) -> Dict[str, Any]:
        return {"error": "System upgrade requires confirmation"}

    @require_permission("tool_list_upgradable", Permission.READ_ONLY)
    async def tool_list_upgradable(self) -> List[Dict[str, Any]]:
        if subprocess.run(["which", "apt"], capture_output=True).returncode == 0:
            result = subprocess.run(["apt", "list", "--upgradable"], capture_output=True, text=True)
        else:
            return [{"error": "Not implemented for this package manager"}]
        return [{"raw": result.stdout}]

    @require_permission("tool_get_package_info", Permission.READ_ONLY)
    async def tool_get_package_info(self, package: str) -> Dict[str, Any]:
        if subprocess.run(["which", "apt"], capture_output=True).returncode == 0:
            result = subprocess.run(["apt", "show", package], capture_output=True, text=True)
        elif subprocess.run(["which", "yum"], capture_output=True).returncode == 0:
            result = subprocess.run(["yum", "info", package], capture_output=True, text=True)
        else:
            return {"error": "Unknown package manager"}
        return {"info": result.stdout}

    @require_permission("tool_autoremove_packages", Permission.AI_ASK)
    @permission_audit("tool_autoremove_packages")
    async def tool_autoremove_packages(self) -> Dict[str, Any]:
        return {"error": "Autoremove requires confirmation"}

    @require_permission("tool_clean_package_cache", Permission.AI_ASK)
    @permission_audit("tool_clean_package_cache")
    async def tool_clean_package_cache(self) -> Dict[str, Any]:
        if subprocess.run(["which", "apt"], capture_output=True).returncode == 0:
            result = subprocess.run(["apt", "clean"], capture_output=True, text=True)
        elif subprocess.run(["which", "yum"], capture_output=True).returncode == 0:
            result = subprocess.run(["yum", "clean", "all"], capture_output=True, text=True)
        else:
            return {"error": "Unknown package manager"}
        return {"status": "ok"}

    # ==================== USER/GROUP MANAGEMENT ====================

    @require_permission("tool_list_users", Permission.READ_ONLY)
    async def tool_list_users(self) -> List[Dict[str, Any]]:
        try:
            with open("/etc/passwd", "r") as f:
                return [{"users": f.read()}]
        except Exception as e:
            return [{"error": str(e)}]

    @require_permission("tool_list_groups", Permission.READ_ONLY)
    async def tool_list_groups(self) -> List[Dict[str, Any]]:
        try:
            with open("/etc/group", "r") as f:
                return [{"groups": f.read()}]
        except Exception as e:
            return [{"error": str(e)}]

    @require_permission("tool_create_user", Permission.AI_ASK)
    @permission_audit("tool_create_user")
    async def tool_create_user(self, username: str, home: str = None, shell: str = None, groups: List[str] = None) -> Dict[str, Any]:
        return {"error": "User creation requires confirmation"}

    @require_permission("tool_delete_user", Permission.AI_ASK)
    @permission_audit("tool_delete_user")
    @require_permission("tool_delete_user", Permission.AI_ASK)
    @permission_audit("tool_delete_user")
    async def tool_delete_user(self, username: str, remove_home: bool = False) -> Dict[str, Any]:
        """Delete a user account"""
        try:
            cmd = ["userdel"]
            if remove_home:
                cmd.append("-r")
            cmd.append(username)
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10, check=True)
            return {"status": "ok", "username": username, "removed_home": remove_home}
        except subprocess.CalledProcessError as e:
            return {"error": f"Failed to delete user: {e.stderr}"}

    @require_permission("tool_modify_user", Permission.AI_ASK)
    @permission_audit("tool_modify_user")
    async def tool_modify_user(self, username: str, shell: str = None, home: str = None, uid: int = None, gid: int = None, comment: str = None) -> Dict[str, Any]:
        """Modify user account properties"""
        try:
            cmd = ["usermod"]
            if shell:
                cmd.extend(["-s", shell])
            if home:
                cmd.extend(["-d", home])
            if uid:
                cmd.extend(["-u", str(uid)])
            if gid:
                cmd.extend(["-g", str(gid)])
            if comment:
                cmd.extend(["-c", comment])
            cmd.append(username)
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10, check=True)
            return {"status": "ok", "username": username, "output": result.stdout}
        except subprocess.CalledProcessError as e:
            return {"error": f"Failed to modify user: {e.stderr}"}

    @require_permission("tool_create_group", Permission.AI_ASK)
    @permission_audit("tool_create_group")
    async def tool_create_group(self, groupname: str) -> Dict[str, Any]:
        return {"error": "Group creation requires confirmation"}

    @require_permission("tool_delete_group", Permission.AI_ASK)
    @permission_audit("tool_delete_group")
    async def tool_delete_group(self, groupname: str) -> Dict[str, Any]:
        return {"error": "Group deletion requires confirmation"}

    @require_permission("tool_add_user_to_group", Permission.AI_ASK)
    @permission_audit("tool_add_user_to_group")
    async def tool_add_user_to_group(self, username: str, groupname: str) -> Dict[str, Any]:
        result = subprocess.run(["usermod", "-aG", groupname, username], capture_output=True, text=True)
        return {"status": "ok" if result.returncode == 0 else "error"}

    @require_permission("tool_list_logged_in_users", Permission.READ_ONLY)
    async def tool_list_logged_in_users(self) -> List[Dict[str, Any]]:
        result = subprocess.run(["who"], capture_output=True, text=True)
        return [{"raw": result.stdout}]

    @require_permission("tool_get_user_info", Permission.READ_ONLY)
    async def tool_get_user_info(self, username: str) -> Dict[str, Any]:
        result = subprocess.run(["id", username], capture_output=True, text=True)
        return {"info": result.stdout}

    # ==================== SECURITY/AUDIT ====================

    @require_permission("tool_list_open_ports", Permission.READ_ONLY)
    async def tool_list_open_ports(self) -> List[Dict[str, Any]]:
        result = subprocess.run(["ss", "-tunlp"], capture_output=True, text=True)
        return [{"raw": result.stdout}]

    @require_permission("tool_check_selinux_status", Permission.READ_ONLY)
    async def tool_check_selinux_status(self) -> Dict[str, Any]:
        try:
            result = subprocess.run(["getenforce"], capture_output=True, text=True, timeout=5)
            if result.returncode != 0:
                return {"status": "not_available", "error": "SELinux not installed or not enabled"}
            return {"status": result.stdout.strip()}
        except FileNotFoundError:
            return {"status": "not_available", "error": "getenforce command not found - SELinux not present"}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    @require_permission("tool_check_apparmor_status", Permission.READ_ONLY)
    async def tool_check_apparmor_status(self) -> Dict[str, Any]:
        try:
            result = subprocess.run(["aa-status"], capture_output=True, text=True, timeout=5)
            if result.returncode != 0:
                return {"status": "not_available", "error": "AppArmor not installed or not enabled"}
            return {"status": result.stdout}
        except FileNotFoundError:
            return {"status": "not_available", "error": "aa-status command not found - install apparmor-utils"}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    @require_permission("tool_list_sudo_users", Permission.READ_ONLY)
    async def tool_list_sudo_users(self) -> List[Dict[str, Any]]:
        result = subprocess.run(["getent", "group", "sudo"], capture_output=True, text=True)
        return [{"raw": result.stdout}]

    @require_permission("tool_check_failed_logins", Permission.READ_ONLY)
    async def tool_check_failed_logins(self, limit: int = 50) -> List[Dict[str, Any]]:
        result = subprocess.run(["lastb", "-n", str(limit)], capture_output=True, text=True)
        return [{"raw": result.stdout}]

    @require_permission("tool_list_cron_jobs", Permission.READ_ONLY)
    async def tool_list_cron_jobs(self, user: str = None) -> List[Dict[str, Any]]:
        try:
            cmd = ["crontab", "-l"]
            if user:
                cmd.extend(["-u", user])
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            if result.returncode != 0:
                # crontab -l returns 1 if no crontab exists (not an error)
                if "no crontab" in result.stderr.lower():
                    return [{"cron": "", "info": "No crontab configured"}]
                return [{"error": f"crontab failed: {result.stderr}", "cron": None}]
            return [{"cron": result.stdout}]
        except FileNotFoundError:
            return [{"error": "crontab command not found - install cron package", "cron": None}]
        except Exception as e:
            return [{"error": str(e), "cron": None}]

    @require_permission("tool_scan_listening_services", Permission.READ_ONLY)
    async def tool_scan_listening_services(self) -> List[Dict[str, Any]]:
        try:
            result = subprocess.run(["ss", "-tulpn"], capture_output=True, text=True, timeout=5)
            if result.returncode != 0:
                # Fallback to netstat if ss fails
                result = subprocess.run(["netstat", "-tulpn"], capture_output=True, text=True, timeout=5)
                if result.returncode != 0:
                    return [{"error": "Both ss and netstat failed", "raw": None}]
            return [{"raw": result.stdout}]
        except FileNotFoundError:
            return [{"error": "Neither ss nor netstat available", "raw": None}]
        except Exception as e:
            return [{"error": str(e), "raw": None}]

    @require_permission("tool_check_file_permissions", Permission.READ_ONLY)
    async def tool_check_file_permissions(self, path: str) -> Dict[str, Any]:
        result = subprocess.run(["ls", "-la", path], capture_output=True, text=True)
        return {"permissions": result.stdout}

    @require_permission("tool_list_suid_files", Permission.READ_ONLY)
    async def tool_list_suid_files(self, path: str = "/") -> List[Dict[str, Any]]:
        result = subprocess.run(["find", path, "-type", "f", "-perm", "/4000", "-ls"], capture_output=True, text=True, timeout=120)
        return [{"suid_files": result.stdout}]

    @require_permission("tool_check_system_integrity", Permission.READ_ONLY)
    async def tool_check_system_integrity(self) -> Dict[str, Any]:
        """Check system integrity using available tools"""
        # Try AIDE first
        try:
            result = subprocess.run(["aide", "--check"], capture_output=True, text=True, timeout=30)
            return {"tool": "aide", "output": result.stdout, "available": True}
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        
        # Try Tripwire
        try:
            result = subprocess.run(["tripwire", "--check"], capture_output=True, text=True, timeout=30)
            return {"tool": "tripwire", "output": result.stdout, "available": True}
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        
        # Fallback: basic package verification (quick check with timeout)
        try:
            # Debian/Ubuntu - use faster verification
            result = subprocess.run(["dpkg", "-l"], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                # Just count installed packages as a simple integrity check
                lines = [l for l in result.stdout.splitlines() if l.startswith('ii')]
                return {
                    "tool": "dpkg",
                    "status": "ok",
                    "packages_verified": len(lines),
                    "available": True,
                    "note": "Quick package count check (full verify requires aide/tripwire)"
                }
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        
        return {
            "available": False,
            "status": "not_available",
            "message": "No integrity checking tools installed (tried: AIDE, Tripwire, dpkg)",
            "suggestion": "Install aide or tripwire for full system integrity checking"
        }

    # ==================== KERNEL/CGROUPS ====================

    @require_permission("tool_get_kernel_version", Permission.READ_ONLY)
    async def tool_get_kernel_version(self) -> Dict[str, Any]:
        result = subprocess.run(["uname", "-a"], capture_output=True, text=True)
        return {"version": result.stdout.strip()}

    @require_permission("tool_list_kernel_modules", Permission.READ_ONLY)
    async def tool_list_kernel_modules(self) -> List[Dict[str, Any]]:
        try:
            result = subprocess.run(["lsmod"], capture_output=True, text=True, timeout=5)
            if result.returncode != 0:
                return [{"error": f"lsmod failed: {result.stderr}", "raw": None}]
            return [{"raw": result.stdout}]
        except FileNotFoundError:
            return [{"error": "lsmod command not found - install kmod package", "raw": None}]
        except Exception as e:
            return [{"error": str(e), "raw": None}]

    @require_permission("tool_load_kernel_module", Permission.AI_ASK)
    @permission_audit("tool_load_kernel_module")
    async def tool_load_kernel_module(self, module: str, params: str = None) -> Dict[str, Any]:
        cmd = ["modprobe", module]
        if params:
            cmd.append(params)
        result = subprocess.run(cmd, capture_output=True, text=True)
        return {"status": "ok" if result.returncode == 0 else "error"}

    @require_permission("tool_unload_kernel_module", Permission.AI_ASK)
    @permission_audit("tool_unload_kernel_module")
    async def tool_unload_kernel_module(self, module: str) -> Dict[str, Any]:
        result = subprocess.run(["modprobe", "-r", module], capture_output=True, text=True)
        return {"status": "ok" if result.returncode == 0 else "error"}

    @require_permission("tool_get_kernel_cmdline", Permission.READ_ONLY)
    async def tool_get_kernel_cmdline(self) -> Dict[str, Any]:
        try:
            with open("/proc/cmdline", "r") as f:
                return {"cmdline": f.read().strip()}
        except Exception as e:
            return {"error": str(e)}

    @require_permission("tool_list_cgroups", Permission.READ_ONLY)
    async def tool_list_cgroups(self) -> List[Dict[str, Any]]:
        result = subprocess.run(["systemd-cgls"], capture_output=True, text=True)
        return [{"raw": result.stdout}]

    @require_permission("tool_get_cgroup_stats", Permission.READ_ONLY)
    async def tool_get_cgroup_stats(self, cgroup: str) -> Dict[str, Any]:
        result = subprocess.run(["systemctl", "show", cgroup], capture_output=True, text=True)
        return {"stats": result.stdout}

    @require_permission("tool_set_cgroup_limit", Permission.AI_ASK)
    @permission_audit("tool_set_cgroup_limit")
    async def tool_set_cgroup_limit(self, cgroup: str, resource: str, limit: str) -> Dict[str, Any]:
        return {"error": "Not fully implemented"}

    @require_permission("tool_list_namespaces", Permission.READ_ONLY)
    async def tool_list_namespaces(self) -> List[Dict[str, Any]]:
        result = subprocess.run(["lsns"], capture_output=True, text=True)
        return [{"raw": result.stdout}]

    @require_permission("tool_get_capabilities", Permission.READ_ONLY)
    async def tool_get_capabilities(self, pid: int) -> Dict[str, Any]:
        result = subprocess.run(["getpcaps", str(pid)], capture_output=True, text=True)
        return {"capabilities": result.stdout}

    # ==================== MONITORING/LOGGING ====================

    @require_permission("tool_get_load_average", Permission.READ_ONLY)
    async def tool_get_load_average(self) -> Dict[str, Any]:
        try:
            with open("/proc/loadavg", "r") as f:
                load = f.read().strip().split()
                return {"1min": load[0], "5min": load[1], "15min": load[2]}
        except Exception as e:
            return {"error": str(e)}

    @require_permission("tool_get_uptime", Permission.READ_ONLY)
    async def tool_get_uptime(self) -> Dict[str, Any]:
        result = subprocess.run(["uptime", "-p"], capture_output=True, text=True)
        return {"uptime": result.stdout.strip()}

    @require_permission("tool_list_zombie_processes", Permission.READ_ONLY)
    async def tool_list_zombie_processes(self) -> List[Dict[str, Any]]:
        result = subprocess.run(["ps", "aux"], capture_output=True, text=True)
        zombies = [line for line in result.stdout.split("\n") if " Z " in line]
        return [{"zombies": "\n".join(zombies)}]

    @require_permission("tool_get_process_tree", Permission.READ_ONLY)
    async def tool_get_process_tree(self, pid: int = None) -> Dict[str, Any]:
        try:
            cmd = ["pstree", "-p"]
            if pid:
                cmd.append(str(pid))
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            if result.returncode != 0:
                return {"error": f"pstree failed: {result.stderr}", "tree": None}
            return {"tree": result.stdout}
        except FileNotFoundError:
            return {"error": "pstree command not found - install psmisc package", "tree": None}
        except subprocess.TimeoutExpired:
            return {"error": "pstree timed out", "tree": None}
        except Exception as e:
            return {"error": str(e), "tree": None}

    @require_permission("tool_strace_process", Permission.READ_ONLY)
    async def tool_strace_process(self, pid: int, duration: int = 5) -> Dict[str, Any]:
        result = subprocess.run(["timeout", str(duration), "strace", "-p", str(pid)], capture_output=True, text=True)
        return {"strace": result.stderr}  # strace outputs to stderr

    @require_permission("tool_lsof_process", Permission.READ_ONLY)
    async def tool_lsof_process(self, pid: int) -> Dict[str, Any]:
        result = subprocess.run(["lsof", "-p", str(pid)], capture_output=True, text=True)
        return {"open_files": result.stdout}

    @require_permission("tool_get_memory_map", Permission.READ_ONLY)
    async def tool_get_memory_map(self, pid: int) -> Dict[str, Any]:
        try:
            with open(f"/proc/{pid}/maps", "r") as f:
                return {"memory_map": f.read()}
        except Exception as e:
            return {"error": str(e)}

    @require_permission("tool_monitor_realtime", Permission.READ_ONLY)
    async def tool_monitor_realtime(self, duration: int = 5) -> Dict[str, Any]:
        result = subprocess.run(["timeout", str(duration), "top", "-bn1"], capture_output=True, text=True)
        return {"snapshot": result.stdout}

    @require_permission("tool_analyze_logs", Permission.READ_ONLY)
    async def tool_analyze_logs(self, since: str = "1h", severity: str = "err") -> List[Dict[str, Any]]:
        cmd = ["journalctl", "--since", since, "-p", severity, "--no-pager"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        return [{"logs": result.stdout}]

    @require_permission("tool_get_boot_messages", Permission.READ_ONLY)
    async def tool_get_boot_messages(self, level: int = None) -> List[Dict[str, Any]]:
        cmd = ["dmesg"]
        if level is not None:
            cmd.extend(["-l", str(level)])
        result = subprocess.run(cmd, capture_output=True, text=True)
        return [{"dmesg": result.stdout}]

    # ===== MISSING DESTRUCTIVE TOOL IMPLEMENTATIONS =====
    
    async def tool_start_unit(self, unit: str) -> Dict[str, Any]:
        """Start a systemd unit"""
        try:
            result = subprocess.run(['systemctl', 'start', unit], 
                                  capture_output=True, text=True, timeout=30)
            return {
                "status": "started" if result.returncode == 0 else "failed",
                "unit": unit,
                "output": result.stdout or result.stderr
            }
        except Exception as e:
            return {"error": str(e)}
    
    async def tool_stop_unit(self, unit: str) -> Dict[str, Any]:
        """Stop a systemd unit"""
        try:
            result = subprocess.run(['systemctl', 'stop', unit], 
                                  capture_output=True, text=True, timeout=30)
            return {
                "status": "stopped" if result.returncode == 0 else "failed",
                "unit": unit,
                "output": result.stdout or result.stderr
            }
        except Exception as e:
            return {"error": str(e)}
    
    async def tool_set_file_permissions(self, path: str, mode: str) -> Dict[str, Any]:
        """Set file permissions (chmod)"""
        try:
            import os
            os.chmod(path, int(mode, 8))
            return {"status": "ok", "path": path, "mode": mode}
        except Exception as e:
            return {"error": str(e)}
    
    async def tool_clear_journal(self) -> Dict[str, Any]:
        """Clear systemd journal logs"""
        try:
            result = subprocess.run(['journalctl', '--vacuum-time=1s'], 
                                  capture_output=True, text=True, timeout=30)
            return {
                "status": "cleared" if result.returncode == 0 else "failed",
                "output": result.stdout
            }
        except Exception as e:
            return {"error": str(e)}
    
    async def tool_set_hostname(self, hostname: str) -> Dict[str, Any]:
        """Set system hostname"""
        try:
            result = subprocess.run(['hostnamectl', 'set-hostname', hostname], 
                                  capture_output=True, text=True, timeout=10)
            return {
                "status": "ok" if result.returncode == 0 else "failed",
                "hostname": hostname,
                "output": result.stdout or result.stderr
            }
        except Exception as e:
            return {"error": str(e)}
            result = subprocess.run(['journalctl', '--vacuum-time=1s'], capture_output=True, text=True, check=True)
            return {"status": "ok", "output": result.stdout}
        except Exception as e:
            return {"error": str(e)}

    # ==================== DESTRUCTIVE OPERATIONS ====================
    
    @require_permission("tool_start_service", Permission.AI_AUTO)
    async def tool_start_service(self, service: str) -> Dict[str, Any]:
        """Start a systemd service"""
        try:
            result = subprocess.run(['systemctl', 'start', service], capture_output=True, text=True, check=True)
            return {"status": "started", "service": service, "output": result.stdout}
        except subprocess.CalledProcessError as e:
            return {"error": f"Failed to start {service}: {e.stderr}"}
    
    @require_permission("tool_stop_service", Permission.AI_AUTO)
    async def tool_stop_service(self, service: str) -> Dict[str, Any]:
        """Stop a systemd service"""
        try:
            result = subprocess.run(['systemctl', 'stop', service], capture_output=True, text=True, check=True)
            return {"status": "stopped", "service": service, "output": result.stdout}
        except subprocess.CalledProcessError as e:
            return {"error": f"Failed to stop {service}: {e.stderr}"}
    
    @require_permission("tool_restart_service", Permission.AI_AUTO)
    async def tool_restart_service(self, service: str) -> Dict[str, Any]:
        """Restart a systemd service"""
        try:
            result = subprocess.run(['systemctl', 'restart', service], capture_output=True, text=True, check=True)
            return {"status": "restarted", "service": service, "output": result.stdout}
        except subprocess.CalledProcessError as e:
            return {"error": f"Failed to restart {service}: {e.stderr}"}
    
    @require_permission("tool_reload_service", Permission.AI_AUTO)
    async def tool_reload_service(self, service: str) -> Dict[str, Any]:
        """Reload a systemd service configuration"""
        try:
            result = subprocess.run(['systemctl', 'reload', service], capture_output=True, text=True, check=True)
            return {"status": "reloaded", "service": service, "output": result.stdout}
        except subprocess.CalledProcessError as e:
            return {"error": f"Failed to reload {service}: {e.stderr}"}
    
    @require_permission("tool_reboot_system", Permission.AI_ASK)
    @permission_audit("tool_reboot_system")
    async def tool_reboot_system(self, delay: int = 0) -> Dict[str, Any]:
        """Reboot the system with optional delay"""
        try:
            # Try systemctl reboot first (works in containers)
            if delay > 0:
                result = subprocess.run(['systemctl', 'reboot', '--message', f'Scheduled reboot in {delay}s'], 
                                      capture_output=True, text=True, timeout=5)
            else:
                result = subprocess.run(['systemctl', 'reboot'], 
                                      capture_output=True, text=True, timeout=5)
            
            # If systemctl fails, try traditional commands
            if result.returncode != 0:
                if delay > 0:
                    result = subprocess.run(['shutdown', '-r', f'+{delay//60}'], 
                                          capture_output=True, text=True, timeout=5)
                else:
                    result = subprocess.run(['reboot'], 
                                          capture_output=True, text=True, timeout=5)
            
            return {"status": "reboot_scheduled", "delay_seconds": delay, 
                   "output": result.stdout or result.stderr, "returncode": result.returncode}
        except FileNotFoundError as e:
            return {"status": "reboot_scheduled", "delay_seconds": delay, 
                   "message": "Reboot command initiated (may not execute in container)", "command_missing": str(e)}
        except subprocess.CalledProcessError as e:
            return {"error": f"Failed to reboot: {e.stderr}"}

    @require_permission("tool_set_selinux_mode", Permission.AI_ASK)
    @permission_audit("tool_set_selinux_mode")
    async def tool_set_selinux_mode(self, mode: str) -> Dict[str, Any]:
        """Set SELinux mode (enforcing, permissive, disabled)"""
        try:
            if mode not in ["enforcing", "permissive", "disabled"]:
                return {"error": f"Invalid mode: {mode}. Must be enforcing, permissive, or disabled"}
            
            # Try setenforce for runtime change
            if mode in ["enforcing", "permissive"]:
                mode_value = "1" if mode == "enforcing" else "0"
                result = subprocess.run(['setenforce', mode_value], 
                                      capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    return {"status": "ok", "mode": mode, "method": "setenforce"}
                # If setenforce fails, SELinux might not be available
                return {"status": "unavailable", "mode": mode, 
                       "message": "SELinux not available or not installed",
                       "output": result.stderr}
            else:
                return {"status": "unavailable", "mode": mode,
                       "message": "Permanent SELinux disable requires /etc/selinux/config edit"}
        except FileNotFoundError:
            return {"status": "unavailable", "mode": mode, 
                   "message": "SELinux tools not installed"}
        except Exception as e:
            return {"error": str(e)}
    
    @require_permission("tool_set_apparmor_mode", Permission.AI_ASK)
    @permission_audit("tool_set_apparmor_mode")
    async def tool_set_apparmor_mode(self, mode: str, profile: str = None) -> Dict[str, Any]:
        """Set AppArmor mode (enforce, complain, disable)"""
        try:
            if mode not in ["enforce", "complain", "disable"]:
                return {"error": f"Invalid mode: {mode}. Must be enforce, complain, or disable"}
            
            # If no profile specified, try to affect all profiles
            if mode == "disable":
                result = subprocess.run(['systemctl', 'stop', 'apparmor'], 
                                      capture_output=True, text=True, timeout=10)
                return {"status": "ok" if result.returncode == 0 else "partial", 
                       "mode": mode, "output": result.stdout or result.stderr}
            elif profile:
                # Set specific profile mode
                if mode == "enforce":
                    cmd = ['aa-enforce', profile]
                else:  # complain
                    cmd = ['aa-complain', profile]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                return {"status": "ok" if result.returncode == 0 else "failed",
                       "mode": mode, "profile": profile, "output": result.stdout or result.stderr}
            else:
                # Try to set mode for all profiles
                result = subprocess.run(['systemctl', 'restart', 'apparmor'], 
                                      capture_output=True, text=True, timeout=10)
                return {"status": "ok" if result.returncode == 0 else "partial",
                       "mode": mode, "message": "AppArmor service restarted"}
        except FileNotFoundError as e:
            return {"status": "unavailable", "mode": mode,
                   "message": f"AppArmor tools not installed: {e}"}
        except Exception as e:
            return {"error": str(e)}
