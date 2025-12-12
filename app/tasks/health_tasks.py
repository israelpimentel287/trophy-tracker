"""Health check and monitoring tasks."""

import logging
from datetime import datetime

from flask import current_app
from app import celery, create_app

logger = logging.getLogger(__name__)


def get_flask_app():
    try:
        return current_app._get_current_object()
    except RuntimeError:
        return create_app()


@celery.task
def health_check():
    return {
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'worker_id': health_check.request.id if hasattr(health_check, 'request') else 'unknown',
        'notifications_enabled': True
    }