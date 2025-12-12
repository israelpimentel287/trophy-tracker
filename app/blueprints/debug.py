"""Debug blueprint for development testing."""

from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from datetime import datetime
from app import db
from flask import current_app as app
from app.models import User, Game, Achievement

debug_bp = Blueprint('debug', __name__)


@debug_bp.route('/user-data')
@login_required
def debug_user_data():
    games_count = current_user.games.count()
    achievements_count = current_user.achievements.count()
    unlocked_achievements = current_user.achievements.filter_by(unlocked=True).count()
    
    return jsonify({
        'user': {
            'id': current_user.id,
            'username': current_user.username,
            'steam_id': current_user.steam_id,
            'steam_profile_url': current_user.steam_profile_url,
            'last_sync': current_user.last_sync.isoformat() if current_user.last_sync else None
        },
        'stats': {
            'games_count': games_count,
            'total_achievements': achievements_count,
            'unlocked_achievements': unlocked_achievements
        },
        'games': [
            {
                'name': game.name,
                'steam_app_id': game.steam_app_id,
                'total_achievements': game.total_achievements,
                'unlocked_achievements': game.unlocked_achievements,
                'completion_percentage': game.completion_percentage
            }
            for game in current_user.games.limit(10).all()
        ],
        'recent_achievements': [
            {
                'name': ach.name,
                'unlocked': ach.unlocked,
                'rarity_tier': ach.rarity_tier,
                'global_percentage': ach.global_percentage,
                'unlock_time': ach.unlock_time.isoformat() if ach.unlock_time else None,
                'game_name': ach.game.name if ach.game else 'Unknown'
            }
            for ach in current_user.achievements.filter_by(unlocked=True)
                .filter(Achievement.unlock_time.isnot(None))
                .order_by(Achievement.unlock_time.desc())
                .limit(20).all()
        ]
    })


@debug_bp.route('/steam-raw/<steam_id>/<int:app_id>')
def debug_steam_raw(steam_id, app_id):
    try:
        from app.steam_api import steam_api
        
        schema = steam_api.get_game_schema(app_id)
        user_achievements = steam_api.get_user_achievements(steam_id, app_id)
        global_percentages = steam_api.get_achievement_percentages(app_id)
        
        return jsonify({
            'app_id': app_id,
            'schema_count': len(schema),
            'schema_sample': schema[:3] if schema else [],
            'user_achievements_count': len(user_achievements),
            'user_achievements_sample': user_achievements[:3] if user_achievements else [],
            'global_percentages_count': len(global_percentages),
            'global_percentages_sample': dict(list(global_percentages.items())[:3]) if global_percentages else {}
        })
    except Exception as e:
        return jsonify({
            'error': str(e),
            'app_id': app_id
        })


@debug_bp.route('/sync-single-game/<int:app_id>')
@login_required
def debug_sync_single_game(app_id):
    if not current_user.steam_id:
        return jsonify({'error': 'No Steam ID set'})
    
    try:
        from app.tasks import sync_specific_games
        
        task = sync_specific_games.delay(current_user.id, [app_id])
        
        return jsonify({
            'task_id': task.id,
            'status': 'started',
            'message': f'Single game sync started for app {app_id}'
        })
            
    except Exception as e:
        return jsonify({'error': str(e)})


@debug_bp.route('/sync-test')
@login_required
def debug_sync_test():
    if not current_user.steam_id:
        return jsonify({
            'error': 'No Steam ID configured',
            'redirect': '/profile'
        })
    
    try:
        from app import celery
        from app.steam_api import steam_api
        
        api_test = app.config.get('STEAM_API_KEY')
        if not api_test or api_test == 'your-steam-api-key':
            return jsonify({
                'error': 'Steam API key not configured properly',
                'step': 'api_key_check'
            })
        
        games = steam_api.get_user_games(current_user.steam_id)
        
        if not games:
            return jsonify({
                'error': 'Could not fetch games from Steam API',
                'step': 'games_fetch',
                'steam_id': current_user.steam_id
            })
        
        try:
            inspect = celery.control.inspect()
            workers = inspect.active()
            
            if not workers:
                return jsonify({
                    'error': 'No Celery workers active',
                    'step': 'celery_workers',
                    'message': 'Start worker with: python celery_worker.py'
                })
        except Exception as e:
            return jsonify({
                'error': f'Celery connection failed: {str(e)}',
                'step': 'celery_connection'
            })
        
        try:
            from app.tasks import health_check, quick_steam_sync, full_steam_sync
            
            return jsonify({
                'steam_id': current_user.steam_id,
                'games_count': len(games),
                'sample_games': games[:3],
                'celery_workers': list(workers.keys()) if workers else [],
                'available_tasks': ['health_check', 'quick_steam_sync', 'full_steam_sync'],
                'message': 'All checks passed'
            })
            
        except ImportError as e:
            return jsonify({
                'error': f'Task import failed: {str(e)}',
                'step': 'task_import'
            })
            
    except Exception as e:
        return jsonify({
            'error': f'Debug test failed: {str(e)}',
            'step': 'general_error'
        })


@debug_bp.route('/force-sync')
@login_required
def debug_force_sync():
    if not current_user.steam_id:
        return jsonify({'error': 'No Steam ID configured'})
    
    try:
        from app.tasks import quick_steam_sync
        
        task = quick_steam_sync.delay(current_user.id, max_games=5)
        
        return jsonify({
            'task_id': task.id,
            'message': 'Debug sync started with 5 games limit',
            'status_url': f'/api/task-status/{task.id}',
            'user_id': current_user.id,
            'steam_id': current_user.steam_id
        })
        
    except ImportError as e:
        return jsonify({'error': f'Could not import sync task: {str(e)}'})
    except Exception as e:
        return jsonify({'error': f'Force sync failed: {str(e)}'})


@debug_bp.route('/auth-status')
def debug_auth_status():
    from flask_login import current_user
    from flask import session
    
    return jsonify({
        'flask_login_status': {
            'is_authenticated': current_user.is_authenticated,
            'is_anonymous': current_user.is_anonymous,
            'user_id': getattr(current_user, 'id', 'No ID'),
            'username': getattr(current_user, 'username', 'No username'),
            'user_type': type(current_user).__name__
        },
        'session_info': {
            'session_keys': list(session.keys()),
            'user_id_in_session': session.get('_user_id', 'Not found'),
            'session_permanent': session.permanent
        },
        'test_queries': {
            'user_count': User.query.count(),
            'current_user_from_db': User.query.get(getattr(current_user, 'id', 0)) is not None if hasattr(current_user, 'id') else False
        }
    })