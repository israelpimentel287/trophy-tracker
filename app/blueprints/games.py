"""Games blueprint for game listing and trophy views."""

from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from datetime import datetime
from app.models import Game, Achievement

games_bp = Blueprint('games', __name__)


@games_bp.route('/games')
@login_required
def games():
    if not current_user.steam_id:
        flash('Please add your Steam ID to view games.', 'warning')
        return redirect(url_for('profile.profile'))
    
    user_games = current_user.games.all()
    games_data = []
    
    for game in user_games:
        all_achievements = game.achievements.filter_by(user_id=current_user.id)
        total_achievements = all_achievements.count()
        unlocked_achievements = all_achievements.filter_by(unlocked=True).count()
        
        completion_rate = (unlocked_achievements / total_achievements * 100) if total_achievements > 0 else 0
        
        trophy_counts = {
            'platinum': all_achievements.filter_by(unlocked=True, rarity_tier='platinum').count(),
            'gold': all_achievements.filter_by(unlocked=True, rarity_tier='gold').count(),
            'silver': all_achievements.filter_by(unlocked=True, rarity_tier='silver').count(),
            'bronze': all_achievements.filter_by(unlocked=True, rarity_tier='bronze').count()
        }
        
        latest_unlock = all_achievements.filter_by(unlocked=True)\
            .filter(Achievement.unlock_time.isnot(None))\
            .order_by(Achievement.unlock_time.desc()).first()
        
        playtime_hours = 0
        if hasattr(game, 'playtime_forever') and game.playtime_forever:
            playtime_hours = round(game.playtime_forever / 60, 1) if game.playtime_forever >= 60 else game.playtime_forever
        
        games_data.append({
            'game': game,
            'completion_rate': round(completion_rate, 1),
            'trophy_counts': trophy_counts,
            'total_unlocked': unlocked_achievements,
            'total_available': total_achievements,
            'latest_unlock': latest_unlock,
            'playtime_hours': playtime_hours,
            'has_achievements': total_achievements > 0
        })
    
    show_all = request.args.get('show_all', 'false').lower() == 'true'
    if not show_all:
        games_data = [g for g in games_data if g['has_achievements']]
    
    sort_by = request.args.get('sort', 'recent')
    
    if sort_by == 'completion':
        games_data.sort(key=lambda x: x['completion_rate'], reverse=True)
    elif sort_by == 'name':
        games_data.sort(key=lambda x: x['game'].name.lower())
    elif sort_by == 'playtime':
        games_data.sort(key=lambda x: x['game'].playtime_forever or 0, reverse=True)
    else:
        games_data.sort(key=lambda x: x['game'].last_played or datetime.min, reverse=True)
    
    total_games = len(games_data)
    completed_games = len([g for g in games_data if g['completion_rate'] == 100])
    total_trophies = sum(sum(g['trophy_counts'].values()) for g in games_data)
    avg_completion = sum(g['completion_rate'] for g in games_data) / total_games if total_games > 0 else 0
    
    summary_stats = {
        'total_games': total_games,
        'completed_games': completed_games,
        'total_trophies': total_trophies,
        'avg_completion': round(avg_completion, 1)
    }
    
    return render_template('games.html', 
                         title='My Games',
                         games_data=games_data,
                         summary_stats=summary_stats,
                         sort_by=sort_by,
                         show_all=show_all)


@games_bp.route('/games/<int:game_id>/trophies')
@login_required
def game_trophies(game_id):
    game = Game.query.filter_by(id=game_id, user_id=current_user.id).first_or_404()
    
    achievements = game.achievements.filter_by(user_id=current_user.id)\
        .order_by(Achievement.unlocked.desc(), Achievement.name).all()
    
    total_count = len(achievements)
    unlocked_count = sum(1 for a in achievements if a.unlocked)
    completion_rate = (unlocked_count / total_count * 100) if total_count > 0 else 0
    
    trophy_counts = {
        'platinum': sum(1 for a in achievements if a.unlocked and a.rarity_tier == 'platinum'),
        'gold': sum(1 for a in achievements if a.unlocked and a.rarity_tier == 'gold'),
        'silver': sum(1 for a in achievements if a.unlocked and a.rarity_tier == 'silver'),
        'bronze': sum(1 for a in achievements if a.unlocked and a.rarity_tier == 'bronze')
    }
    
    return render_template('game_trophies.html',
                         title=f'{game.name} - Trophies',
                         game=game,
                         achievements=achievements,
                         total_count=total_count,
                         unlocked_count=unlocked_count,
                         completion_rate=completion_rate,
                         trophy_counts=trophy_counts)