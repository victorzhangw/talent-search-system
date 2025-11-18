from .celery import app as celery_app
from .celery import app as celery

__all__ = ('celery_app', 'celery')
