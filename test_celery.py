"""Test script for Celery setup."""

import redis
import time

def test_redis_connection():
    try:
        r = redis.Redis(host='localhost', port=6380, db=0)
        r.ping()
        print("Redis connection successful")
        return True
    except Exception as e:
        print(f"Redis connection failed: {e}")
        print("Make sure Redis is running: docker-compose up -d redis")
        return False

def test_celery_connection():
    try:
        from app import celery
        
        inspect = celery.control.inspect()
        stats = inspect.stats()
        if stats:
            print("Celery workers found and responding")
            print(f"Active workers: {list(stats.keys())}")
            return True
        else:
            print("Celery broker connected but no workers found")
            print("Make sure to run: python celery_worker.py")
            return False
    except Exception as e:
        print(f"Celery connection failed: {e}")
        print("Check if Redis is running and worker is started")
        return False

def test_simple_task():
    try:
        from app.tasks import health_check
        
        print("Testing simple task...")
        result = health_check.delay()
        print(f"Task queued")
        print(f"Task ID: {result.id}")
        print(f"Initial State: {result.state}")
        
        print("Waiting for task completion...")
        for i in range(10):
            time.sleep(1)
            if result.ready():
                break
            print(f"Still waiting... ({i+1}/10)")
        
        print(f"Final State: {result.state}")
        
        if result.state == 'SUCCESS':
            print(f"Result: {result.result}")
            return True
        elif result.state == 'FAILURE':
            print(f"Error: {result.info}")
            return False
        else:
            print(f"Task did not complete in time (State: {result.state})")
            return False
            
    except ImportError as e:
        print(f"Task import failed: {e}")
        print("Make sure Flask app is properly configured")
        return False
    except Exception as e:
        print(f"Task test failed: {e}")
        return False

def test_task_registration():
    try:
        from app import celery
        inspect = celery.control.inspect()
        registered = inspect.registered()
        
        if registered:
            print("Registered tasks:")
            for worker, tasks in registered.items():
                print(f"Worker {worker}:")
                for task in sorted(tasks):
                    if not task.startswith('celery.'):
                        print(f"  • {task}")
            return True
        else:
            print("No registered tasks found")
            return False
            
    except Exception as e:
        print(f"Task registration check failed: {e}")
        return False

def main():
    print("=== Trophy Tracker Celery Test ===")
    
    if not test_redis_connection():
        print("Setup incomplete - Redis not accessible")
        print("Run: docker-compose up -d redis")
        return
    
    if not test_celery_connection():
        print("Setup incomplete - Start Celery worker first")
        print("Run: python celery_worker.py")
        return
    
    test_task_registration()
    
    if test_simple_task():
        print("All tests passed! Your setup is working correctly.")
        print("Ready to use Celery tasks in your Flask app!")
    else:
        print("Task execution failed - check your task definitions")
        print("Make sure the worker is processing tasks")

if __name__ == "__main__":
    main()