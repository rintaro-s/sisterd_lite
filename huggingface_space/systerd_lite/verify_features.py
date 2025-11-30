
import os
import sys
import time
import json
import shutil
import tempfile
from pathlib import Path
from datetime import datetime

# Add current directory to path
sys.path.append(os.getcwd())

from calculator import Calculator
from scheduler import Scheduler
from systemd_native import SystemdNative

def test_calculator():
    print("\n=== Testing Calculator ===")
    calc = Calculator()
    
    # Test basic calculation
    expr1 = "1 + 1"
    res1 = calc.evaluate(expr1)
    print(f"Calc '{expr1}': {res1}")
    
    # Test math functions
    expr2 = "sin(pi/2)"
    res2 = calc.evaluate(expr2)
    print(f"Calc '{expr2}': {res2}")
    
    return {
        "basic": {"input": expr1, "output": str(res1)},
        "math": {"input": expr2, "output": str(res2)}
    }

def test_scheduler():
    print("\n=== Testing Scheduler ===")
    with tempfile.TemporaryDirectory() as tmpdir:
        state_dir = Path(tmpdir)
        scheduler = Scheduler(state_dir)
        
        # Create task
        print("Creating task...")
        res = scheduler.create_task(
            name="Test Task",
            description="A test task",
            command="echo 'hello'",
            scheduled_time="+1h",
            repeat="once"
        )
        print(f"Create result: {res}")
        
        # List tasks
        tasks = scheduler.list_tasks() # Assuming list_tasks exists
        print(f"Tasks: {len(tasks)}")
        
        return {
            "create_task": res,
            "tasks_count": len(tasks)
        }

def test_systemd():
    print("\n=== Testing SystemdNative ===")
    # Use a temp dir for state to avoid messing with real system
    with tempfile.TemporaryDirectory() as tmpdir:
        sysd = SystemdNative(state_dir=tmpdir)
        
        # List units (this might fail if not running as root or no access to systemd, 
def test_systemd():
    print("\n=== Testing SystemdNative ===")
    # Use a temp dir for state to avoid messing with real system
    with tempfile.TemporaryDirectory() as tmpdir:
        sysd = SystemdNative(state_dir=tmpdir)
        
        # Trigger daemon_reload to populate unit_states
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        res = loop.run_until_complete(sysd.daemon_reload())
        print(f"Reload result: {res}")
        
        units = sysd.unit_states
        print(f"Units found: {len(units)}")
        
        return {
            "units_count": len(units),
            "reload_result": res
        }

if __name__ == "__main__":
    results = {}
    try:
        results["calculator"] = test_calculator()
    except Exception as e:
        print(f"Calculator test failed: {e}")
        results["calculator"] = {"error": str(e)}

    try:
        results["scheduler"] = test_scheduler()
    except Exception as e:
        print(f"Scheduler test failed: {e}")
        results["scheduler"] = {"error": str(e)}
        
    try:
        results["systemd"] = test_systemd()
    except Exception as e:
        print(f"Systemd test failed: {e}")
        results["systemd"] = {"error": str(e)}

    print("\n=== Final Results ===")
    print(json.dumps(results, indent=2))
