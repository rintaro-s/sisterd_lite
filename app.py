#!/usr/bin/env python3
"""
systerd-lite Application Launcher

Python equivalent of start-mcp.sh with additional options.

Usage:
    python app.py                    # Start normally
    python app.py --kill             # Kill existing process before starting
    python app.py --port 9000        # Custom port
    python app.py --no-ui            # Headless mode
    python app.py --stop             # Stop running instance
    python app.py --status           # Check status
"""

import argparse
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.resolve()
VENV_DIR = SCRIPT_DIR / ".venv"
VENV_PYTHON = VENV_DIR / "bin" / "python"
PID_FILE = Path("/tmp/systerd-lite.pid")
LOG_FILE = Path("/tmp/systerd-lite.log")

REQUIRED_PACKAGES = [
    "aiohttp",
    "psutil", 
    "gradio",
    "numpy",
    "sympy",
    "requests",
]


def print_color(message: str, color: str = ""):
    """Print colored message."""
    colors = {
        "red": "\033[0;31m",
        "green": "\033[0;32m",
        "yellow": "\033[1;33m",
        "blue": "\033[0;34m",
        "reset": "\033[0m",
    }
    c = colors.get(color, "")
    reset = colors["reset"] if c else ""
    print(f"{c}{message}{reset}")


def get_running_pid() -> int | None:
    """Get PID of running systerd-lite process."""
    if PID_FILE.exists():
        try:
            pid = int(PID_FILE.read_text().strip())
            # Check if process is actually running
            os.kill(pid, 0)
            return pid
        except (ValueError, ProcessLookupError, PermissionError):
            PID_FILE.unlink(missing_ok=True)
    return None


