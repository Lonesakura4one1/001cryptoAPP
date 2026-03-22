"""
Celery configuration for crypto platform backend.
"""

import os
from celery import Celery
from django.conf import settings

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings.development')

app = Celery('crypto_platform')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
app.autodiscover_tasks()

# Configure Celery
app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
)

# Beat schedule for periodic tasks
app.conf.beat_schedule = {
    'update-crypto-prices': {
        'task': 'backend.transactions.tasks.update_crypto_prices',
        'schedule': 60.0,  # Every 1 minute
    },
    'process-aml-checks': {
        'task': 'backend.compliance.tasks.process_aml_checks',
        'schedule': 300.0,  # Every 5 minutes
    },
    'cleanup-sessions': {
        'task': 'backend.users.tasks.cleanup_expired_sessions',
        'schedule': 3600.0,  # Every hour
    },
    'generate-reports': {
        'task': 'backend.compliance.tasks.generate_daily_reports',
        'schedule': 86400.0,  # Every day at midnight
    },
}

if __name__ == '__main__':
    app.start()
