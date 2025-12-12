"""Task utilities for managing Celery tasks and progress tracking."""

import json
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, asdict
from typing import Dict, List, Any, Optional, Union
from celery import current_app
from celery.result import AsyncResult
from celery.states import SUCCESS, FAILURE, PENDING, STARTED, RETRY, REVOKED

from app import celery, db
from app.models import User


class TaskState(Enum):
    PENDING = 'PENDING'
    STARTED = 'STARTED'
    PROGRESS = 'PROGRESS'
    SUCCESS = 'SUCCESS'
    FAILURE = 'FAILURE'
    RETRY = 'RETRY'
    REVOKED = 'REVOKED'


class SyncType(Enum):
    FULL = 'full'
    QUICK = 'quick'
    SPECIFIC = 'specific'
    ACHIEVEMENT_REFRESH = 'achievement_refresh'
    USER_STATS = 'user_stats'
    BATCH = 'batch'


@dataclass
class TaskProgress:
    current: int = 0
    total: int = 1
    status: str = 'Starting...'
    phase: str = 'initialization'
    games_synced: int = 0
    games_skipped: int = 0
    failed_games: int = 0
    start_time: Optional[str] = None
    current_game: Optional[str] = None
    sync_type: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TaskProgress':
        return cls(**data)
    
    @property
    def percentage(self) -> float:
        if self.total == 0:
            return 0.0
        return (self.current / self.total) * 100
    
    @property
    def is_complete(self) -> bool:
        return self.current >= self.total


@dataclass
class TaskResult:
    status: str
    message: str
    games_synced: int = 0
    games_skipped: int = 0
    failed_games: List[Union[int, str]] = None
    total: int = 0
    sync_type: Optional[str] = None
    completion_time: Optional[str] = None
    stats: Optional[Dict[str, Any]] = None
    errors: List[str] = None
    
    def __post_init__(self):
        if self.failed_games is None:
            self.failed_games = []
        if self.errors is None:
            self.errors = []
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TaskResult':
        return cls(**data)


class TaskManager:
    
    @staticmethod
    def get_task_status(task_id: str) -> Dict[str, Any]:
        try:
            task = AsyncResult(task_id, app=celery)
            
            response = {
                'task_id': task_id,
                'state': task.state,
                'ready': task.ready(),
                'successful': task.successful(),
                'failed': task.failed(),
                'date_done': task.date_done.isoformat() if task.date_done else None,
            }
            
            if task.state == PENDING:
                response.update({
                    'current': 0,
                    'total': 1,
                    'percentage': 0.0,
                    'status': 'Task is waiting to be processed...',
                    'phase': 'pending'
                })
                
            elif task.state == STARTED:
                response.update({
                    'current': 0,
                    'total': 1,
                    'percentage': 0.0,
                    'status': 'Task has started...',
                    'phase': 'started'
                })
                
            elif task.state == 'PROGRESS':
                info = task.info
                if isinstance(info, dict):
                    progress = TaskProgress.from_dict(info)
                    response.update({
                        'current': progress.current,
                        'total': progress.total,
                        'percentage': progress.percentage,
                        'status': progress.status,
                        'phase': progress.phase,
                        'games_synced': progress.games_synced,
                        'games_skipped': progress.games_skipped,
                        'failed_games': progress.failed_games,
                        'current_game': progress.current_game,
                        'sync_type': progress.sync_type,
                        'start_time': progress.start_time
                    })
                else:
                    response.update({
                        'current': 1,
                        'total': 1,
                        'percentage': 50.0,
                        'status': 'Processing...',
                        'phase': 'progress'
                    })
                    
            elif task.state == SUCCESS:
                result = task.result
                if isinstance(result, dict):
                    task_result = TaskResult.from_dict(result)
                    response.update({
                        'current': task_result.total,
                        'total': task_result.total,
                        'percentage': 100.0,
                        'status': task_result.message,
                        'phase': 'completed',
                        'result': task_result.to_dict()
                    })
                else:
                    response.update({
                        'current': 1,
                        'total': 1,
                        'percentage': 100.0,
                        'status': 'Task completed',
                        'phase': 'completed',
                        'result': result
                    })
                    
            elif task.state == FAILURE:
                response.update({
                    'current': 1,
                    'total': 1,
                    'percentage': 0.0,
                    'status': f'Task failed: {str(task.info)}',
                    'phase': 'failed',
                    'error': str(task.info),
                    'traceback': task.traceback
                })
                
            elif task.state == RETRY:
                response.update({
                    'current': 0,
                    'total': 1,
                    'percentage': 0.0,
                    'status': 'Task is being retried...',
                    'phase': 'retry',
                    'retry_info': str(task.info) if task.info else None
                })
                
            elif task.state == REVOKED:
                response.update({
                    'current': 0,
                    'total': 1,
                    'percentage': 0.0,
                    'status': 'Task was cancelled',
                    'phase': 'cancelled'
                })
                
            return response
            
        except Exception as e:
            return {
                'task_id': task_id,
                'state': 'ERROR',
                'status': f'Error retrieving task status: {str(e)}',
                'phase': 'error',
                'error': str(e)
            }
    
    @staticmethod
    def cancel_task(task_id: str, terminate: bool = False) -> Dict[str, Any]:
        try:
            celery.control.revoke(task_id, terminate=terminate)
            return {
                'status': 'cancelled',
                'task_id': task_id,
                'terminated': terminate,
                'message': f'Task {task_id} has been cancelled'
            }
        except Exception as e:
            return {
                'status': 'error',
                'task_id': task_id,
                'error': str(e),
                'message': f'Failed to cancel task {task_id}'
            }
    
    @staticmethod
    def get_active_tasks() -> List[Dict[str, Any]]:
        try:
            inspect = celery.control.inspect()
            active_tasks = inspect.active()
            
            if not active_tasks:
                return []
            
            tasks = []
            for worker, task_list in active_tasks.items():
                for task in task_list:
                    tasks.append({
                        'task_id': task['id'],
                        'name': task['name'],
                        'worker': worker,
                        'args': task.get('args', []),
                        'kwargs': task.get('kwargs', {}),
                        'time_start': task.get('time_start')
                    })
            
            return tasks
            
        except Exception as e:
            print(f"Error getting active tasks: {e}")
            return []
    
    @staticmethod
    def get_user_active_tasks(user_id: int) -> List[Dict[str, Any]]:
        active_tasks = TaskManager.get_active_tasks()
        user_tasks = []
        
        for task in active_tasks:
            args = task.get('args', [])
            if args and len(args) > 0 and args[0] == user_id:
                user_tasks.append(task)
        
        return user_tasks
    
    @staticmethod
    def cleanup_completed_tasks(days_old: int = 7) -> Dict[str, Any]:
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_old)
            
            return {
                'status': 'completed',
                'message': f'Cleaned up task results older than {days_old} days',
                'cutoff_date': cutoff_date.isoformat(),
                'cleaned_count': 0
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'message': f'Error cleaning up tasks: {str(e)}',
                'error': str(e)
            }