def kill_existing_processes(force: bool = False) -> bool:
    """Kill existing systerd-lite processes."""
    killed = False
    
    # Try graceful shutdown first via PID file
    pid = get_running_pid()
    if pid:
        try:
            print_color(f"Stopping process {pid}...", "yellow")
            os.kill(pid, signal.SIGTERM)
            time.sleep(2)
            killed = True
        except ProcessLookupError:
            pass
    
    # Kill by process name
    try:
        result = subprocess.run(
            ["pgrep", "-f", "systerd-lite.py"],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            pids = result.stdout.strip().split("\n")
            for p in pids:
                if p:
                    try:
                        sig = signal.SIGKILL if force else signal.SIGTERM
                        os.kill(int(p), sig)
                        killed = True
                    except (ValueError, ProcessLookupError):
                        pass
            time.sleep(1)
    except FileNotFoundError:
        pass
    
    PID_FILE.unlink(missing_ok=True)
    return killed


def setup_venv():
    """Setup virtual environment and install dependencies."""
    if not VENV_DIR.exists():
        print_color("Creating virtual environment...", "yellow")
        subprocess.run([sys.executable, "-m", "venv", str(VENV_DIR)], check=True)
    
    # Upgrade pip and install packages
    pip_path = VENV_DIR / "bin" / "pip"
    print_color("Checking dependencies...", "yellow")
    
    subprocess.run(
        [str(pip_path), "install", "-q", "--upgrade", "pip"],
        capture_output=True
    )
    
    subprocess.run(
        [str(pip_path), "install", "-q"] + REQUIRED_PACKAGES,
        capture_output=True
    )


def check_status(port: int) -> dict:
    """Check if server is running and get status."""
    import urllib.request
    import json
    
    pid = get_running_pid()
    
    try:
        with urllib.request.urlopen(f"http://localhost:{port}/health", timeout=2) as resp:
            health = json.loads(resp.read().decode())
            return {
                "running": True,
                "pid": pid,
                "health": health,
            }
    except Exception:
        return {
            "running": False,
            "pid": pid,
        }


def wait_for_startup(port: int, timeout: int = 30) -> bool:
    """Wait for server to start."""
    import urllib.request
    
    for i in range(timeout * 2):
        try:
            with urllib.request.urlopen(f"http://localhost:{port}/health", timeout=1):
                return True
        except Exception:
            time.sleep(0.5)
            print(".", end="", flush=True)
    return False


def get_tool_count(port: int) -> int:
    """Get number of enabled tools."""
    import urllib.request
    import json
    
    try:
        req = urllib.request.Request(
            f"http://localhost:{port}/",
            data=json.dumps({
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/list",
                "params": {}
            }).encode(),
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            return len(data.get("result", {}).get("tools", []))
    except Exception:
        return -1


def start_server(
    port: int = 8089,
    gradio_port: int = 7861,
    no_ui: bool = False,
    debug: bool = False,
    foreground: bool = False,
) -> int:
    """Start the systerd-lite server."""
    
    # Build command
    cmd = [str(VENV_PYTHON), "systerd-lite.py", "--port", str(port)]
    
    if no_ui:
        cmd.append("--no-ui")
    else:
        cmd.extend(["--gradio", str(gradio_port)])
    
    if debug:
        cmd.append("--debug")
    
    # Create state directory
    (SCRIPT_DIR / ".state").mkdir(exist_ok=True)
    
    if foreground:
        # Run in foreground
        print_color(f"Starting server (foreground)...", "green")
        os.chdir(SCRIPT_DIR)
        os.execv(str(VENV_PYTHON), cmd)
    else:
        # Run in background
        print_color("Starting MCP server...", "green")
        
        # Clear old log
        LOG_FILE.write_text("")
        
        with open(LOG_FILE, "a") as log:
            proc = subprocess.Popen(
                cmd,
                cwd=str(SCRIPT_DIR),
                stdout=log,
                stderr=log,
                start_new_session=True,
            )
        
        # Save PID
        PID_FILE.write_text(str(proc.pid))
        
        # Wait for startup
        print("Waiting for server to start", end="", flush=True)
        if wait_for_startup(port):
            print()
            print_color("✓ Server started successfully!", "green")
            print()
            print(f"  PID: {proc.pid}")
            print(f"  HTTP API: http://localhost:{port}")
            if not no_ui:
                print(f"  Gradio UI: http://localhost:{gradio_port}")
            print(f"  Log file: {LOG_FILE}")
            print()
            print("VS Code MCP config (.vscode/mcp.json):")
            print('{')
            print('  "servers": {')
            print('    "systerd": {')
            print('      "type": "http",')
            print(f'      "url": "http://localhost:{port}"')
            print('    }')
            print('  }')
            print('}')
            print()
            
            tool_count = get_tool_count(port)
            if tool_count >= 0:
                print_color(f"Enabled tools: {tool_count}", "green")
            
            return 0
        else:
            print()
            print_color("✗ Server failed to start!", "red")
            print(f"Check logs: tail -f {LOG_FILE}")
            return 1


def main():
    parser = argparse.ArgumentParser(
        description="systerd-lite Application Launcher",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python app.py                    # Start normally
  python app.py --kill             # Kill existing before starting
  python app.py --port 9000        # Custom HTTP port
  python app.py --stop             # Stop running instance
  python app.py --status           # Check status
  python app.py --foreground       # Run in foreground (not background)
        """
    )
    
    parser.add_argument("--port", type=int, default=8089,
                        help="HTTP API port (default: 8089)")
    parser.add_argument("--gradio", type=int, default=7861,
                        help="Gradio UI port (default: 7861)")
    parser.add_argument("--no-ui", action="store_true",
                        help="Disable Gradio UI (headless mode)")
    parser.add_argument("--debug", action="store_true",
                        help="Enable debug logging")
    parser.add_argument("--kill", "-k", action="store_true",
                        help="Kill existing process before starting")
    parser.add_argument("--stop", action="store_true",
                        help="Stop running instance and exit")
    parser.add_argument("--status", action="store_true",
                        help="Check server status and exit")
    parser.add_argument("--foreground", "-f", action="store_true",
                        help="Run in foreground (not background)")
    
    args = parser.parse_args()
    
    print("=========================================")
    print(" systerd-lite MCP Server")
    print("=========================================")
    
    # Status check
    if args.status:
        status = check_status(args.port)
        if status["running"]:
            print_color("✓ Server is running", "green")
            print(f"  PID: {status['pid']}")
            if "health" in status:
                print(f"  Status: {status['health'].get('status', 'unknown')}")
                print(f"  Uptime: {status['health'].get('uptime', 'unknown')}")
        else:
            print_color("✗ Server is not running", "red")
        return 0 if status["running"] else 1
    
    # Stop
    if args.stop:
        if kill_existing_processes():
            print_color("✓ Server stopped", "green")
        else:
            print_color("No running instance found", "yellow")
        return 0
    
    # Kill existing if requested
    if args.kill:
        print_color("Stopping existing instances...", "yellow")
        kill_existing_processes()
        time.sleep(1)
    else:
        # Check if already running
        status = check_status(args.port)
        if status["running"]:
            print_color(f"Server already running (PID: {status['pid']})", "yellow")
            print("Use --kill to restart or --stop to stop")
            return 1
    
    # Setup environment
    setup_venv()
    
    # Start server
    return start_server(
        port=args.port,
        gradio_port=args.gradio,
        no_ui=args.no_ui,
        debug=args.debug,
        foreground=args.foreground,
    )


if __name__ == "__main__":
    sys.exit(main())
