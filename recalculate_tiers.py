"""
Recalculate all achievement tiers with new thresholds.
Run this script from your project root: python recalculate_all_tiers.py
"""

from app import create_app, db
from app.models import Achievement

def recalculate_all_tiers():
    app = create_app()
    
    with app.app_context():
        print("Fetching all achievements...")
        achievements = Achievement.query.all()
        total = len(achievements)
        print(f"Found {total} achievements to recalculate")
        
        updated = 0
        for i, ach in enumerate(achievements):
            old_tier = ach.rarity_tier
            ach.calculate_rarity_tier()
            
            if old_tier != ach.rarity_tier:
                updated += 1
                if updated <= 10:  # Show first 10 changes
                    print(f"  Updated: {ach.name} - {old_tier} -> {ach.rarity_tier} ({ach.global_percentage}%)")
            
            # Progress indicator
            if (i + 1) % 1000 == 0:
                print(f"  Progress: {i + 1}/{total}...")
        
        print(f"\nCommitting changes to database...")
        db.session.commit()
        print(f"✓ Successfully updated {updated} achievements")
        
        # Show new distribution
        print(f"\n=== NEW TIER DISTRIBUTION ===")
        gold_count = Achievement.query.filter_by(rarity_tier='gold').count()
        silver_count = Achievement.query.filter_by(rarity_tier='silver').count()
        bronze_count = Achievement.query.filter_by(rarity_tier='bronze').count()
        platinum_count = Achievement.query.filter_by(rarity_tier='platinum').count()
        
        print(f"Platinum: {platinum_count}")
        print(f"Gold (<10%): {gold_count}")
        print(f"Silver (10-25%): {silver_count}")
        print(f"Bronze (≥25%): {bronze_count}")
        
        # Show YOUR unlocked trophies
        print(f"\n=== YOUR UNLOCKED TROPHIES ===")
        from app.models import User
        user = User.query.first()
        
        if user:
            unlocked = Achievement.query.filter_by(user_id=user.id, unlocked=True).all()
            my_platinum = len([a for a in unlocked if a.rarity_tier == 'platinum'])
            my_gold = len([a for a in unlocked if a.rarity_tier == 'gold'])
            my_silver = len([a for a in unlocked if a.rarity_tier == 'silver'])
            my_bronze = len([a for a in unlocked if a.rarity_tier == 'bronze'])
            
            print(f"Platinum: {my_platinum}")
            print(f"Gold (<10%): {my_gold}")
            print(f"Silver (10-25%): {my_silver}")
            print(f"Bronze (≥25%): {my_bronze}")
            print(f"Total: {len(unlocked)}")
        
        print(f"\n✓ All done! Refresh your browser to see the correct trophy counts.")

if __name__ == '__main__':
    recalculate_all_tiers()