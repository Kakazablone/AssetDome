from __future__ import absolute_import, unicode_literals
import os
from celery import Celery
from celery.schedules import crontab
from calendar import monthrange
from datetime import datetime

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'AssetDome.settings')

# Create a Celery app instance.
app = Celery('AssetDome')

# Load the Django settings into the Celery app.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Automatically discover tasks in all registered Django app configs.
app.autodiscover_tasks()

def is_last_day_of_month():
    today = datetime.now()
    last_day = monthrange(today.year, today.month)[1]  # Gets the last day of the current month
    return today.day == last_day

# Define the schedule for periodic tasks.
app.conf.beat_schedule = {
    # Monthly report: Last day of every month at 23:59
    'send_monthly_report': {
        'task': 'assets.tasks.send_monthly_report',
        'schedule': crontab(day_of_month='28-31', hour=23, minute=59),
    },
    # Fully depreciated asset notification: Every day at midnight
    'send_fully_depreciated_assets_email': {
        'task': 'assets.tasks.send_fully_depreciated_assets_email',
        'schedule': crontab(hour=0, minute=0),
    },
    # Quarterly report: First day of January, April, July, and October at midnight
    'send_quarterly_summary_report': {
        'task': 'assets.tasks.send_quarterly_summary_report',
        'schedule': crontab(month_of_year='1,4,7,10', day_of_month=1, hour=0, minute=0),
    },
}
