"""Authentication blueprint for login and registration."""

from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_user, logout_user, current_user, login_required
from app import db
from app.models import User
from app.routes import extract_steam_id, validate_steam_id, get_steam_profile_url

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        steam_input = request.form.get('steam_id', '').strip()
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists')
            return redirect(url_for('auth.register'))
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered')
            return redirect(url_for('auth.register'))
        
        steam_id = None
        if steam_input:
            steam_id = extract_steam_id(steam_input)
            if not steam_id:
                flash('Invalid Steam ID format. Please use your numeric Steam ID, profile URL, or custom username.')
                return redirect(url_for('auth.register'))
            
            if User.query.filter_by(steam_id=steam_id).first():
                flash('This Steam ID is already registered to another account')
                return redirect(url_for('auth.register'))
        
        user = User(username=username, email=email, steam_id=steam_id)
        user.set_password(password)
        
        if steam_id:
            try:
                profile_url = get_steam_profile_url(steam_id)
                user.steam_profile_url = profile_url
            except Exception as e:
                current_app.logger.error(f"Could not fetch Steam profile info: {e}")
        
        db.session.add(user)
        db.session.commit()
        
        if steam_id:
            flash(f'Registration complete! Steam ID {steam_id} linked to your account.')
        else:
            flash('Registration complete! You can add your Steam ID later in your profile.')
        
        return redirect(url_for('auth.login'))
    
    return render_template('register.html', title='Register')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('main.index'))
        else:
            flash('Invalid username or password')
    
    return render_template('login.html', title='Login')


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.')
    return redirect(url_for('main.index'))