class ProgressTracker:
    
    def __init__(self, task, total_items: int, initial_status: str = 'Starting...'):
        self.task = task
        self.total_items = total_items
        self.current_item = 0
        self.progress = TaskProgress(
            total=total_items,
            status=initial_status,
            start_time=datetime.utcnow().isoformat()
        )
        self.update_progress()
    
    def update_progress(self, status: str = None, phase: str = None, 
                       current_game: str = None, increment: bool = False):
        if increment:
            self.current_item += 1
        
        if status:
            self.progress.status = status
        if phase:
            self.progress.phase = phase
        if current_game:
            self.progress.current_game = current_game
        
        self.progress.current = self.current_item
        
        self.task.update_state(
            state='PROGRESS',
            meta=self.progress.to_dict()
        )
    
    def increment_synced(self):
        self.progress.games_synced += 1
        self.update_progress()
    
    def increment_skipped(self):
        self.progress.games_skipped += 1
        self.update_progress()
    
    def increment_failed(self):
        self.progress.failed_games += 1
        self.update_progress()
    
    def set_phase(self, phase: str, status: str = None):
        self.update_progress(phase=phase, status=status)
    
    def complete(self, final_status: str = 'Completed'):
        self.progress.current = self.progress.total
        self.progress.status = final_status
        self.progress.phase = 'completed'
        self.update_progress()
    
    def get_duration_seconds(self) -> float:
        if not self.progress.start_time:
            return 0.0
        
        try:
            start = datetime.fromisoformat(self.progress.start_time.replace('Z', '+00:00'))
            now = datetime.utcnow()
            duration = now - start
            return duration.total_seconds()
        except Exception:
            return 0.0
        
    def get_rate(self) -> float:
        duration = self.get_duration_seconds()
        if duration > 0 and self.current_item > 0:
            return self.current_item / duration
        return 0.0


def format_task_duration(start_time: str, end_time: str = None) -> str:
    try:
        start = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
        if end_time:
            end = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
        else:
            end = datetime.utcnow()
        
        duration = end - start
        
        if duration.days > 0:
            return f"{duration.days}d {duration.seconds // 3600}h {(duration.seconds % 3600) // 60}m"
        elif duration.seconds >= 3600:
            return f"{duration.seconds // 3600}h {(duration.seconds % 3600) // 60}m"
        elif duration.seconds >= 60:
            return f"{duration.seconds // 60}m {duration.seconds % 60}s"
        else:
            return f"{duration.seconds}s"
            
    except Exception:
        return "Unknown"


def estimate_time_remaining(current: int, total: int, start_time: str) -> str:
    try:
        if current == 0 or current >= total:
            return "Unknown"
        
        start = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
        elapsed = datetime.utcnow() - start
        
        rate = current / elapsed.total_seconds()
        remaining_items = total - current
        remaining_seconds = remaining_items / rate
        
        if remaining_seconds >= 3600:
            hours = int(remaining_seconds // 3600)
            minutes = int((remaining_seconds % 3600) // 60)
            return f"~{hours}h {minutes}m remaining"
        elif remaining_seconds >= 60:
            minutes = int(remaining_seconds // 60)
            return f"~{minutes}m remaining"
        else:
            return f"~{int(remaining_seconds)}s remaining"
            
    except Exception:
        return "Unknown"


def validate_user_permissions(user_id: int, task_user_id: int) -> bool:
    return user_id == task_user_id


def get_task_summary(task_id: str) -> Dict[str, Any]:
    status = TaskManager.get_task_status(task_id)
    
    summary = {
        'task_id': task_id,
        'state': status.get('state'),
        'status': status.get('status'),
        'percentage': status.get('percentage', 0),
        'phase': status.get('phase'),
        'sync_type': status.get('sync_type'),
    }
    
    if status.get('start_time'):
        summary['duration'] = format_task_duration(status['start_time'])
        if not status.get('ready', False):
            summary['eta'] = estimate_time_remaining(
                status.get('current', 0),
                status.get('total', 1),
                status['start_time']
            )
    
    if status.get('result'):
        result = status['result']
        summary['games_synced'] = result.get('games_synced', 0)
        summary['games_skipped'] = result.get('games_skipped', 0)
        summary['total_games'] = result.get('total', 0)
    
    return summary