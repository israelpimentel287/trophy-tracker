"""Steam API integration and synchronization orchestration."""

import requests
import time
from flask import current_app as app
from app import db
from app.models import User, Game, Achievement
from datetime import datetime
from celery import current_task, shared_task
from sqlalchemy.exc import SQLAlchemyError

from app.services import (
    TrophyService,
    steam_api_service
)


class SteamAPI:
    """Manages Steam data synchronization."""
    
    def __init__(self):
        self._api_service = None 
    
    @property
    def api_service(self):
        if self._api_service is None:
            from app.services.steam_api_service import steam_api_service, init_steam_api_service
        
            if steam_api_service is None:
                print("Lazy-initializing steam_api_service...")
                try:
                    init_steam_api_service()
                    from app.services.steam_api_service import steam_api_service as reloaded_service
                    self._api_service = reloaded_service
                    print("steam_api_service lazy-initialized")
                except Exception as e:
                    print(f"Error lazy-initializing steam_api_service: {e}")
                    raise
            else:
                self._api_service = steam_api_service
    
        return self._api_service

    def get_user_games(self, steam_id):
        return self.api_service.get_user_games(steam_id)
    
    def get_user_achievements(self, steam_id, app_id):
        return self.api_service.get_user_achievements(steam_id, app_id)
    
    def get_achievement_percentages(self, app_id):
        return self.api_service.get_achievement_percentages(app_id)
    
    def get_game_schema(self, app_id):
        return self.api_service.get_game_schema(app_id)
    
    def sync_achievements(self, user, game):
        print(f"    Getting achievement schema for {game.name} (ID: {game.steam_app_id})")
        
        schema = self.get_game_schema(game.steam_app_id)
        if not schema:
            print(f"    No achievement schema found for {game.name}")
            return 0
        
        print(f"    Found {len(schema)} achievements in schema")
        
        user_achievements = self.get_user_achievements(user.steam_id, game.steam_app_id)
        user_ach_dict = {ach['apiname']: ach for ach in user_achievements}
        
        print(f"    Found {len(user_achievements)} user achievements")
        
        global_percentages = self.get_achievement_percentages(game.steam_app_id)
        print(f"    Found global percentages for {len(global_percentages)} achievements")
        
        unlocked_count = 0
        total_count = len(schema)
        achievements_processed = 0
        newly_unlocked_achievements = []
        
        previous_completion = game.completion_percentage
        was_completed = previous_completion == 100.0
        
        for ach_schema in schema:
            try:
                ach_name = ach_schema['name']
                
                achievement = Achievement.query.filter_by(
                    user_id=user.id,
                    game_id=game.id,
                    steam_achievement_id=ach_name
                ).first()
                
                was_previously_unlocked = achievement.unlocked if achievement else False
                
                if not achievement:
                    achievement = Achievement(
                        user_id=user.id,
                        game_id=game.id,
                        steam_achievement_id=ach_name,
                        name=ach_schema.get('displayName', ach_name),
                        description=ach_schema.get('description', ''),
                        icon_url=ach_schema.get('icon', ''),
                        icon_gray_url=ach_schema.get('icongray', '')
                    )
                    db.session.add(achievement)
                
                achievement.name = ach_schema.get('displayName', ach_name)
                achievement.description = ach_schema.get('description', '')
                achievement.icon_url = ach_schema.get('icon', '')
                achievement.icon_gray_url = ach_schema.get('icongray', '')
                
                achievement.global_percentage = float(global_percentages.get(ach_name, 100.0))
                achievement.calculate_rarity_tier()
                
                if ach_name in user_ach_dict:
                    user_ach = user_ach_dict[ach_name]
                    if user_ach['achieved'] == 1:
                        if not was_previously_unlocked:
                            newly_unlocked_achievements.append(achievement)
                            rarity_desc = TrophyService.get_tier_display_name(achievement.rarity_tier)
                            print(f"      NEW TROPHY: {achievement.name} - {rarity_desc} ({achievement.global_percentage:.2f}%)")
                        
                        achievement.unlocked = True
                        if user_ach['unlocktime'] > 0:
                            achievement.unlock_time = datetime.fromtimestamp(user_ach['unlocktime'])
                        unlocked_count += 1
                        print(f"      ✓ {achievement.name} - {achievement.rarity_tier}")
                    else:
                        achievement.unlocked = False
                        achievement.unlock_time = None
                else:
                    achievement.unlocked = False
                    achievement.unlock_time = None
                
                achievements_processed += 1
                
            except Exception as e:
                print(f"    Error processing achievement {ach_schema.get('name', 'Unknown')}: {e}")
                continue
        
        game.total_achievements = total_count
        game.unlocked_achievements = unlocked_count
        game.calculate_completion()
        
        print(f"    Game {game.name}: {unlocked_count}/{total_count} achievements unlocked ({game.completion_percentage:.1f}%)")
        
        try:
            db.session.commit()
        except SQLAlchemyError as e:
            print(f"    Error committing changes: {e}")
            db.session.rollback()
            return achievements_processed
        
        is_now_completed = game.completion_percentage == 100.0
        
        if is_now_completed and not was_completed:
            print(f"    GAME COMPLETED: {game.name}")
            self._handle_game_completion(user, game)
        
        return achievements_processed
    
    def _handle_game_completion(self, user, game):
        """Handle platinum trophy creation for game completion."""
        try:
            platinum_trophy = Achievement.query.filter_by(
                user_id=user.id,
                game_id=game.id,
                steam_achievement_id=f'PLATINUM_{game.steam_app_id}'
            ).first()
            
            if not platinum_trophy:
                platinum_trophy = Achievement(
                    user_id=user.id,
                    game_id=game.id,
                    steam_achievement_id=f'PLATINUM_{game.steam_app_id}',
                    name=f'{game.name} - Master',
                    description=f'Unlock all achievements in {game.name}',
                    icon_url=game.header_image or '/static/images/platinum_trophy.png',
                    icon_gray_url=game.header_image or '/static/images/platinum_trophy_gray.png',
                    global_percentage=1.0,
                    rarity_tier='platinum',
                    unlocked=True,
                    unlock_time=datetime.utcnow()
                )
                db.session.add(platinum_trophy)
                db.session.flush()
                
                print(f"      PLATINUM TROPHY CREATED: {platinum_trophy.name}")
            else:
                if not platinum_trophy.unlocked:
                    platinum_trophy.unlocked = True
                    platinum_trophy.unlock_time = datetime.utcnow()
                    print(f"      PLATINUM TROPHY RE-UNLOCKED: {platinum_trophy.name}")
                else:
                    print(f"      PLATINUM TROPHY ALREADY UNLOCKED: {platinum_trophy.name}")
            
            db.session.commit()
            
        except Exception as e:
            print(f"      Error creating platinum trophy: {e}")
            db.session.rollback()


