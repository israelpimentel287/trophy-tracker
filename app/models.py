from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(120), index=True, unique=True)
    password_hash = db.Column(db.String(256))
   
    steam_id = db.Column(db.String(64), unique=True, index=True)
    steam_persona_name = db.Column(db.String(128))
    steam_profile_url = db.Column(db.String(255))
    steam_avatar_url = db.Column(db.String(255))
   
    companion_token = db.Column(db.String(64), unique=True, nullable=True)
    companion_machine_id = db.Column(db.String(100), nullable=True)
    companion_version = db.Column(db.String(20), nullable=True)
    companion_last_seen = db.Column(db.DateTime, nullable=True)
    companion_status = db.Column(db.String(20), default='inactive')
   
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_sync = db.Column(db.DateTime)
   
    achievements = db.relationship('Achievement', backref='owner', lazy='dynamic')
    games = db.relationship('Game', backref='owner', lazy='dynamic')
    notifications = db.relationship('Notification', backref='user', lazy='dynamic')
   
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
   
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
   
    def get_trophy_counts(self):
        """Get trophy counts by tier."""
        achievements = self.achievements.filter_by(unlocked=True).all()
        counts = {'platinum': 0, 'gold': 0, 'silver': 0, 'bronze': 0}
        
        for achievement in achievements:
            if achievement.rarity_tier in ['gold', 'silver', 'bronze']:
                counts[achievement.rarity_tier] += 1
        
        completed_games = self.games.filter_by(completion_percentage=100.0).count()
        counts['platinum'] = completed_games
        
        return counts
    
    def get_trophy_level(self):
        counts = self.get_trophy_counts()
        
        points = (
            counts['platinum'] * 300 +
            counts['gold'] * 90 +
            counts['silver'] * 30 +
            counts['bronze'] * 15
        )
        
        level = points // 100
        
        return level
   
    def __repr__(self):
        return f'<User {self.username}>'


