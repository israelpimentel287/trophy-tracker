"""Profile blueprint for user settings."""

from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app import db
from app.routes import extract_steam_id, get_steam_profile_url

profile_bp = Blueprint('profile', __name__)


@profile_bp.route('/profile')
@login_required
def profile():
    return render_template('profile.html', title='Profile', user=current_user)


@profile_bp.route('/update-steam-id', methods=['POST'])
@login_required
def update_steam_id():
    steam_input = request.form.get('steam_id', '').strip()
    
    if not steam_input:
        flash('Please enter a Steam ID')
        return redirect(url_for('profile.profile'))
    
    steam_id = extract_steam_id(steam_input)
    if not steam_id:
        flash('Invalid Steam ID format. Please use your numeric Steam ID, profile URL, or custom username.')
        return redirect(url_for('profile.profile'))
    
    from app.models import User
    existing_user = User.query.filter_by(steam_id=steam_id).first()
    if existing_user and existing_user.id != current_user.id:
        flash('This Steam ID is already registered to another account')
        return redirect(url_for('profile.profile'))
    
    current_user.steam_id = steam_id
    current_user.steam_profile_url = get_steam_profile_url(steam_id)
    
    try:
        db.session.commit()
        flash(f'Steam ID updated: {steam_id}')
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating Steam ID: {str(e)}')
    
    return redirect(url_for('profile.profile'))