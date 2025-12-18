"""
Celery Application Configuration
"""
from celery import Celery
from config import settings

app = Celery(
    'actorhub_worker',
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        'tasks.training',
        'tasks.face_recognition',
        'tasks.notifications',
        'tasks.cleanup',
    ]
)

app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour max
    task_soft_time_limit=3300,  # 55 minutes soft limit
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    result_expires=86400,  # 24 hours
    broker_connection_retry_on_startup=True,
)

# Task routing
app.conf.task_routes = {
    'tasks.training.*': {'queue': 'training'},
    'tasks.face_recognition.*': {'queue': 'face'},
    'tasks.notifications.*': {'queue': 'notifications'},
    'tasks.cleanup.*': {'queue': 'cleanup'},
}

# Periodic tasks
app.conf.beat_schedule = {
    'cleanup-expired-downloads': {
        'task': 'tasks.cleanup.cleanup_expired_downloads',
        'schedule': 3600.0,  # Every hour
    },
    'cleanup-orphan-files': {
        'task': 'tasks.cleanup.cleanup_orphan_files',
        'schedule': 86400.0,  # Every day
    },
    'update-usage-stats': {
        'task': 'tasks.cleanup.update_usage_stats',
        'schedule': 300.0,  # Every 5 minutes
    },
}

if __name__ == '__main__':
    app.start()
