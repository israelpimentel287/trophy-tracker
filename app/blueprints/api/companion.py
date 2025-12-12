"""Companion API blueprint for Electron app."""

from flask import Blueprint, jsonify, request, send_file
from flask_login import current_user
from app import db
from app.models import User, Game, Achievement
from datetime import datetime
import secrets
import os

companion_api_bp = Blueprint('companion_api', __name__)


@companion_api_bp.route('/register', methods=['POST'])
def register_companion():
    try:
        data = request.get_json()
        
        required_fields = ['steam_id', 'machine_id', 'companion_version']
        if not all(field in data for field in required_fields):
            return jsonify({'message': 'Missing required fields: steam_id, machine_id, companion_version'}), 400
        
        user = User.query.filter_by(steam_id=str(data['steam_id'])).first()
        if not user:
            return jsonify({'message': 'User not found. Please register on the web app first.'}), 404
        
        companion_token = secrets.token_hex(32)
        
        user.companion_token = companion_token
        user.companion_machine_id = data['machine_id']
        user.companion_version = data['companion_version']
        user.companion_last_seen = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'message': 'Companion app registered',
            'token': companion_token,
            'user': {
                'id': user.id,
                'username': user.username,
                'steam_id': user.steam_id,
                'preferences': {
                    'notifications_enabled': True,
                    'sound_enabled': True,
                    'trophy_style': 'premium'
                }
            }
        }), 200
        
    except Exception as e:
        db.session.rollback()
        print(f"Error registering companion: {e}")
        return jsonify({'message': 'Internal server error'}), 500


