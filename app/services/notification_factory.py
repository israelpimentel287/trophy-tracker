"""Notification factory for creating platinum trophy notifications."""
import uuid
from datetime import datetime
from app.models import Notification
from app.config.trophy_config import NOTIFICATION_DURATIONS


class NotificationFactory:
    """Factory for creating notification data structures."""

    @staticmethod
    def create_platinum_trophy_notification(game, user) -> Notification:
        """Create platinum trophy notification for game completion."""
        notif = Notification(
            id=str(uuid.uuid4()),
            user_id=user.id,
            type="platinum_trophy",
            title="Platinum Trophy Earned!",
            message=f"You completed {game.name} 100% and earned the Platinum Trophy!",
            data={
                "game_id": game.id,
                "game_name": game.name,
                "steam_app_id": game.steam_app_id,
                "icon_html": '<img src="/static/images/trophies/platinum-trophy.svg" style="width: 48px; height: 48px; flex-shrink: 0;" alt="Platinum">'
            },
            priority=3,
            display_duration=NOTIFICATION_DURATIONS.get('platinum', 8000),
            created_at=datetime.utcnow()
        )

        notif.can_batch = False
        notif.group_id = None
        notif.timestamp = datetime.utcnow().isoformat()
        notif.animation = "trophy_pop"

        return notif