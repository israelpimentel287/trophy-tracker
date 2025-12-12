import os
from dotenv import load_dotenv
from datetime import timedelta

load_dotenv()

basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-secret-key-here'
    
    database_url = os.environ.get('DATABASE_URL')
    if database_url and database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    SQLALCHEMY_DATABASE_URI = database_url or \
        'sqlite:///' + os.path.join(basedir, 'app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    STEAM_API_KEY = os.environ.get('STEAM_API_KEY') or 'your-steam-api-key'
    STEAM_WEB_API_URL = 'https://api.steampowered.com'
    
    REDIS_HOST = os.environ.get('REDIS_HOST', '127.0.0.1')
    REDIS_PORT = os.environ.get('REDIS_PORT', '6380')

    broker_url = os.environ.get('CELERY_BROKER_URL') or f'redis://{REDIS_HOST}:{REDIS_PORT}/0'
    result_backend = os.environ.get('CELERY_RESULT_BACKEND') or f'redis://{REDIS_HOST}:{REDIS_PORT}/1'      
    task_serializer = 'json'
    result_serializer = 'json'
    accept_content = ['json']
    timezone = 'UTC'
    enable_utc = True

    worker_pool = 'solo'
    worker_concurrency = 1
    worker_prefetch_multiplier = 1
    task_acks_late = True
    worker_disable_rate_limits = False
    task_track_started = True
    worker_send_task_events = True
    task_send_sent_event = True
    worker_max_tasks_per_child = 100

    task_retry_delay = 60
    task_max_retries = 3

    task_annotations = {'*': {'rate_limit': '10/m'}}
    task_routes = {}

    STEAM_SYNC_RATE_LIMIT = '10/m'
    STEAM_SYNC_TIME_LIMIT = 600

    REDIS_NOTIFICATION_URL = os.environ.get('REDIS_NOTIFICATION_URL') or f'redis://{REDIS_HOST}:{REDIS_PORT}/2'
    REDIS_NOTIFICATION_KEY_PREFIX = 'steam_trophy_notifications:'
    REDIS_NOTIFICATION_EXPIRE_TIME = 3600

    TROPHY_NOTIFICATIONS_ENABLED = os.environ.get('TROPHY_NOTIFICATIONS_ENABLED', 'True').lower() == 'true' 
    TROPHY_SOUND_ENABLED_DEFAULT = True
    TROPHY_POPUP_ENABLED_DEFAULT = True
    TROPHY_NOTIFICATION_DURATION_DEFAULT = 5000
    TROPHY_NOTIFICATION_POSITION_DEFAULT = 'top-right'
    TROPHY_STYLE_DEFAULT = 'premium'

    TROPHY_RARITY_THRESHOLDS = {
        'platinum': 0.01,
        'gold': 0.05,
        'silver': 0.25,
        'bronze': 1.0
    }

    NOTIFICATION_RATE_LIMIT_PER_USER = 100
    NOTIFICATION_BURST_LIMIT = 10
    NOTIFICATION_BURST_WINDOW = 60
    TROPHY_NOTIFICATION_QUEUE_SIZE = 50
    TROPHY_NOTIFICATION_BATCH_SIZE = 5
    TROPHY_NOTIFICATION_BATCH_DELAY = 2

    SYSTEM_NOTIFICATIONS_ENABLED = True
    SYNC_PROGRESS_NOTIFICATIONS = True
    MILESTONE_NOTIFICATIONS_ENABLED = True
    ERROR_NOTIFICATIONS_ENABLED = True
    MILESTONE_THRESHOLDS = [10, 25, 50, 100, 250, 500, 1000, 2500, 5000]
    MILESTONE_NOTIFICATION_COOLDOWN = 300
    PROGRESS_UPDATE_INTERVAL = 2
    PROGRESS_UPDATE_THRESHOLD = 5
    WS_ROOM_CLEANUP_INTERVAL = 300
    WS_MAX_CONNECTIONS_PER_USER = 5
    WS_CONNECTION_TIMEOUT = 3600
    PUSH_NOTIFICATIONS_ENABLED = os.environ.get('PUSH_NOTIFICATIONS_ENABLED', 'False').lower() == 'true'    
    VAPID_PUBLIC_KEY = os.environ.get('VAPID_PUBLIC_KEY')
    VAPID_PRIVATE_KEY = os.environ.get('VAPID_PRIVATE_KEY')
    VAPID_CLAIMS_EMAIL = os.environ.get('VAPID_CLAIMS_EMAIL', 'mailto:admin@steamtrophyenhancer.com')       
    EMAIL_NOTIFICATIONS_ENABLED = os.environ.get('EMAIL_NOTIFICATIONS_ENABLED', 'False').lower() == 'true'  
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'localhost')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 25))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'False').lower() == 'true'
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', 'noreply@steamtrophyenhancer.com')
    NOTIFICATION_HISTORY_RETENTION_DAYS = int(os.environ.get('NOTIFICATION_HISTORY_RETENTION_DAYS', 30))    
    NOTIFICATION_CLEANUP_INTERVAL = 86400
    USER_NOTIFICATION_DEFAULTS = {
        'trophy_notifications_enabled': True,
        'sound_enabled': True,
        'trophy_popup_enabled': True,
        'milestone_notifications_enabled': True,
        'sync_notifications_enabled': True,
        'error_notifications_enabled': True,
        'trophy_style': TROPHY_STYLE_DEFAULT,
        'notification_position': TROPHY_NOTIFICATION_POSITION_DEFAULT,
        'trophy_duration': TROPHY_NOTIFICATION_DURATION_DEFAULT,
        'notification_sound_volume': 0.7,
        'rare_trophy_emphasis': True,
        'completion_celebrations': True
    }

    NOTIFICATION_CACHE_TIMEOUT = 300
    TROPHY_ICON_CACHE_TIMEOUT = 3600
    NOTIFICATION_DEBUG_MODE = os.environ.get('NOTIFICATION_DEBUG_MODE', 'False').lower() == 'true'
    NOTIFICATION_TEST_MODE = os.environ.get('NOTIFICATION_TEST_MODE', 'False').lower() == 'true'
    WS_CSRF_PROTECTION = True
    WS_ORIGIN_CHECK = True
    WS_SESSION_VALIDATION = True

    FEATURE_FLAGS = {
        'real_time_notifications': True,
        'trophy_animations': True,
        'sound_effects': True,
        'milestone_tracking': True,
        'rare_trophy_highlights': True,
        'completion_celebrations': True,
        'notification_history': True,
        'custom_notification_sounds': False,
        'notification_scheduling': False,
        'trophy_sharing': False
    }

class DevelopmentConfig(Config):
    DEBUG = True
    NOTIFICATION_DEBUG_MODE = True
    NOTIFICATION_TEST_MODE = True
    PROGRESS_UPDATE_INTERVAL = 1
    TROPHY_NOTIFICATION_BATCH_DELAY = 1

class ProductionConfig(Config):
    DEBUG = False
    NOTIFICATION_DEBUG_MODE = False
    NOTIFICATION_TEST_MODE = False
    NOTIFICATION_RATE_LIMIT_PER_USER = 50
    WS_MAX_CONNECTIONS_PER_USER = 3

class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    TROPHY_NOTIFICATIONS_ENABLED = False
    WTF_CSRF_ENABLED = False
    NOTIFICATION_TEST_MODE = True

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}