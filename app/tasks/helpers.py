"""Helper classes and utilities for Celery tasks."""

import logging
from datetime import datetime

from app.task_utils import ProgressTracker, TaskResult


logger = logging.getLogger(__name__)


class TaskConfig:
    
    RATE_LIMIT_FULL_SYNC = 0.5
    RATE_LIMIT_QUICK_SYNC = 0.3
    RATE_LIMIT_SPECIFIC_GAME = 0.3
    RATE_LIMIT_ACHIEVEMENT_REFRESH = 0.5
    RATE_LIMIT_BATCH_USER = 30
    
    MAX_RETRIES = 3
    RETRY_COUNTDOWN = 60
    QUICK_RETRY_COUNTDOWN = 30
    
    COMMIT_BATCH_SIZE = 10
    ACHIEVEMENT_COMMIT_BATCH = 5
    
    BATCH_SYNC_TIMEOUT = 1200


class SyncTaskHelper:
    
    def __init__(self, task_instance, user_id: int, sync_type: str):
        self.task = task_instance
        self.user_id = user_id
        self.sync_type = sync_type
        self.task_id = task_instance.request.id
        self.tracker = None
    
    def start_sync(self, total_items: int, message: str, data: dict = None):
        self.tracker = ProgressTracker(self.task, total_items, message)
        self.tracker.progress.sync_type = self.sync_type
        self.tracker.progress.start_time = datetime.utcnow().isoformat()
        
        self.task.update_state(
            state='PROGRESS',
            meta={
                'percent': 0,
                'current_game': '',
                'games_synced': 0,
                'games_skipped': 0,
                'games_failed': 0,
                'total_games': total_items,
                'current_index': 0,
                'phase': 'initializing',
                'status': message,
                'sync_type': self.sync_type,
                'start_time': self.tracker.progress.start_time,
                'duration_seconds': 0,
                'avg_games_per_second': 0
            }
        )
        
        return self.tracker
    
    def update_progress(self, game_name: str):
        self.tracker.update_progress(
            status=f'Syncing {game_name}...',
            current_game=game_name,
            increment=True
        )
        
        self.task.update_state(
            state='PROGRESS',
            meta={
                'percent': int(self.tracker.progress.percentage),
                'current_game': game_name,
                'games_synced': self.tracker.progress.games_synced,
                'games_skipped': self.tracker.progress.games_skipped,
                'games_failed': self.tracker.progress.failed_games,
                'total_games': self.tracker.progress.total,
                'current_index': self.tracker.progress.current,  
                'phase': self.tracker.progress.phase,
                'status': f'Syncing {game_name}...',
                'sync_type': self.sync_type,
                'start_time': self.tracker.progress.start_time,
                'duration_seconds': self.tracker.get_duration_seconds(),
                'avg_games_per_second': self.tracker.get_rate()
            }
        )
    
    def complete_sync(self, message: str, **kwargs):
        result_obj = TaskResult(
            status='completed',
            message=message,
            sync_type=self.sync_type,
            completion_time=datetime.utcnow().isoformat(),
            **kwargs
        )
        
        return result_obj.to_dict()