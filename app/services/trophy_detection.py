"""Detects special trophy events like Platinum trophies."""

import logging
from app.models import Game, User, Notification
from app import db
from app.services.notification_factory import NotificationFactory

logger = logging.getLogger(__name__)


def check_for_platinum_trophy(game, user):
    try:
        if game.completion_percentage != 100.0:
            return False

        try:
            dialect = db.engine.dialect.name
        except Exception:
            dialect = None

        if dialect == "postgresql":
            existing_platinum = Notification.query.filter_by(
                user_id=user.id,
                type="platinum_trophy"
            ).filter(
                Notification.data['game_id'].cast(db.String) == str(game.id)
            ).first()
        else:
            existing_platinum = Notification.query.filter_by(
                user_id=user.id,
                type="platinum_trophy"
            ).filter(
                Notification.data.contains({'game_id': game.id})
            ).first()

        if existing_platinum:
            logger.debug(f"Platinum already awarded for {game.name}")
            return False

        logger.info(f"Platinum detected: {game.name} for user {user.id}")

        platinum_notification = NotificationFactory.create_platinum_trophy_notification(game, user)

        db.session.add(platinum_notification)
        db.session.commit()

        logger.info(f"Platinum trophy notification saved to database for {game.name}")

        return True

    except Exception as e:
        logger.error(f"Error checking platinum trophy for game {getattr(game, 'id', '?')}: {e}", exc_info=True)
        return False