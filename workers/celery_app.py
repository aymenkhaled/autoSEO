"""Celery application configuration for AutoSEO background tasks."""
import os
from celery import Celery
from celery.schedules import crontab

# Read Redis URL from environment
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

app = Celery(
    "autoseo",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=[
        "workers.tasks.crawl",
        "workers.tasks.fix",
        "workers.tasks.report",
    ],
)

app.conf.update(
    # Serialization
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    
    # Results
    result_expires=3600,
    
    # Worker settings
    worker_max_tasks_per_child=50,  # Restart worker after 50 tasks (memory leak prevention)
    worker_prefetch_multiplier=1,   # Fair scheduling
    
    # Task time limits
    task_soft_time_limit=1800,  # 30 min soft limit (raises SoftTimeLimitExceeded)
    task_time_limit=3600,       # 60 min hard limit (kills task)
    
    # Timezone
    timezone="UTC",
    enable_utc=True,
)

# --- Periodic Tasks (Celery Beat) ---
app.conf.beat_schedule = {
    "weekly-crawls": {
        "task": "workers.tasks.crawl.run_scheduled_crawls",
        "schedule": crontab(hour=2, minute=0),  # Every day at 2 AM UTC
    },
    "refresh-tokens": {
        "task": "workers.tasks.crawl.refresh_expiring_tokens",
        "schedule": crontab(hour=1, minute=0),  # Every day at 1 AM UTC
    },
}
