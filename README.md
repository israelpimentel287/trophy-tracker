🏆 Trophy Tracker
Track your Steam achievements with real-time notifications and progress stats.
Trophy Dashboard
![Trophy Dashboard](screenshots/trophy-collection.png)
*Track your achievement collection with trophy tier breakdowns*

Game Library
![Game Library](screenshots/games.png)
*View all your Steam games with completion percentages*

Achievement Details
![Achievement Details](screenshots/achievements.png)
*See individual achievements with rarity information*

Features

Real-time notifications when you unlock achievements
Trophy tiers - Achievements ranked by rarity (Bronze, Silver, Gold, Platinum)
Game library - Track all your Steam games in one place
Progress tracking - See your completion percentage for each game
REST API - Build your own apps on top of Trophy Tracker
Background syncing - Automatic updates via Celery task queue


Tech Stack
Backend

Flask (Python 3.13.5)
PostgreSQL
Redis
Celery
Gunicorn (production)

Frontend

HTML/CSS/JavaScript
Polling for live updates

APIs

Steam Web API

Installation
What You Need

Python 3.13+
PostgreSQL
Redis
Steam API Key (get one here)

Setup

Clone the repo

bashgit clone https://github.com/israelpimentel287/trophy-tracker.git
cd trophy-tracker

Create a virtual environment

bashpython -m venv .venv
.venv\Scripts\activate

Install dependencies

bashpip install -r requirements.txt

Set up environment variables

Create a .env file:
envSTEAM_API_KEY=your_steam_api_key
SECRET_KEY=your_secret_key
DATABASE_URL=postgresql://user:password@localhost:5432/trophy_tracker
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/1
REDIS_NOTIFICATION_URL=redis://localhost:6379/2
TROPHY_NOTIFICATIONS_ENABLED=True
NOTIFICATION_DEBUG_MODE=False

Set up the database

bashflask db upgrade

Start Redis

bashdocker run -d -p 6379:6379 redis:latest

Run the app

You need THREE terminals:
Terminal 1 - Web server:
bashpython app.py
Terminal 2 - Background worker:
bashpython celery_worker.py --loglevel=info
Terminal 3 - Task scheduler:
bashcelery -A celery_worker beat --loglevel=info

Open your browser

http://localhost:5000

Deployment
Deployed on Render.com with:

Web service (Flask + Gunicorn)
PostgreSQL database
Redis instance
Celery background worker

Environment Variables for Production
SECRET_KEY              # Generate: python -c "import secrets; print(secrets.token_hex(32))"
STEAM_API_KEY           # Your Steam API key
DATABASE_URL            # From Render PostgreSQL
REDIS_URL               # From Render Redis
CELERY_BROKER_URL       # Same as REDIS_URL
CELERY_RESULT_BACKEND   # REDIS_URL with /1
REDIS_NOTIFICATION_URL  # REDIS_URL with /2
TROPHY_NOTIFICATIONS_ENABLED=True
NOTIFICATION_DEBUG_MODE=False

API Docs
Endpoints
All requests need an API key in the X-API-Key header.
Get all achievements
httpGET /api/achievements
Get recent achievements
httpGET /api/achievements/recent?limit=10
Get your games
httpGET /api/games
Sync with Steam
httpPOST /api/sync

Trophy Tiers
Achievements are ranked by how rare they are:
Tier        Rarity                      Icon
Platinum    100% completion             Platinum
Gold        1-10% of players            Gold 
Silver      10-25% of players           Silver 
Bronze      More than 25% of players    Bronze 

Project Structure
trophy-tracker/
├── app/
│   ├── blueprints/        # Routes (main, api, companion_api)
│   ├── services/          # Core logic (steam, tiers, notifications)
│   ├── tasks/             # Background jobs
│   ├── static/            # CSS, JS, images
│   └── templates/         # HTML files
├── migrations/            # Database migrations
├── config.py              # App settings
├── app.py                 # Main app file
├── celery_worker.py       # Background worker
├── Procfile               # Render config
├── requirements.txt       # Python packages
└── runtime.txt            # Python version

Contributing
Want to help? Feel free to open a pull request!

Fork the repo
Create your branch (git checkout -b feature/cool-feature)
Commit your changes (git commit -m 'Add cool feature')
Push to the branch (git push origin feature/cool-feature)
Open a pull request


License
MIT License - see the LICENSE file for details.

Author
Israel Pimentel

GitHub: @israelpimentel287


Support
Got issues or questions? Open an issue on GitHub.

