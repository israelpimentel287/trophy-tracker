"""
Script to import SQLite data into PostgreSQL database
"""
import sqlite3
from app import create_app, db
from app.models import User, Game, Achievement

def import_data():
    """Import data from SQLite to PostgreSQL"""
    
    # Create Flask app context
    app = create_app()
    
    with app.app_context():
        print("Connecting to SQLite database...")
        sqlite_conn = sqlite3.connect('app.db')
        sqlite_conn.row_factory = sqlite3.Row
        cursor = sqlite_conn.cursor()
        
        try:
            # Import Users
            print("\nImporting users...")
            cursor.execute("SELECT * FROM user")
            users = cursor.fetchall()
            
            for user_row in users:
                user = User(
                    id=user_row['id'],
                    username=user_row['username'],
                    email=user_row['email'],
                    password_hash=user_row['password_hash'],
                    steam_id=user_row['steam_id'],
                    steam_persona_name=user_row['steam_persona_name'],
                    steam_profile_url=user_row['steam_profile_url'],
                    steam_avatar_url=user_row['steam_avatar_url'],
                    companion_token=user_row['companion_token'] if 'companion_token' in user_row.keys() else None,
                    companion_machine_id=user_row['companion_machine_id'] if 'companion_machine_id' in user_row.keys() else None,
                    companion_version=user_row['companion_version'] if 'companion_version' in user_row.keys() else None,
                    companion_last_seen=user_row['companion_last_seen'] if 'companion_last_seen' in user_row.keys() else None,
                    companion_status=user_row['companion_status'] if 'companion_status' in user_row.keys() else None,
                    created_at=user_row['created_at'],
                    last_sync=user_row['last_sync'] if 'last_sync' in user_row.keys() else None
                )
                db.session.add(user)
            
            db.session.commit()
            print(f"✅ Imported {len(users)} users")
            
            # Import Games
            print("\nImporting games...")
            cursor.execute("SELECT * FROM game")
            games = cursor.fetchall()
            
            for game_row in games:
                game = Game(
                    id=game_row['id'],
                    steam_app_id=game_row['steam_app_id'],
                    name=game_row['name'],
                    header_image=game_row['header_image'],
                    user_id=game_row['user_id'],
                    playtime_forever=game_row['playtime_forever'],
                    playtime_2weeks=game_row['playtime_2weeks'] if 'playtime_2weeks' in game_row.keys() else None,
                    total_achievements=game_row['total_achievements'],
                    unlocked_achievements=game_row['unlocked_achievements'],
                    completion_percentage=game_row['completion_percentage'],
                    last_played=game_row['last_played'] if 'last_played' in game_row.keys() else None,
                    added_at=game_row['added_at'],
                    last_synced=game_row['last_synced'] if 'last_synced' in game_row.keys() else None
                )
                db.session.add(game)
            
            db.session.commit()
            print(f"✅ Imported {len(games)} games")
            
            # Import Achievements
            print("\nImporting achievements...")
            cursor.execute("SELECT * FROM achievement")
            achievements = cursor.fetchall()
            
            for ach_row in achievements:
                achievement = Achievement(
                    id=ach_row['id'],
                    steam_achievement_id=ach_row['steam_achievement_id'] if 'steam_achievement_id' in ach_row.keys() else None,
                    name=ach_row['name'],
                    description=ach_row['description'] if 'description' in ach_row.keys() else None,
                    icon_url=ach_row['icon_url'] if 'icon_url' in ach_row.keys() else None,
                    icon_gray_url=ach_row['icon_gray_url'] if 'icon_gray_url' in ach_row.keys() else None,
                    user_id=ach_row['user_id'],
                    game_id=ach_row['game_id'],
                    unlocked=ach_row['unlocked'],
                    unlock_time=ach_row['unlock_time'] if 'unlock_time' in ach_row.keys() else None,
                    global_percentage=ach_row['global_percentage'] if 'global_percentage' in ach_row.keys() else None,
                    rarity_tier=ach_row['rarity_tier'] if 'rarity_tier' in ach_row.keys() else None,
                    notification_sent=ach_row['notification_sent'] if 'notification_sent' in ach_row.keys() else False,
                    notification_sent_at=ach_row['notification_sent_at'] if 'notification_sent_at' in ach_row.keys() else None,
                    created_at=ach_row['created_at'] if 'created_at' in ach_row.keys() else None,
                    updated_at=ach_row['updated_at'] if 'updated_at' in ach_row.keys() else None
                )
                db.session.add(achievement)
            
            # Commit in batches to avoid memory issues
            if len(achievements) > 1000:
                print("Committing in batches...")
                db.session.commit()
            
            db.session.commit()
            print(f"✅ Imported {len(achievements)} achievements")
            
            print("\n🎉 Import completed successfully!")
            
            # Reset sequences for auto-increment
            print("\nResetting PostgreSQL sequences...")
            db.session.execute(db.text("SELECT setval('user_id_seq', (SELECT MAX(id) FROM \"user\"))"))
            db.session.execute(db.text("SELECT setval('game_id_seq', (SELECT MAX(id) FROM game))"))
            db.session.execute(db.text("SELECT setval('achievement_id_seq', (SELECT MAX(id) FROM achievement))"))
            db.session.commit()
            print("✅ Sequences reset")
            
        except Exception as e:
            print(f"❌ Error during import: {e}")
            db.session.rollback()
            raise
        
        finally:
            sqlite_conn.close()

if __name__ == '__main__':
    import_data()