from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_moment import Moment
from celery import Celery
import redis
from datetime import datetime
from config import Config

# Initialize Flask extensions
db = SQLAlchemy()
migrate = Migrate()
login = LoginManager()
login.login_view = 'auth.login'
moment = Moment()
celery = Celery(__name__)

# Celery setup
def make_celery(app):
    celery = Celery(
        app.import_name,
        broker=app.config.get('broker_url') or app.config.get('CELERY_BROKER_URL'),
        backend=app.config.get('result_backend') or app.config.get('CELERY_RESULT_BACKEND')
    )
    celery.conf.update(app.config)

    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery.Task = ContextTask
    return celery

# Factory function
def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Enable template auto-reload and disable caching
    app.config['TEMPLATES_AUTO_RELOAD'] = True
    app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
    app.jinja_env.auto_reload = True

    # Initialize core extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login.init_app(app)
    moment.init_app(app)

    # Redis connection
    redis_client = None
    redis_connected = False
    try:
        redis_client = redis.from_url(
            app.config.get('REDIS_NOTIFICATION_URL', 'redis://localhost:6380/2'),
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
            retry_on_timeout=True
        )
        redis_client.ping()
        redis_connected = True
        print("Redis connected")
    except Exception as e:
        print(f"Redis unavailable, using in-memory fallback: {e}")
    app.redis_client = redis_client
    app.redis_connected = redis_connected

    # Celery setup
    celery = make_celery(app)
    app.celery = celery
    globals()['celery'] = celery
  
    # Blueprints
    from app.blueprints import register_blueprints
    with app.app_context():
        register_blueprints(app)

    # Import routes and register template helpers
    from app import routes
    routes.register_template_helpers(app)

    # Health and init routes
    @app.route('/health')
    def health_check():
        status = {
            'status': 'healthy',
            'database': 'connected',
            'redis': 'connected' if app.redis_connected else 'disconnected',
            'celery': 'configured'
        }
        try:
            db.session.execute('SELECT 1')
        except Exception:
            status['database'] = 'disconnected'
            status['status'] = 'degraded'
        return status, 200 if status['status'] == 'healthy' else 503

    # Error handlers
    @app.errorhandler(404)
    def not_found_error(error):
        try:
            return render_template('404.html'), 404
        except Exception:
            return "<h1>404 - Page Not Found</h1>", 404

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        try:
            return render_template('500.html'), 500
        except Exception:
            return "<h1>500 - Internal Server Error</h1>", 500

    # Template filters
    @app.template_filter('notification_time')
    def notification_time_filter(timestamp):
        try:
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            diff = datetime.utcnow() - dt.replace(tzinfo=None)
            if diff.days > 0:
                return f"{diff.days}d ago"
            elif diff.seconds > 3600:
                return f"{diff.seconds // 3600}h ago"
            elif diff.seconds > 60:
                return f"{diff.seconds // 60}m ago"
            return "Just now"
        except Exception:
            return "Unknown"

    @app.template_filter('trophy_rarity_class')
    def trophy_rarity_class_filter(percentage):
        if percentage <= 1.0:
            return 'trophy-platinum'
        elif percentage <= 10.0:
            return 'trophy-gold'
        elif percentage <= 25.0:
            return 'trophy-silver'
        return 'trophy-bronze'

    @app.template_filter('time_ago')
    def time_ago_filter(dt):
        if not dt:
            return "Never"
        now = datetime.utcnow()
        if dt.tzinfo:
            dt = dt.replace(tzinfo=None)
        diff = now - dt
        if diff.days > 365:
            years = diff.days // 365
            return f"{years} year{'s' if years > 1 else ''} ago"
        elif diff.days > 30:
            months = diff.days // 30
            return f"{months} month{'s' if months > 1 else ''} ago"
        elif diff.days > 0:
            return f"{diff.days} day{'s' if diff.days > 1 else ''} ago"
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"{hours} hour{'s' if hours > 1 else ''} ago"
        elif diff.seconds > 60:
            minutes = diff.seconds // 60
            return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
        return "Just now"

    # User loader for Flask-Login
    from app.models import User

    @login.user_loader
    def load_user(user_id):
        """Load user by ID for Flask-Login."""
        return User.query.get(int(user_id))

    # Initialize Steam API service
    from app.services.steam_api_service import init_steam_api_service
    with app.app_context():
        init_steam_api_service()

    return app