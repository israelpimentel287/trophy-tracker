import requests
import re
from flask import current_app as app
from datetime import datetime

# Helper functions for formatting and display
def format_playtime(minutes):
    """Convert minutes to readable playtime format."""
    if not minutes or minutes == 0:
        return "Never played"
    
    if minutes < 60:
        return f"{minutes}m"
    elif minutes < 1440:  # Less than 24 hours
        hours = round(minutes / 60, 1)
        return f"{hours}h"
    else:  # 24+ hours
        hours = round(minutes / 60, 1)
        return f"{hours}h"


def get_rarity_color(tier):
    """Get CSS class for rarity tier."""
    colors = {
        'platinum': 'text-cyan-400',
        'gold': 'text-yellow-400',
        'silver': 'text-gray-400',
        'bronze': 'text-amber-600'
    }
    return colors.get(tier, 'text-gray-500')

# Steam ID extraction functions
def extract_steam_id(steam_input):
    """Extract a 64-bit Steam ID from various input formats."""
    if not steam_input or not isinstance(steam_input, str):
        return None

    steam_input = steam_input.strip()

    # Check if it's a direct Steam ID
    direct_id_match = re.match(r'^(765\d{14})$', steam_input)
    if direct_id_match:
        steam_id = direct_id_match.group(1)
        if validate_steam_id(steam_id):
            return steam_id

    # Try Profile URL format
    profile_url_match = re.search(r'steamcommunity\.com/profiles/(\d+)', steam_input)
    if profile_url_match:
        steam_id = profile_url_match.group(1)
        if validate_steam_id(steam_id):
            return steam_id

    # Try custom URL format
    custom_url_match = re.search(r'steamcommunity\.com/id/([^/\s]+)', steam_input)
    if custom_url_match:
        custom_name = custom_url_match.group(1)
        return resolve_vanity_url(custom_name)

    # Try as direct custom name
    if not re.match(r'^\d+$', steam_input) and '/' not in steam_input and '.' not in steam_input:
        return resolve_vanity_url(steam_input)

    return None


def validate_steam_id(steam_id):
    """Validate that a Steam ID is in the correct 64-bit format."""
    if not steam_id:
        return False

    if not steam_id.isdigit():
        return False

    if len(steam_id) != 17:
        return False

    if not steam_id.startswith('765'):
        return False

    try:
        steam_id_int = int(steam_id)
        if steam_id_int < 76561197960265728:
            return False
        return True
    except ValueError:
        return False


def resolve_vanity_url(vanity_name):
    """Resolve a Steam vanity URL (custom name) to a 64-bit Steam ID using Steam Web API."""
    api_key = app.config.get('STEAM_API_KEY')

    if not api_key or api_key == 'your-steam-api-key':
        print("Steam API key not configured")
        return None

    vanity_name = vanity_name.strip().lower()

    url = 'https://api.steampowered.com/ISteamUser/ResolveVanityURL/v0001/'
    params = {
        'key': api_key,
        'vanityurl': vanity_name,
        'url_type': 1,
        'format': 'json'
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        if 'response' in data:
            response_data = data['response']
            if response_data.get('success') == 1 and 'steamid' in response_data:
                steam_id = response_data['steamid']
                if validate_steam_id(steam_id):
                    return steam_id
            elif response_data.get('success') == 42:
                print(f"Vanity URL not found: {vanity_name}")
            else:
                print(f"Could not resolve vanity URL {vanity_name}")
        return None
    except Exception as e:
        print(f"Error resolving vanity URL {vanity_name}: {e}")
        return None


def get_steam_profile_url(steam_id):
    """Generate Steam profile URL from Steam ID."""
    if not validate_steam_id(steam_id):
        return None
    return f"https://steamcommunity.com/profiles/{steam_id}/"


# Template helpers
def register_template_helpers(app):
    @app.context_processor
    def template_helpers():
        """Template context helpers."""
        return {
            'format_playtime': format_playtime,
            'get_rarity_color': get_rarity_color
        }