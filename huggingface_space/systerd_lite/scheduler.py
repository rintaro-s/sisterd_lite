#!/usr/bin/env python3
"""
Scheduling and reminder management for systerd.
Provides task scheduling, reminders, and cron-like functionality.
"""

import asyncio
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, asdict
from enum import Enum


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class RepeatType(str, Enum):
    ONCE = "once"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    CUSTOM = "custom"  # Custom interval in seconds


@dataclass
class Task:
    id: str
    name: str
    description: str
    command: str
    scheduled_time: float  # Unix timestamp
    status: TaskStatus = TaskStatus.PENDING
    repeat: RepeatType = RepeatType.ONCE
    repeat_interval: int = 0  # For custom repeats (seconds)
    created_at: float = 0
    last_run: Optional[float] = None
    next_run: Optional[float] = None
    run_count: int = 0
    max_runs: Optional[int] = None
    enabled: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Task':
        return cls(**data)


class Scheduler:
    """Task scheduler with reminder and cron-like functionality"""
    
    def __init__(self, state_dir: Path):
        self.state_dir = state_dir
        self.tasks_file = state_dir / 'scheduled_tasks.json'
        self.tasks: Dict[str, Task] = {}
        self.running = False
        self._load_tasks()
    
    def _load_tasks(self):
        """Load tasks from disk"""
        if self.tasks_file.exists():
            try:
                with open(self.tasks_file, 'r') as f:
                    data = json.load(f)
                    self.tasks = {
                        task_id: Task.from_dict(task_data)
                        for task_id, task_data in data.items()
                    }
            except Exception as e:
                print(f"Error loading tasks: {e}")
    
    def _save_tasks(self):
        """Save tasks to disk"""
        try:
            self.tasks_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.tasks_file, 'w') as f:
                json.dump(
                    {task_id: task.to_dict() for task_id, task in self.tasks.items()},
                    f,
                    indent=2
                )
        except Exception as e:
            print(f"Error saving tasks: {e}")
    
    def create_task(self, name: str, description: str, command: str,
                   scheduled_time: str, repeat: str = "once",
                   repeat_interval: int = 0, max_runs: int = None) -> Dict[str, Any]:
        """
        Create a new scheduled task.
        
        Args:
            scheduled_time: ISO format or relative time (e.g., "+1h", "+30m", "2025-12-01T10:00:00")
            repeat: "once", "daily", "weekly", "monthly", "custom"
            repeat_interval: For custom repeats, interval in seconds
        """
        try:
            # Parse scheduled time
            if scheduled_time.startswith('+'):
                # Relative time (e.g., "+1h", "+30m", "+1d")
                delta = self._parse_relative_time(scheduled_time)
                timestamp = time.time() + delta
            else:
                # Absolute time (ISO format)
                dt = datetime.fromisoformat(scheduled_time)
                timestamp = dt.timestamp()
            
            # Generate task ID
            task_id = f"task_{int(time.time() * 1000)}"
            
            task = Task(
                id=task_id,
                name=name,
                description=description,
                command=command,
                scheduled_time=timestamp,
                repeat=RepeatType(repeat),
                repeat_interval=repeat_interval,
                created_at=time.time(),
                next_run=timestamp,
                max_runs=max_runs
            )
            
            self.tasks[task_id] = task
            self._save_tasks()
            
            return {
                'status': 'ok',
                'task_id': task_id,
                'task': task.to_dict(),
                'scheduled_datetime': datetime.fromtimestamp(timestamp).isoformat()
            }
        
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def _parse_relative_time(self, relative: str) -> float:
        """Parse relative time strings like '+1h', '+30m', '+2d'"""
        relative = relative[1:]  # Remove '+'
        
        units = {
            's': 1,
            'm': 60,
            'h': 3600,
            'd': 86400,
            'w': 604800,
        }
        
        for unit, multiplier in units.items():
            if relative.endswith(unit):
                value = int(relative[:-1])
                return value * multiplier
        
        raise ValueError(f"Invalid relative time format: {relative}")
    
    def list_tasks(self, status: str = None, enabled: bool = None) -> List[Dict[str, Any]]:
        """List all tasks with optional filtering"""
        tasks = []
        
        for task in self.tasks.values():
            if status and task.status != status:
                continue
            if enabled is not None and task.enabled != enabled:
                continue
            
            task_dict = task.to_dict()
            
            # Add human-readable times
            task_dict['scheduled_datetime'] = datetime.fromtimestamp(task.scheduled_time).isoformat()
            if task.next_run:
                task_dict['next_run_datetime'] = datetime.fromtimestamp(task.next_run).isoformat()
                task_dict['time_until_next_run'] = self._format_duration(task.next_run - time.time())
            
            tasks.append(task_dict)
        
        return sorted(tasks, key=lambda x: x.get('next_run', 0))
    
    def _format_duration(self, seconds: float) -> str:
        """Format duration in human-readable format"""
        if seconds < 0:
            return "overdue"
        
        if seconds < 60:
            return f"{int(seconds)}s"
        elif seconds < 3600:
            return f"{int(seconds / 60)}m"
        elif seconds < 86400:
            return f"{int(seconds / 3600)}h {int((seconds % 3600) / 60)}m"
        else:
            return f"{int(seconds / 86400)}d {int((seconds % 86400) / 3600)}h"
    
    def get_task(self, task_id: str) -> Dict[str, Any]:
        """Get task details"""
        if task_id not in self.tasks:
            return {'status': 'error', 'error': 'Task not found'}
        
        task = self.tasks[task_id]
        task_dict = task.to_dict()
        task_dict['scheduled_datetime'] = datetime.fromtimestamp(task.scheduled_time).isoformat()
        if task.next_run:
            task_dict['next_run_datetime'] = datetime.fromtimestamp(task.next_run).isoformat()
        
        return {'status': 'ok', 'task': task_dict}
    
    def update_task(self, task_id: str, **updates) -> Dict[str, Any]:
        """Update task properties"""
        if task_id not in self.tasks:
            return {'status': 'error', 'error': 'Task not found'}
        
        task = self.tasks[task_id]
        
        for key, value in updates.items():
            if hasattr(task, key):
                setattr(task, key, value)
        
        self._save_tasks()
        
        return {'status': 'ok', 'task': task.to_dict()}
    
    def cancel_task(self, task_id: str) -> Dict[str, Any]:
        """Cancel a scheduled task"""
        if task_id not in self.tasks:
            return {'status': 'error', 'error': 'Task not found'}
        
        task = self.tasks[task_id]
        task.status = TaskStatus.CANCELLED
        task.enabled = False
        self._save_tasks()
        
        return {'status': 'ok', 'message': f'Task {task_id} cancelled'}
    
    def delete_task(self, task_id: str) -> Dict[str, Any]:
        """Delete a task"""
        if task_id not in self.tasks:
            return {'status': 'error', 'error': 'Task not found'}
        
        del self.tasks[task_id]
        self._save_tasks()
        
        return {'status': 'ok', 'message': f'Task {task_id} deleted'}
    
    async def run_scheduler(self, executor_callback):
        """
        Run the scheduler loop.
        Checks for due tasks every 10 seconds.
        
        Args:
            executor_callback: Async function to execute tasks
        """
        self.running = True
        
        while self.running:
            try:
                current_time = time.time()
                
                for task in list(self.tasks.values()):
                    if not task.enabled or task.status == TaskStatus.CANCELLED:
                        continue
                    
                    if task.next_run and current_time >= task.next_run:
                        # Execute task
                        await self._execute_task(task, executor_callback)
                
                # Sleep for 10 seconds
                await asyncio.sleep(10)
            
            except Exception as e:
                print(f"Scheduler error: {e}")
                await asyncio.sleep(10)
    
    async def _execute_task(self, task: Task, executor_callback):
        """Execute a single task"""
        try:
            task.status = TaskStatus.RUNNING
            task.last_run = time.time()
            self._save_tasks()
            
            # Execute via callback
            result = await executor_callback(task.command)
            
            task.run_count += 1
            task.status = TaskStatus.COMPLETED
            
            # Schedule next run if repeating
            if task.repeat != RepeatType.ONCE:
                if task.max_runs and task.run_count >= task.max_runs:
                    task.enabled = False
                    task.status = TaskStatus.COMPLETED
                else:
                    task.next_run = self._calculate_next_run(task)
            else:
                task.enabled = False
            
            self._save_tasks()
        
        except Exception as e:
            task.status = TaskStatus.FAILED
            self._save_tasks()
            print(f"Task {task.id} execution failed: {e}")
    
    def _calculate_next_run(self, task: Task) -> float:
        """Calculate next run time for repeating tasks"""
        current = task.next_run or time.time()
        
        if task.repeat == RepeatType.DAILY:
            return current + 86400
        elif task.repeat == RepeatType.WEEKLY:
            return current + 604800
        elif task.repeat == RepeatType.MONTHLY:
            # Approximate month as 30 days
            return current + (86400 * 30)
        elif task.repeat == RepeatType.CUSTOM:
            return current + task.repeat_interval
        else:
            return current
    
    def stop_scheduler(self):
        """Stop the scheduler loop"""
        self.running = False
    
    def create_reminder(self, message: str, remind_at: str) -> Dict[str, Any]:
        """
        Create a simple reminder (convenience wrapper for create_task).
        
        Args:
            message: Reminder message
            remind_at: ISO format or relative time
        """
        return self.create_task(
            name=f"Reminder: {message[:30]}",
            description=message,
            command=f"echo 'REMINDER: {message}'",
            scheduled_time=remind_at,
            repeat="once"
        )
    
    def get_upcoming(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get upcoming tasks within next period"""
        upcoming = []
        current_time = time.time()
        
        for task in self.tasks.values():
            if task.enabled and task.next_run and task.next_run > current_time:
                task_dict = task.to_dict()
                task_dict['next_run_datetime'] = datetime.fromtimestamp(task.next_run).isoformat()
                task_dict['time_until'] = self._format_duration(task.next_run - current_time)
                upcoming.append(task_dict)
        
        upcoming.sort(key=lambda x: x['next_run'])
        return upcoming[:limit]
