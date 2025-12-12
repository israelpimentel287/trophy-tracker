"""Trophy tier calculations and trophy-related business logic."""

from app.config.trophy_config import TROPHY_TIERS


class TrophyService:
    
    @staticmethod
    def get_tier_display_name(tier: str) -> str:
        return TROPHY_TIERS.get(tier, TROPHY_TIERS['bronze'])['display_name']