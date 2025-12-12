"""Steam library sync tasks."""

import time
import logging
from datetime import datetime, timedelta
import requests
from sqlalchemy.exc import SQLAlchemyError

from flask import current_app
from app import db, celery, create_app
from app.models import User, Game
from app.steam_api import steam_api, sync_single_game_sync

from .helpers import SyncTaskHelper
from app.services.trophy_detection import check_for_platinum_trophy

logger = logging.getLogger(__name__)


def get_flask_app():
    """Get or create Flask app instance for Celery context."""
    try:
        return current_app._get_current_object()
    except RuntimeError:
        return create_app()


@celery.task(bind=True, autoretry_for=(requests.RequestException, SQLAlchemyError), 
             retry_kwargs={'max_retries': 3, 'countdown': 60})
def full_steam_sync(self, user_id, force_refresh=False):
    """Complete Steam library sync with all games and achievements."""
    app = get_flask_app()
    with app.app_context():
        try:
            user = User.query.get(user_id)
            if not user or not user.steam_id:
                raise ValueError(f"Invalid user {user_id}")

            helper = SyncTaskHelper(self, user_id, 'full')

            games_data = steam_api.get_user_games(user.steam_id)
            if not games_data:
                return helper.complete_sync('No games found in Steam library', total=0)

            games_data = sorted(games_data, key=lambda x: x.get('playtime_forever', 0), reverse=True)
            tracker = helper.start_sync(len(games_data), "Beginning complete Steam library sync...")

            for i, game_data in enumerate(games_data):
                try:
                    game_name = game_data.get("name", f"Game {game_data.get('appid')}")
                    helper.update_progress(game_name)

                    if not force_refresh:
                        existing_game = Game.query.filter_by(
                            user_id=user.id, 
                            steam_app_id=game_data['appid']
                        ).first()
                        
                        if (existing_game and existing_game.last_synced and 
                            existing_game.last_synced > datetime.utcnow() - timedelta(days=7) and
                            game_data.get('playtime_2weeks', 0) == 0):
                            tracker.increment_skipped()
                            continue

                    success = sync_single_game_sync(user, game_data)
                    if success:
                        tracker.increment_synced()
                        
                        game = Game.query.filter_by(
                            user_id=user.id, 
                            steam_app_id=game_data['appid']
                        ).first()
                        if game:
                            check_for_platinum_trophy(game, user)
                    else:
                        tracker.increment_skipped()

                    time.sleep(0.5)

                    if (i + 1) % 10 == 0:
                        db.session.commit()
                        
                        self.update_state(
                            state='PROGRESS',
                            meta={
                                'percent': int((i + 1) / len(games_data) * 100),
                                'current_game': game_name,
                                'games_synced': tracker.progress.games_synced,
                                'games_skipped': tracker.progress.games_skipped,
                                'games_failed': tracker.progress.games_failed,
                                'total_games': len(games_data),
                                'current_index': i + 1,
                                'phase': 'syncing',
                                'status': f"Processed {i + 1}/{len(games_data)} games...",
                                'duration_seconds': tracker.get_duration_seconds(),
                                'avg_games_per_second': tracker.get_rate()
                            }
                        )
                        

                except Exception as e:
                    logger.error(f"Error syncing game {game_data.get('name', 'Unknown')}: {e}")
                    tracker.increment_failed()
                    continue

            user.last_sync = datetime.utcnow()
            db.session.commit()

            tracker.set_phase('finalizing', 'Calculating user statistics...')

            from .stats_tasks import calculate_user_stats
            calculate_user_stats.delay(user_id)

            return helper.complete_sync(
                'Full Steam sync completed successfully',
                games_synced=tracker.progress.games_synced,
                games_skipped=tracker.progress.games_skipped,
                failed_games=[],
                total=len(games_data),
                stats={
                    'duration_seconds': tracker.get_duration_seconds(),
                    'avg_games_per_second': tracker.get_rate()
                }
            )

        except Exception as e:
            logger.error(f"Error in full_steam_sync: {e}", exc_info=True)

            if isinstance(e, (requests.RequestException, SQLAlchemyError)):
                raise self.retry(exc=e)
            else:
                raise e


@celery.task(bind=True, autoretry_for=(requests.RequestException, SQLAlchemyError),
             retry_kwargs={'max_retries': 3, 'countdown': 30})
