"""Sync API blueprint for Steam synchronization."""

from flask import Blueprint, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user
from celery.result import AsyncResult
from app import celery
from app.tasks import full_steam_sync, quick_steam_sync, sync_specific_games
from app.task_utils import TaskManager, get_task_summary

sync_api_bp = Blueprint('sync_api', __name__)


@sync_api_bp.route('/sync-steam')
@login_required
def sync_steam():
    if not current_user.steam_id:
        flash('Please set your Steam ID first in your profile')
        return redirect(url_for('profile.profile'))
    
    try:
        task = full_steam_sync.delay(current_user.id)
        flash(f'Full Steam sync started! Task ID: {task.id}')
        return redirect(url_for('sync_api.sync_status', task_id=task.id))
        
    except ImportError as e:
        flash(f'Error importing sync task: {str(e)}')
        return redirect(url_for('trophies.trophies'))
    except Exception as e:
        flash(f'Error starting Steam sync: {str(e)}')
        return redirect(url_for('trophies.trophies'))


@sync_api_bp.route('/sync-steam-quick')
@login_required
def sync_steam_quick():
    if not current_user.steam_id:
        flash('Please set your Steam ID first in your profile')
        return redirect(url_for('profile.profile'))
    
    try:
        task = quick_steam_sync.delay(current_user.id, max_games=20)
        flash(f'Quick Steam sync started! Task ID: {task.id}')
        return redirect(url_for('sync_api.sync_status', task_id=task.id))
        
    except ImportError as e:
        flash(f'Error importing sync task: {str(e)}')
        return redirect(url_for('trophies.trophies'))
    except Exception as e:
        flash(f'Error starting quick sync: {str(e)}')
        return redirect(url_for('trophies.trophies'))


@sync_api_bp.route('/sync-status/<task_id>')
@login_required
def sync_status(task_id):
    from flask import render_template
    return render_template('sync_status.html', task_id=task_id, title='Sync Status')


@sync_api_bp.route('/task-status/<task_id>')
@login_required
def task_status(task_id):
    try:
        task = AsyncResult(task_id, app=celery)
        
        response = {
            'task_id': task_id,
            'state': task.state,
            'ready': task.ready(),
            'successful': task.successful() if task.ready() else False,
            'failed': task.failed() if task.ready() else False,
        }
        
        if task.state == 'PENDING':
            response.update({
                'status': 'Task is waiting to start...',
                'percentage': 0,
                'current': 0,
                'total': 1,
                'games_synced': 0,
                'games_skipped': 0,
                'failed_games': 0,
                'phase': 'pending'
            })
        
        elif task.state == 'PROGRESS':
            if isinstance(task.info, dict):
                response.update({
                    'status': task.info.get('status', 'Processing...'),
                    'percentage': task.info.get('percent', 0),
                    'current': task.info.get('current_index', 0),
                    'total': task.info.get('total_games', 1),
                    'current_game': task.info.get('current_game'),
                    'games_synced': task.info.get('games_synced', 0),
                    'games_skipped': task.info.get('games_skipped', 0),
                    'failed_games': task.info.get('games_failed', 0),
                    'phase': task.info.get('phase', 'progress'),
                    'sync_type': task.info.get('sync_type'),
                    'start_time': task.info.get('start_time'),
                    'duration_seconds': task.info.get('duration_seconds', 0),
                    'avg_games_per_second': task.info.get('avg_games_per_second', 0)
                })
            else:
                response.update({
                    'status': 'Processing...',
                    'percentage': 50,
                    'phase': 'progress'
                })
        
        elif task.state == 'SUCCESS':
            result = task.result
            if isinstance(result, dict):
                response.update({
                    'status': result.get('message', 'Completed'),
                    'percentage': 100,
                    'result': result,
                    'games_synced': result.get('games_synced', 0),
                    'games_skipped': result.get('games_skipped', 0),
                    'failed_games': result.get('failed_games', []),
                    'total': result.get('total', 0),
                    'sync_type': result.get('sync_type'),
                    'phase': 'completed'
                })
            else:
                response.update({
                    'status': 'Task completed',
                    'percentage': 100,
                    'result': result,
                    'phase': 'completed'
                })
        
        elif task.state == 'FAILURE':
            response.update({
                'status': f'Task failed: {str(task.info)}',
                'percentage': 0,
                'error': str(task.info),
                'traceback': task.traceback,
                'phase': 'failed'
            })
        
        else:
            response.update({
                'status': f'Task state: {task.state}',
                'info': str(task.info) if task.info else None
            })
        
        return jsonify(response)
            
    except Exception as e:
        print(f"Error checking task status: {e}")
        return jsonify({
            'state': 'ERROR',
            'status': 'Error retrieving task status',
            'error': str(e)
        }), 500


