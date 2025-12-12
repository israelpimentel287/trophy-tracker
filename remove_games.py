from app import create_app, db
from app.models import Game, Achievement, Notification

app = create_app()

with app.app_context():
    games = Game.query.all()
    print("\nYour Games:")
    print("=" * 60)
    for game in games:
        print(f"{game.id}: {game.name} - {game.unlocked_achievements}/{game.total_achievements} achievements")
    
    print("\n" + "=" * 60)
    game_ids = input("\nEnter game IDs to delete (comma-separated, e.g. 1,2,3): ")
    
    if game_ids.strip():
        ids = [int(id.strip()) for id in game_ids.split(',')]
        
        for game_id in ids:
            game = Game.query.get(game_id)
            if game:
                print(f"\nDeleting {game.name}...")
                
                # Delete achievements
                achievements = Achievement.query.filter_by(game_id=game.id).all()
                for achievement in achievements:
                    db.session.delete(achievement)
                
                # Delete game
                db.session.delete(game)
                print(f"  Deleted game and {len(achievements)} achievements")
        
        db.session.commit()
        print("\nDone! Refresh your browser.")
    else:
        print("No games deleted.")