def quick_steam_sync(self, user_id, max_games=20):
    """Quick sync of user's most played games."""
    app = get_flask_app()
    with app.app_context():
        try:
            max_games = int(max_games or 20)

            user = User.query.get(user_id)
            if not user or not user.steam_id:
                raise ValueError(f"Invalid user {user_id}")

            helper = SyncTaskHelper(self, user_id, 'quick')

            games_data = steam_api.get_user_games(user.steam_id)
            if not games_data:
                return helper.complete_sync('No games found', total=0)

            games_data = sorted(
                games_data,
                key=lambda x: (x.get('playtime_2weeks', 0), x.get('playtime_forever', 0)),
                reverse=True
            )[:max_games]

            tracker = helper.start_sync(len(games_data), f"Syncing your top {max_games} most played games...")

            for game_data in games_data:
                try:
                    game_name = game_data.get("name", "Unknown Game")
                    helper.update_progress(game_name)

                    if sync_single_game_sync(user, game_data):
                        tracker.increment_synced()

                        game = Game.query.filter_by(
                            user_id=user.id,
                            steam_app_id=game_data['appid']
                        ).first()

                        if game:
                            check_for_platinum_trophy(game, user)
                    else:
                        tracker.increment_skipped()

                    time.sleep(0.3)

                except Exception as e:
                    logger.error(f"Error in quick sync for game {game_data.get('name', 'Unknown')}: {e}")
                    tracker.increment_failed()
                    continue

            user.last_sync = datetime.utcnow()
            db.session.commit()

            return helper.complete_sync(
                f'Quick sync completed - {tracker.progress.games_synced} games updated',
                games_synced=tracker.progress.games_synced,
                games_skipped=tracker.progress.games_skipped,
                total=len(games_data),
                stats={
                    'duration_seconds': tracker.get_duration_seconds(),
                    'avg_games_per_second': tracker.get_rate()
                }
            )

        except Exception as e:
            logger.error(f"Error in quick_steam_sync: {e}", exc_info=True)

            if isinstance(e, (requests.RequestException, SQLAlchemyError)):
                raise self.retry(exc=e)
            else:
                raise e


@celery.task(bind=True, autoretry_for=(requests.RequestException, SQLAlchemyError),
             retry_kwargs={'max_retries': 3, 'countdown': 30})
def sync_specific_games(self, user_id, app_ids):
    """Sync specific games by their Steam App IDs."""
    app = get_flask_app()
    with app.app_context():
        try:
            user = User.query.get(user_id)
            if not user or not user.steam_id:
                raise ValueError(f"Invalid user {user_id}")

            if not isinstance(app_ids, list):
                app_ids = [app_ids]

            helper = SyncTaskHelper(self, user_id, 'specific')

            games_data = steam_api.get_user_games(user.steam_id)
            games_dict = {game['appid']: game for game in games_data}

            tracker = helper.start_sync(len(app_ids), f"Syncing {len(app_ids)} specific games...")
            failed_games = []

            for app_id in app_ids:
                try:
                    game_data = games_dict.get(app_id, {
                        'appid': app_id,
                        'name': f'Game {app_id}',
                        'playtime_forever': 0
                    })
                    game_name = game_data.get('name', f'Game {app_id}')

                    helper.update_progress(game_name)

                    if sync_single_game_sync(user, game_data):
                        tracker.increment_synced()
                        
                        game = Game.query.filter_by(
                            user_id=user.id, 
                            steam_app_id=app_id
                        ).first()
                        if game:
                            check_for_platinum_trophy(game, user)
                    else:
                        tracker.increment_skipped()
                        failed_games.append(app_id)

                    time.sleep(0.3)

                except Exception as e:
                    logger.error(f"Error syncing specific game {app_id}: {e}")
                    tracker.increment_failed()
                    failed_games.append(app_id)
                    continue

            db.session.commit()

            return helper.complete_sync(
                'Specific games sync completed',
                games_synced=tracker.progress.games_synced,
                games_skipped=tracker.progress.games_skipped,
                failed_games=failed_games,
                total=len(app_ids),
                stats={
                    'duration_seconds': tracker.get_duration_seconds(),
                    'successful_app_ids': [app_id for app_id in app_ids if app_id not in failed_games]
                }
            )

        except Exception as e:
            logger.error(f"Error in sync_specific_games: {e}", exc_info=True)

            if isinstance(e, (requests.RequestException, SQLAlchemyError)):
                raise self.retry(exc=e)
            else:
                raise e
