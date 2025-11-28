#!/usr/bin/env python3
"""
System Tuners - Apply OS-level tuning (priority, governor, sysctl, etc.)
"""

import os
import subprocess
from typing import Dict, Any, Optional


class SystemTuner:
    def set_process_priority(self, pid: int, nice: int) -> Dict[str, Any]:
        """
        Set process nice level (-20 to 19).
        Requires appropriate permissions.
        """
        try:
            os.setpriority(os.PRIO_PROCESS, pid, nice)
            return {"status": "ok", "pid": pid, "nice": nice}
        except PermissionError:
            return {"status": "error", "message": "Permission denied"}
        except ProcessLookupError:
            return {"status": "error", "message": "Process not found"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def set_cpu_governor(self, governor: str) -> Dict[str, Any]:
        """
        Set CPU frequency governor (powersave, performance, etc.)
        """
        try:
            # Find all CPUs
            cpu_dirs = [
                d for d in os.listdir("/sys/devices/system/cpu")
                if d.startswith("cpu") and d[3:].isdigit()
            ]
            
            for cpu_dir in cpu_dirs:
                governor_path = f"/sys/devices/system/cpu/{cpu_dir}/cpufreq/scaling_governor"
                if os.path.exists(governor_path):
                    with open(governor_path, 'w') as f:
                        f.write(governor)
            
            return {"status": "ok", "governor": governor}
        except PermissionError:
            return {"status": "error", "message": "Permission denied (requires root)"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def get_sysctl(self, key: str) -> Dict[str, Any]:
        """Read a sysctl value"""
        try:
            result = subprocess.run(
                ["sysctl", "-n", key],
                capture_output=True,
                text=True,
                check=True
            )
            return {"key": key, "value": result.stdout.strip()}
        except subprocess.CalledProcessError as e:
            return {"error": str(e)}
        except FileNotFoundError:
            return {"error": "sysctl command not found"}

    def set_sysctl(self, key: str, value: str) -> Dict[str, Any]:
        """Write a sysctl value (requires root)"""
        try:
            subprocess.run(
                ["sysctl", "-w", f"{key}={value}"],
                capture_output=True,
                text=True,
                check=True
            )
            return {"status": "ok", "key": key, "value": value}
        except subprocess.CalledProcessError as e:
            return {"status": "error", "message": e.stderr}
        except PermissionError:
            return {"status": "error", "message": "Permission denied (requires root)"}
        except FileNotFoundError:
            return {"status": "error", "message": "sysctl command not found"}

    def set_io_scheduler(self, device: str, scheduler: str) -> Dict[str, Any]:
        """
        Set I/O scheduler for a block device (none, mq-deadline, kyber, bfq)
        """
        try:
            scheduler_path = f"/sys/block/{device}/queue/scheduler"
            if not os.path.exists(scheduler_path):
                return {"status": "error", "message": f"Device {device} not found"}
            
            with open(scheduler_path, 'w') as f:
                f.write(scheduler)
            
            return {"status": "ok", "device": device, "scheduler": scheduler}
        except PermissionError:
            return {"status": "error", "message": "Permission denied (requires root)"}
        except Exception as e:
            return {"status": "error", "message": str(e)}
