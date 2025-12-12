"""Script to remove test achievements from database."""

import os
import sys
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

sys.path.append('.')

try:
    from app import app, db
    from app.models import User, Game, Achievement, Notification
except ImportError:
    print("Error: Could not import models. Make sure you're running this from your app directory.")
    sys.exit(1)

def cleanup_test_achievements():
    test_games = [
        'FINAL FANTASY XVI',
        'Liar\'s Bar', 
        'Dota 2',
        'Spacewar'
    ]
    
    print("Starting cleanup of test achievements...")
    
    try:
        games_to_clean = Game.query.filter(Game.name.in_(test_games)).all()
        
        if not games_to_clean:
            print("No test games found in database.")
            return
        
        total_achievements_removed = 0
        total_notifications_removed = 0
        
        for game in games_to_clean:
            print(f"\nProcessing game: {game.name}")
            
            achievements = Achievement.query.filter_by(game_id=game.id).all()
            achievement_count = len(achievements)
            
            if achievement_count > 0:
                for achievement in achievements:
                    related_notifications = Notification.query.filter(
                        Notification.data.contains(f'"achievement_id": {achievement.id}')
                    ).all()
                    
                    for notification in related_notifications:
                        db.session.delete(notification)
                        total_notifications_removed += 1
                
                Achievement.query.filter_by(game_id=game.id).delete()
                total_achievements_removed += achievement_count
                
                print(f"   Removed {achievement_count} achievements")
                
                game.total_achievements = 0
                game.unlocked_achievements = 0
                game.completion_percentage = 0.0
                
            else:
                print(f"   No achievements found for {game.name}")
        
        db.session.commit()
        
        print(f"\nCleanup completed")
        print(f"   Total achievements removed: {total_achievements_removed}")
        print(f"   Total notifications removed: {total_notifications_removed}")
        print(f"   Games processed: {len(games_to_clean)}")
        
        users = User.query.all()
        for user in users:
            print(f"   Refreshing trophy counts for user: {user.username}")
        
        print("\nAll done! Test achievements have been removed.")
        
    except Exception as e:
        print(f"Error during cleanup: {str(e)}")
        db.session.rollback()
        raise

def main():
    print("Trophy Tracker - Test Achievement Cleanup")
    print("=" * 50)
    
    with app.app_context():
        total_games = Game.query.count()
        total_achievements = Achievement.query.count()
        total_unlocked = Achievement.query.filter_by(unlocked=True).count()
        
        print(f"Current database stats:")
        print(f"   Games: {total_games}")
        print(f"   Total achievements: {total_achievements}")
        print(f"   Unlocked achievements: {total_unlocked}")
        
        response = input("\nDo you want to proceed with cleanup? (y/N): ")
        
        if response.lower() in ['y', 'yes']:
            cleanup_test_achievements()
        else:
            print("Cleanup cancelled.")

if __name__ == "__main__":
    main()