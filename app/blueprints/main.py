"""Main blueprint for dashboard and stats."""

from flask import Blueprint, render_template, jsonify
from flask_login import login_required, current_user
from app.models import Achievement, Game
from sqlalchemy import func
from app import db

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
@main_bp.route('/index')
@login_required
def index():
    try:
        trophy_counts = current_user.get_trophy_counts()
        
        total_trophies = sum(trophy_counts.values())
        total_games = Game.query.filter_by(user_id=current_user.id).count()
        
        games_with_trophies = db.session.query(Achievement.game_id).filter(
            Achievement.user_id == current_user.id,
            Achievement.unlocked == True
        ).distinct().count()
        
        avg_completion = 0
        if total_games > 0:
            game_completions = db.session.query(
                Achievement.game_id,
                func.count(Achievement.id).label('total'),
                func.sum(func.cast(Achievement.unlocked, db.Integer)).label('unlocked')
            ).filter(
                Achievement.user_id == current_user.id
            ).group_by(Achievement.game_id).all()
            
            if game_completions:
                completion_rates = []
                for comp in game_completions:
                    if comp.total > 0:
                        unlocked_count = int(comp.unlocked) if comp.unlocked else 0
                        rate = (unlocked_count / comp.total * 100)
                        completion_rates.append(rate)
                
                avg_completion = sum(completion_rates) / len(completion_rates) if completion_rates else 0
        
        trophy_level = current_user.get_trophy_level()
        
        recent_achievements = Achievement.query.filter_by(
            user_id=current_user.id,
            unlocked=True
        ).order_by(Achievement.unlock_time.desc()).limit(5).all()
        
    except Exception as e:
        print(f"Error loading dashboard: {e}")
        import traceback
        traceback.print_exc()
        
        trophy_counts = {'platinum': 0, 'gold': 0, 'silver': 0, 'bronze': 0}
        total_trophies = 0
        total_games = 0
        games_with_trophies = 0
        avg_completion = 0
        trophy_level = 0
        recent_achievements = []
    
    return render_template(
        'index.html',
        title='Dashboard',
        trophy_counts=trophy_counts,
        total_trophies=total_trophies,
        total_games=total_games,
        games_with_trophies=games_with_trophies,
        avg_completion=round(avg_completion, 1),
        trophy_level=trophy_level,
        recent_achievements=recent_achievements
    )


@main_bp.route('/api/stats')
@login_required
def get_stats():
    try:
        trophy_counts = current_user.get_trophy_counts()
        
        total_trophies = sum(trophy_counts.values())
        total_games = Game.query.filter_by(user_id=current_user.id).count()
        games_with_trophies = db.session.query(Achievement.game_id).filter(
            Achievement.user_id == current_user.id,
            Achievement.unlocked == True
        ).distinct().count()
        
        return jsonify({
            'trophy_counts': trophy_counts,
            'total_trophies': total_trophies,
            'total_games': total_games,
            'games_with_trophies': games_with_trophies
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500