"""User statistics calculation tasks."""

import logging
from datetime import datetime, timedelta

from flask import current_app
from app import db, celery, create_app
from app.models import User, Game, Achievement
from app.task_utils import ProgressTracker, TaskResult

logger = logging.getLogger(__name__)


def get_flask_app():
    try:
        return current_app._get_current_object()
    except RuntimeError:
        return create_app()


@celery.task(bind=True)
def calculate_user_stats(self, user_id):
    app = get_flask_app()
    with app.app_context(): 
        try:
            user = User.query.get(user_id)
            if not user:
                raise ValueError(f"User with ID {user_id} not found")
            
            tracker = ProgressTracker(self, 5, "Calculating user statistics...")
            tracker.progress.sync_type = 'user_stats'
            tracker.progress.start_time = datetime.utcnow().isoformat()
            
            self.update_state(
                state='PROGRESS',
                meta={
                    'percent': 20,
                    'phase': 'trophies',
                    'status': 'Calculating trophy counts...',
                    'sync_type': 'user_stats'
                }
            )
            
            trophy_counts = user.get_trophy_counts()
            
            self.update_state(
                state='PROGRESS',
                meta={
                    'percent': 40,
                    'phase': 'completion',
                    'status': 'Calculating completion rates...',
                    'sync_type': 'user_stats'
                }
            )
            
            total_games = user.games.filter(Game.total_achievements > 0).count()
            total_achievements = user.achievements.count()
            unlocked_achievements = user.achievements.filter_by(unlocked=True).count()
            
            completion_rate = (unlocked_achievements / total_achievements * 100) if total_achievements > 0 else 0
            
            self.update_state(
                state='PROGRESS',
                meta={
                    'percent': 60,
                    'phase': 'recent_activity',
                    'status': 'Analyzing recent activity...',
                    'sync_type': 'user_stats'
                }
            )
            
            recent_achievements = user.achievements.filter_by(unlocked=True)\
                .filter(Achievement.unlock_time.isnot(None))\
                .filter(Achievement.unlock_time > datetime.utcnow() - timedelta(days=30))\
                .count()
            
            self.update_state(
                state='PROGRESS',
                meta={
                    'percent': 80,
                    'phase': 'finalizing',
                    'status': 'Finalizing statistics...',
                    'sync_type': 'user_stats'
                }
            )
            
            if user.last_sync and user.created_at:
                days_active = (user.last_sync - user.created_at).days
                achievement_velocity = unlocked_achievements / max(days_active, 1)
            else:
                achievement_velocity = 0
            
            stats = {
                'trophy_counts': trophy_counts,
                'total_games': total_games,
                'total_achievements': total_achievements,
                'unlocked_achievements': unlocked_achievements,
                'completion_rate': round(completion_rate, 2),
                'recent_achievements_30d': recent_achievements,
                'achievement_velocity': round(achievement_velocity, 2),
                'calculation_time': datetime.utcnow().isoformat()
            }
            
            result_obj = TaskResult(
                status='completed',
                message='User statistics calculated',
                stats=stats,
                sync_type='user_stats',
                completion_time=datetime.utcnow().isoformat()
            )
            
            return result_obj.to_dict()
            
        except Exception as e:
            logger.error(f"Error in calculate_user_stats: {e}", exc_info=True)
            
            raise e