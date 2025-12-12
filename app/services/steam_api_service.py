"""Steam API client for Steam Web API endpoints."""

import requests
from typing import List, Dict, Optional
from flask import current_app as app


class SteamAPIService:
    """Steam Web API client."""
    
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        self.api_key = api_key or app.config.get('STEAM_API_KEY')
        self.base_url = base_url or app.config.get('STEAM_WEB_API_URL', 'https://api.steampowered.com')
        
        if not self.api_key:
            raise ValueError("Steam API key not configured")
    
    def get_user_games(self, steam_id: str, include_appinfo: bool = True, 
                      include_free_games: bool = True) -> List[Dict]:
        """Get games owned by a Steam user."""
        url = f"{self.base_url}/IPlayerService/GetOwnedGames/v0001/"
        params = {
            'key': self.api_key,
            'steamid': steam_id,
            'format': 'json',
            'include_appinfo': include_appinfo,
            'include_played_free_games': include_free_games
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if 'response' in data and 'games' in data['response']:
                return data['response']['games']
            return []
            
        except requests.RequestException as e:
            print(f"Steam API error for {steam_id}: {e}")
            return []
    
    def get_user_achievements(self, steam_id: str, app_id: int) -> List[Dict]:
        """Get user achievement progress for a game."""
        url = f"{self.base_url}/ISteamUserStats/GetPlayerAchievements/v0001/"
        params = {
            'key': self.api_key,
            'steamid': steam_id,
            'appid': app_id,
            'format': 'json'
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if 'playerstats' in data and 'achievements' in data['playerstats']:
                return data['playerstats']['achievements']
            return []
            
        except requests.RequestException as e:
            print(f"Steam API error for app {app_id}: {e}")
            return []
    
    def get_achievement_percentages(self, app_id: int) -> Dict[str, float]:
        """Get global achievement unlock percentages."""
        url = f"{self.base_url}/ISteamUserStats/GetGlobalAchievementPercentagesForApp/v0002/"
        params = {
            'gameid': app_id,
            'format': 'json'
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if 'achievementpercentages' in data and 'achievements' in data['achievementpercentages']:
                return {
                    ach['name']: float(ach['percent'])
                    for ach in data['achievementpercentages']['achievements']
                }
            return {}
            
        except requests.RequestException as e:
            print(f"Steam API error for app {app_id}: {e}")
            return {}
    
    def get_game_schema(self, app_id: int) -> List[Dict]:
        """Get achievement schema for a game."""
        url = f"{self.base_url}/ISteamUserStats/GetSchemaForGame/v2/"
        params = {
            'key': self.api_key,
            'appid': app_id,
            'format': 'json'
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if 'game' in data and 'availableGameStats' in data['game']:
                return data['game']['availableGameStats'].get('achievements', [])
            return []
            
        except requests.RequestException as e:
            print(f"Steam API error for app {app_id}: {e}")
            return []


steam_api_service = None

def init_steam_api_service():
    """Initialize the global SteamAPIService instance."""
    global steam_api_service
    if steam_api_service is None:
        steam_api_service = SteamAPIService()
    return steam_api_service