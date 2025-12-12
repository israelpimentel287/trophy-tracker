"""Admin and batch operations tasks."""

import logging
from flask import current_app
from app import create_app

logger = logging.getLogger(__name__)


def get_flask_app():
    try:
        return current_app._get_current_object()
    except RuntimeError:
        return create_app()