@sync_api_bp.route('/task-summary/<task_id>')
@login_required
def task_summary(task_id):
    summary = get_task_summary(task_id)
    return jsonify(summary)


@sync_api_bp.route('/cancel-sync/<task_id>', methods=['POST'])
@login_required
def cancel_sync(task_id):
    try:
        result = TaskManager.cancel_task(task_id, terminate=True)
        return jsonify(result)
    except ImportError as e:
        return jsonify({'message': f'TaskManager import error: {str(e)}'})
    except Exception as e:
        return jsonify({'message': f'Error cancelling task: {str(e)}'})


@sync_api_bp.route('/active-tasks')
@login_required
def active_tasks():
    try:
        tasks = TaskManager.get_user_active_tasks(current_user.id)
        return jsonify({'tasks': tasks})
    except ImportError as e:
        print(f"TaskManager import error: {e}")
        return jsonify({'error': 'Service temporarily unavailable', 'tasks': []})
    except Exception as e:
        print(f"Error getting active tasks: {e}")
        return jsonify({'error': 'Service temporarily unavailable', 'tasks': []})


@sync_api_bp.route('/games/search')
@login_required
def search_games():
    from flask import request
    from app.models import Game, Achievement
    
    query = request.args.get('q', '').strip().lower()
    sort_by = request.args.get('sort', 'recent')
    min_completion = request.args.get('min_completion', type=int)
    max_completion = request.args.get('max_completion', type=int)
    has_trophies = request.args.get('has_trophies', 'true').lower() == 'true'
    
    user_games = current_user.games
    
    if has_trophies:
        user_games = user_games.filter(Game.total_achievements > 0)
    
    games = user_games.all()
    results = []
    
    for game in games:
        total_achievements = game.achievements.filter_by(user_id=current_user.id).count()
        unlocked_achievements = game.achievements.filter_by(user_id=current_user.id, unlocked=True).count()
        completion_rate = (unlocked_achievements / total_achievements * 100) if total_achievements > 0 else 0
        
        if query and query not in game.name.lower():
            continue
            
        if min_completion is not None and completion_rate < min_completion:
            continue
            
        if max_completion is not None and completion_rate > max_completion:
            continue
        
        trophy_counts = {
            'platinum': game.achievements.filter_by(user_id=current_user.id, unlocked=True, rarity_tier='platinum').count(),
            'gold': game.achievements.filter_by(user_id=current_user.id, unlocked=True, rarity_tier='gold').count(), 
            'silver': game.achievements.filter_by(user_id=current_user.id, unlocked=True, rarity_tier='silver').count(),
            'bronze': game.achievements.filter_by(user_id=current_user.id, unlocked=True, rarity_tier='bronze').count()
        }
        
        results.append({
            'id': game.id,
            'name': game.name,
            'steam_app_id': game.steam_app_id,
            'completion_rate': round(completion_rate, 1),
            'trophy_counts': trophy_counts,
            'total_unlocked': unlocked_achievements,
            'total_available': total_achievements,
            'playtime_forever': game.playtime_forever or 0,
            'last_played': game.last_played.isoformat() if game.last_played else None
        })
    
    if sort_by == 'completion':
        results.sort(key=lambda x: x['completion_rate'], reverse=True)
    elif sort_by == 'name':
        results.sort(key=lambda x: x['name'].lower())
    elif sort_by == 'playtime':
        results.sort(key=lambda x: x['playtime_forever'], reverse=True)
    else:
        results.sort(key=lambda x: x['last_played'] or '', reverse=True)
    
    return jsonify({'games': results, 'count': len(results)})