"""Trophies blueprint for trophy viewing."""

from flask import Blueprint, render_template
from flask_login import login_required, current_user
from app.models import Achievement

trophies_bp = Blueprint('trophies', __name__)


@trophies_bp.route('/trophies')
@login_required
def trophies():
    trophy_counts = current_user.get_trophy_counts()
    
    recent_achievements = current_user.achievements.filter_by(unlocked=True)\
        .filter(Achievement.unlock_time.isnot(None))\
        .order_by(Achievement.unlock_time.desc())\
        .limit(10).all()
    
    return render_template('trophies.html', 
                     title='My Trophies', 
                     trophy_counts=trophy_counts,
                     trophy_level=current_user.get_trophy_level(),
                     recent_achievements=recent_achievements)