class Game(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    steam_app_id = db.Column(db.Integer, unique=True, index=True)
    name = db.Column(db.String(255), index=True)
    header_image = db.Column(db.String(255))
   
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    playtime_forever = db.Column(db.Integer, default=0)
    playtime_2weeks = db.Column(db.Integer, default=0)
   
    total_achievements = db.Column(db.Integer, default=0)
    unlocked_achievements = db.Column(db.Integer, default=0)
    completion_percentage = db.Column(db.Float, default=0.0)
   
    last_played = db.Column(db.DateTime)
    added_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_synced = db.Column(db.DateTime)
   
    achievements = db.relationship('Achievement', backref='game', lazy='dynamic')
   
    def calculate_completion(self):
        """Calculate achievement completion percentage."""
        if self.total_achievements > 0:
            self.completion_percentage = (self.unlocked_achievements / self.total_achievements) * 100
        else:
            self.completion_percentage = 0.0
   
    def get_trophy_tier(self):
        """Get trophy tier based on completion."""
        if self.completion_percentage == 100:
            return 'platinum'
        elif self.completion_percentage >= 75:
            return 'gold'
        elif self.completion_percentage >= 50:
            return 'silver'
        elif self.completion_percentage >= 25:
            return 'bronze'
        else:
            return None
    
    def update_last_synced(self):
        """Update last synced timestamp."""
        self.last_synced = datetime.utcnow()
   
    def __repr__(self):
        return f'<Game {self.name}>'


class Achievement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    steam_achievement_id = db.Column(db.String(128), index=True)
    name = db.Column(db.String(255))
    description = db.Column(db.Text)
    icon_url = db.Column(db.String(255))
    icon_gray_url = db.Column(db.String(255))
   
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    game_id = db.Column(db.Integer, db.ForeignKey('game.id'))
   
    unlocked = db.Column(db.Boolean, default=False)
    unlock_time = db.Column(db.DateTime)
   
    global_percentage = db.Column(db.Float, default=0.0)
    rarity_tier = db.Column(db.String(20))
   
    notification_sent = db.Column(db.Boolean, default=False)
    notification_sent_at = db.Column(db.DateTime)
   
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
   
    def calculate_rarity_tier(self):
        """Set rarity tier based on unlock percentage."""
        if self.global_percentage < 10.0:
            self.rarity_tier = 'gold'
        elif self.global_percentage < 25.0:
            self.rarity_tier = 'silver'
        else:
            self.rarity_tier = 'bronze'
   
    def get_rarity_description(self):
        """Get rarity description."""
        if self.rarity_tier == 'platinum':
            return 'Ultra Rare'
        elif self.rarity_tier == 'gold':
            return 'Very Rare'
        elif self.rarity_tier == 'silver':
            return 'Rare'
        else:
            return 'Common'
   
    def mark_notification_sent(self):
        """Mark notification as sent."""
        self.notification_sent = True
        self.notification_sent_at = datetime.utcnow()
   
    def __repr__(self):
        return f'<Achievement {self.name}>'


class Notification(db.Model):
    """Store user notifications."""
    
    __tablename__ = 'notifications'
    
    id = db.Column(db.String(36), primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    
    type = db.Column(db.String(50), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    message = db.Column(db.Text)
    
    data = db.Column(db.JSON)
    priority = db.Column(db.Integer, default=2)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    read_at = db.Column(db.DateTime)
    dismissed_at = db.Column(db.DateTime)
    sent_at = db.Column(db.DateTime)
    
    display_duration = db.Column(db.Integer, default=5000)
    
    @property
    def is_read(self):
        """Check if read."""
        return self.read_at is not None
    
    @property
    def is_dismissed(self):
        """Check if dismissed."""
        return self.dismissed_at is not None
    
    @property
    def is_sent(self):
        """Check if sent."""
        return self.sent_at is not None
    
    def mark_read(self):
        """Mark as read."""
        if not self.read_at:
            self.read_at = datetime.utcnow()
    
    def mark_dismissed(self):
        """Mark as dismissed."""
        if not self.dismissed_at:
            self.dismissed_at = datetime.utcnow()
    
    def mark_sent(self):
        """Mark as sent."""
        if not self.sent_at:
            self.sent_at = datetime.utcnow()
    
    def __repr__(self):
        return f'<Notification {self.type}: {self.title}>'


class TaskProgress:
    """Track task progress for background jobs."""
    
    def __init__(self, total=0, current=0, status="pending", message="", data=None):
        self.total = total
        self.current = current
        self.status = status
        self.message = message
        self.data = data or {}
        self.start_time = datetime.utcnow()
        self.end_time = None
    
    def update(self, current=None, message=None, status=None, data=None):
        """Update progress."""
        if current is not None:
            self.current = current
        if message is not None:
            self.message = message
        if status is not None:
            self.status = status
        if data is not None:
            self.data.update(data)
    
    def complete(self, message=None):
        """Mark as completed."""
        self.status = "completed"
        self.current = self.total
        self.end_time = datetime.utcnow()
        if message:
            self.message = message
    
    def fail(self, message=None):
        """Mark as failed."""
        self.status = "failed"
        self.end_time = datetime.utcnow()
        if message:
            self.message = message
    
    def to_dict(self):
        """Convert to dictionary."""
        return {
            'total': self.total,
            'current': self.current,
            'status': self.status,
            'message': self.message,
            'data': self.data.copy() if self.data else {},
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'percentage': (self.current / self.total * 100) if self.total > 0 else 0
        }
    
    def copy(self):
        """Create a copy of the TaskProgress object."""
        new_progress = TaskProgress(
            total=self.total,
            current=self.current,
            status=self.status,
            message=self.message,
            data=self.data.copy() if self.data else {}
        )
        new_progress.start_time = self.start_time
        new_progress.end_time = self.end_time
        return new_progress