steam_api = SteamAPI()


def sync_single_game_sync(user, game_data):
    app_id = game_data['appid']
    game_name = game_data.get('name', f'Game {app_id}')
    
    print(f"  Syncing game: {game_name} (ID: {app_id})")
    
    playtime = game_data.get('playtime_forever', 0)
    if playtime == 0:
        schema = steam_api.get_game_schema(app_id)
        if not schema:
            print(f"  Skipping {game_name} - no playtime and no achievements")
            return False
    
    try:
        game = Game.query.filter_by(user_id=user.id, steam_app_id=app_id).first()
        if not game:
            game = Game(
                user_id=user.id,
                steam_app_id=app_id,
                name=game_name,
                header_image=f"https://steamcdn-a.akamaihd.net/steam/apps/{app_id}/header.jpg"
            )
            db.session.add(game)
            db.session.flush()
        
        game.name = game_name
        game.playtime_forever = game_data.get('playtime_forever', 0)
        game.playtime_2weeks = game_data.get('playtime_2weeks', 0)
        
        if 'rtime_last_played' in game_data and game_data['rtime_last_played'] > 0:
            game.last_played = datetime.fromtimestamp(game_data['rtime_last_played'])
        
        achievements_synced = steam_api.sync_achievements(user, game)
        
        if achievements_synced > 0:
            print(f"  ✓ {game_name}: {achievements_synced} achievements synced")
            return True
        else:
            print(f"  - {game_name}: No achievements to sync")
            return False
            
    except SQLAlchemyError as e:
        print(f"  Database error syncing {game_name}: {e}")
        db.session.rollback()
        raise e
    except Exception as e:
        print(f"  Error syncing {game_name}: {e}")
        db.session.rollback()
        return False