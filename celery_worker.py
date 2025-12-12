import os
import sys
import signal
import argparse
import logging
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app import celery as celery_app
import app.tasks
from config import Config

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class CeleryWorkerManager:
    
    def __init__(self):
        self.config = Config()
        self.celery = celery_app
        
    def validate_environment(self):
        required_vars = [
            'STEAM_API_KEY',
            'CELERY_BROKER_URL',
            'CELERY_RESULT_BACKEND'
        ]

        missing_vars = []
        for var in required_vars:
            if not os.environ.get(var):
                missing_vars.append(var)
        
        if missing_vars:
            logger.warning(f"Missing environment variables: {', '.join(missing_vars)} - using defaults from Config.")
        
        return True
    
    def start_worker(self, queue=None, concurrency=None, loglevel='info'):
        if not self.validate_environment():
            return False
        
        logger.info("Starting Celery worker for Trophy Tracker...")
        
        if concurrency is None:
            if queue == 'steam_sync':
                concurrency = 2
            elif queue == 'steam_batch':
                concurrency = 1
            else:
                concurrency = 1
        logger.info(f"Using concurrency={concurrency}")

        try:
            worker_args = [
                'worker',
                f'--loglevel={loglevel}',
                '--pool=solo',
                f'--concurrency={concurrency}',
                '--without-gossip',
                '--without-mingle',
                '--without-heartbeat',
            ]
            
            if queue:
                worker_args.append(f'--queues={queue}')
                logger.info(f"Worker queue: {queue}")
            
            self.celery.worker_main(worker_args)
                
        except KeyboardInterrupt:
            logger.info("Worker stopped by user")
        except Exception as e:
            logger.error(f"Error starting worker: {e}")
            return False
        
        return True
    
    def start_beat(self):
        if not self.validate_environment():
            return False
        
        logger.info("Starting Celery beat scheduler...")
        try:
            self.celery.start(['beat', '--loglevel=info'])
        except KeyboardInterrupt:
            logger.info("Beat scheduler stopped by user")
        except Exception as e:
            logger.error(f"Error starting beat scheduler: {e}")
            return False
        
        return True
    
    def start_flower(self, port=5555):
        try:
            import flower
        except ImportError:
            logger.error("Flower not installed. Install with: pip install flower")
            return False
        
        logger.info(f"Starting Flower on port {port}...")
        try:
            import subprocess
            cmd = [
                sys.executable, '-m', 'flower',
                '--broker', self.config.broker_url,
                '--port', str(port)
            ]
            subprocess.run(cmd)
        except KeyboardInterrupt:
            logger.info("Flower monitoring stopped by user")
        except Exception as e:
            logger.error(f"Error starting Flower: {e}")
            return False
        return True
    
    def show_status(self):
        logger.info("Checking Celery status...")
        try:
            with self.celery.connection() as conn:
                conn.ensure_connection(max_retries=3)
            logger.info("Broker connection successful")
        except Exception as e:
            logger.error(f"Broker connection failed: {e}")
            return False
        
        try:
            inspect = self.celery.control.inspect()
            active = inspect.active()
            if active:
                logger.info(f"Active workers: {len(active)}")
        except Exception as e:
            logger.warning(f"Could not inspect Celery: {e}")
        
        return True

def main():
    parser = argparse.ArgumentParser(description='Trophy Tracker Celery Worker')
    parser.add_argument('--queue', '-q', help='Specific queue (steam_sync, steam_batch, etc.)')
    parser.add_argument('--concurrency', '-c', type=int, help='Number of concurrent workers')
    parser.add_argument('--loglevel', '-l', default='info', choices=['debug', 'info', 'warning', 'error'])
    parser.add_argument('--beat', action='store_true', help='Start beat scheduler')
    parser.add_argument('--flower', action='store_true', help='Start Flower monitoring')
    parser.add_argument('--flower-port', type=int, default=5555, help='Flower port')
    parser.add_argument('--status', action='store_true', help='Show Celery status')
    
    args = parser.parse_args()
    manager = CeleryWorkerManager()
    
    if args.status:
        return manager.show_status()
    if args.beat:
        return manager.start_beat()
    elif args.flower:
        return manager.start_flower(args.flower_port)
    else:
        return manager.start_worker(args.queue, args.concurrency, args.loglevel)

if __name__ == '__main__':
    try:
        sys.exit(0 if main() else 1)
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)