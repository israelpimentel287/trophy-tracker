"""Blueprint registration for Flask routes."""
from flask import Blueprint
from app.blueprints.auth import auth_bp
from app.blueprints.main import main_bp
from app.blueprints.profile import profile_bp
from app.blueprints.games import games_bp
from app.blueprints.trophies import trophies_bp
from app.blueprints.debug import debug_bp
from app.blueprints.api.sync import sync_api_bp
from app.blueprints.api.companion import companion_api_bp
from app.blueprints.api.notifications import notifications_api_bp  

def register_blueprints(app):
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(games_bp)
    app.register_blueprint(trophies_bp)
    app.register_blueprint(sync_api_bp, url_prefix='/api')
    app.register_blueprint(companion_api_bp, url_prefix='/api/companion')
    app.register_blueprint(notifications_api_bp)
    app.register_blueprint(debug_bp, url_prefix='/debug')
    print("All blueprints registered")

__all__ = [
    'auth_bp',
    'main_bp',
    'profile_bp',
    'games_bp',
    'trophies_bp',
    'debug_bp',
    'sync_api_bp',
    'companion_api_bp',
    'notifications_api_bp',  
    'register_blueprints'
]