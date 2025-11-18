import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')

import django
django.setup()

from django.conf import settings

app = Celery('cpds_project')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.conf.update(
    broker_url=settings.CELERY_BROKER_URL,
    result_backend=settings.CELERY_RESULT_BACKEND,
    accept_content=settings.CELERY_ACCEPT_CONTENT,
    task_serializer=settings.CELERY_TASK_SERIALIZER,
    result_serializer=settings.CELERY_RESULT_SERIALIZER,
    timezone=settings.CELERY_TIMEZONE,
    beat_scheduler=settings.CELERY_BEAT_SCHEDULER,
)
app.autodiscover_tasks()
app.conf.task_routes = {
    'core.tasks.crawl_*': {'queue': 'crawler'},
    'core.tasks.cleanup_*': {'queue': 'maintenance'},
}

@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
