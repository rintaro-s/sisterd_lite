#!/usr/bin/env python3
"""
System Sensors - Collect comprehensive OS metrics for MCP.
"""

import os
import time
from typing import Dict, Any, List
import json

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False


class SystemSensors:
    def __init__(self):
        self.boot_time = time.time() - (psutil.boot_time() if PSUTIL_AVAILABLE else 0)

    def get_cpu_metrics(self) -> Dict[str, Any]:
        if not PSUTIL_AVAILABLE:
            return {"error": "psutil not available"}
        
        return {
            "percent": psutil.cpu_percent(interval=0.1, percpu=False),
            "percent_per_cpu": psutil.cpu_percent(interval=0.1, percpu=True),
            "count_logical": psutil.cpu_count(logical=True),
            "count_physical": psutil.cpu_count(logical=False),
            "freq": psutil.cpu_freq()._asdict() if psutil.cpu_freq() else None,
            "load_avg": os.getloadavg(),
        }

    def get_memory_metrics(self) -> Dict[str, Any]:
        if not PSUTIL_AVAILABLE:
            return {"error": "psutil not available"}
        
        vm = psutil.virtual_memory()
        swap = psutil.swap_memory()
        
        return {
            "virtual": vm._asdict(),
            "swap": swap._asdict(),
        }

    def get_disk_metrics(self) -> Dict[str, Any]:
        if not PSUTIL_AVAILABLE:
            return {"error": "psutil not available"}
        
        partitions = []
        for part in psutil.disk_partitions(all=False):
            try:
                usage = psutil.disk_usage(part.mountpoint)
                partitions.append({
                    "device": part.device,
                    "mountpoint": part.mountpoint,
                    "fstype": part.fstype,
                    "usage": usage._asdict(),
                })
            except (PermissionError, OSError):
                pass
        
        io = psutil.disk_io_counters(perdisk=False)
        
        return {
            "partitions": partitions,
            "io": io._asdict() if io else None,
        }

    def get_network_metrics(self) -> Dict[str, Any]:
        if not PSUTIL_AVAILABLE:
            return {"error": "psutil not available"}
        
        io = psutil.net_io_counters(pernic=False)
        connections = len(psutil.net_connections())
        
        return {
            "io": io._asdict() if io else None,
            "connections_count": connections,
        }

    def get_sensors(self) -> Dict[str, Any]:
        """Get hardware sensors (temp, battery, etc.)"""
        if not PSUTIL_AVAILABLE:
            return {"error": "psutil not available"}
        
        result = {}
        
        # Temperature sensors
        if hasattr(psutil, "sensors_temperatures"):
            try:
                temps = psutil.sensors_temperatures()
                result["temperatures"] = {
                    name: [t._asdict() for t in sensors]
                    for name, sensors in temps.items()
                }
            except Exception:
                pass
        
        # Battery
        if hasattr(psutil, "sensors_battery"):
            try:
                battery = psutil.sensors_battery()
                if battery:
                    result["battery"] = battery._asdict()
            except Exception:
                pass
        
        return result

    def get_all(self) -> Dict[str, Any]:
        return {
            "cpu": self.get_cpu_metrics(),
            "memory": self.get_memory_metrics(),
            "disk": self.get_disk_metrics(),
            "network": self.get_network_metrics(),
            "sensors": self.get_sensors(),
            "timestamp": time.time(),
        }
