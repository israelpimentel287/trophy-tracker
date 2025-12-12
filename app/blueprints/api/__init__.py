"""API blueprints for REST endpoints."""
from app.blueprints.api.sync import sync_api_bp
from app.blueprints.api.companion import companion_api_bp
from app.blueprints.api.notifications import notifications_api_bp

__all__ = [
    'sync_api_bp',
    'companion_api_bp',
    'notifications_api_bp'
]