@companion_api_bp.route('/heartbeat', methods=['POST'])
def companion_heartbeat():
    try:
        data = request.get_json()
        token = data.get('token') or request.headers.get('Authorization', '').replace('Bearer ', '')
        
        if not token:
            return jsonify({'message': 'No authentication token provided'}), 401
        
        user = User.query.filter_by(companion_token=token).first()
        if not user:
            return jsonify({'message': 'Invalid token'}), 401
        
        user.companion_last_seen = datetime.utcnow()
        
        if 'status' in data:
            user.companion_status = data['status']
        
        db.session.commit()
        
        return jsonify({
            'preferences': {
                'notifications_enabled': True,
                'sound_enabled': True,
                'trophy_style': 'premium'
            },
            'server_time': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        print(f"Error in companion heartbeat: {e}")
        return jsonify({'message': 'Internal server error'}), 500


@companion_api_bp.route('/games/<steam_id>')
def get_companion_games(steam_id):
    try:
        user = User.query.filter_by(steam_id=steam_id).first()
        if not user:
            return jsonify({'message': 'User not found'}), 404
        
        games = []
        for game in user.games.filter(Game.total_achievements > 0).all():
            achievements_data = []
            
            for achievement in game.achievements.filter_by(user_id=user.id).all():
                achievements_data.append({
                    'id': achievement.steam_achievement_id,
                    'name': achievement.name,
                    'description': achievement.description,
                    'icon_url': achievement.icon_url,
                    'unlocked': achievement.unlocked,
                    'unlock_time': achievement.unlock_time.isoformat() if achievement.unlock_time else None,
                    'global_percentage': achievement.global_percentage,
                    'rarity_tier': achievement.rarity_tier
                })
            
            games.append({
                'app_id': game.steam_app_id,
                'name': game.name,
                'total_achievements': game.total_achievements,
                'unlocked_achievements': game.unlocked_achievements,
                'achievements': achievements_data
            })
        
        return jsonify({'games': games, 'count': len(games)})
        
    except Exception as e:
        print(f"Error getting companion games: {e}")
        return jsonify({'message': 'Internal server error'}), 500


@companion_api_bp.route('/notification-assets/<asset_type>/<filename>')
def get_notification_assets(asset_type, filename):
    try:
        from app import app
        
        asset_dirs = {
            'sounds': 'static/sounds',
            'images': 'static/images/trophies',
            'icons': 'static/images/icons'
        }
        
        if asset_type not in asset_dirs:
            return jsonify({'message': 'Invalid asset type'}), 400
        
        asset_dir = asset_dirs[asset_type]
        file_path = os.path.join(app.root_path, asset_dir, filename)
        
        if not os.path.exists(file_path) or not os.path.commonpath([file_path, os.path.join(app.root_path, asset_dir)]) == os.path.join(app.root_path, asset_dir):
            return jsonify({'message': 'Asset not found'}), 404
        
        return send_file(file_path)
        
    except Exception as e:
        print(f"Error serving notification asset: {e}")
        return jsonify({'message': 'Internal server error'}), 500


@companion_api_bp.route('/sync-trigger', methods=['POST'])
def trigger_companion_sync():
    try:
        from app.tasks import full_steam_sync, quick_steam_sync
        
        data = request.get_json()
        token = data.get('token') or request.headers.get('Authorization', '').replace('Bearer ', '')
        
        if not token:
            return jsonify({'message': 'No authentication token provided'}), 401
        
        user = User.query.filter_by(companion_token=token).first()
        if not user:
            return jsonify({'message': 'Invalid token'}), 401
        
        sync_type = data.get('sync_type', 'quick')
        
        if sync_type == 'full':
            task = full_steam_sync.delay(user.id)
        else:
            task = quick_steam_sync.delay(user.id, max_games=20)
        
        return jsonify({
            'message': f'{sync_type.title()} sync started',
            'task_id': task.id,
            'sync_type': sync_type
        })
        
    except Exception as e:
        print(f"Error triggering companion sync: {e}")
        return jsonify({'message': 'Internal server error'}), 500


@companion_api_bp.route('/achievement-unlock', methods=['POST'])
def companion_achievement_unlock():
    try:
        data = request.get_json()
        token = data.get('token') or request.headers.get('Authorization', '').replace('Bearer ', '')
        
        if token:
            user = User.query.filter_by(companion_token=token).first()
        else:
            steam_id = data.get('steam_id')
            if not steam_id:
                return jsonify({'message': 'No authentication provided'}), 401
            user = User.query.filter_by(steam_id=str(steam_id)).first()
        
        if not user:
            return jsonify({'message': 'User not found'}), 404
        
        required_fields = ['app_id', 'achievement_id']
        if not all(field in data for field in required_fields):
            return jsonify({'message': 'Missing required fields'}), 400
        
        app_id = int(data['app_id'])
        achievement_id = data['achievement_id']
        
        game = Game.query.filter_by(user_id=user.id, steam_app_id=app_id).first()
        if not game:
            game = Game(
                user_id=user.id,
                steam_app_id=app_id,
                name=data.get('game_name', f"Game {app_id}"),
                header_image=f"https://steamcdn-a.akamaihd.net/steam/apps/{app_id}/header.jpg"
            )
            db.session.add(game)
            db.session.flush()
        
        achievement = Achievement.query.filter_by(
            user_id=user.id,
            game_id=game.id,
            steam_achievement_id=achievement_id
        ).first()
        
        if not achievement:
            achievement = Achievement(
                user_id=user.id,
                game_id=game.id,
                steam_achievement_id=achievement_id,
                name=data.get('achievement_name', achievement_id),
                description=data.get('achievement_description', ''),
                icon_url=data.get('achievement_icon', ''),
                unlocked=True,
                unlock_time=datetime.utcnow()
            )
            db.session.add(achievement)
        else:
            if not achievement.unlocked:
                achievement.unlocked = True
                achievement.unlock_time = datetime.utcnow()
        
        if 'global_percentage' in data:
            achievement.global_percentage = float(data['global_percentage'])
            achievement.calculate_rarity_tier()
        
        game.calculate_completion()
        
        db.session.commit()
        
        notification_data = {
            'achievement': {
                'id': achievement.id,
                'steam_id': achievement.steam_achievement_id,
                'name': achievement.name,
                'description': achievement.description,
                'icon_url': achievement.icon_url,
                'rarity_tier': achievement.rarity_tier,
                'global_percentage': achievement.global_percentage,
                'unlock_time': achievement.unlock_time.isoformat()
            },
            'game': {
                'id': game.id,
                'name': game.name,
                'app_id': game.steam_app_id,
                'completion_percentage': game.completion_percentage,
                'header_image': game.header_image
            },
            'notification_preferences': {
                'sound_enabled': True,
                'trophy_style': 'premium'
            }
        }
        
        return jsonify({
            'message': 'Achievement processed',
            'notification_data': notification_data
        }), 200
        
    except Exception as e:
        db.session.rollback()
        print(f"Error processing companion achievement unlock: {e}")
        return jsonify({'message': 'Internal server error'}), 500


@companion_api_bp.route('/config')
def get_companion_config():
    try:
        config = {
            'polling_intervals': {
                'achievement_check': 5000,
                'heartbeat': 30000,
                'preference_sync': 60000
            },
            'notification_settings': {
                'default_display_duration': 5000,
                'fade_duration': 500,
                'position': 'top-right'
            },
            'api_endpoints': {
                'achievement_unlock': '/api/companion/achievement-unlock',
                'heartbeat': '/api/companion/heartbeat',
                'games': '/api/companion/games',
                'settings': '/api/companion/settings'
            },
            'version': '1.0.0',
            'required_steam_running': True
        }
        
        return jsonify({'config': config})
        
    except Exception as e:
        return jsonify({'message': f'Error getting companion config: {str(e)}'}), 500


@companion_api_bp.route('/status', methods=['GET'])
def companion_status():
    return jsonify({
        'status': 'ready',
        'message': 'Flask backend ready to receive companion data',
        'endpoints': {
            'achievement_unlock': '/api/companion/achievement-unlock',
            'status': '/api/companion/status',
            'health': '/api/companion/health'
        },
        'timestamp': datetime.utcnow().isoformat()
    })


@companion_api_bp.route('/health', methods=['GET'])
def companion_health():
    return jsonify({
        'status': 'healthy',
        'flask_version': "2.x",
        'companion_support': True,
        'timestamp': datetime.utcnow().isoformat()
    })