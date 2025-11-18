from django.db.models.signals import pre_save
from django.dispatch import receiver
from django_celery_beat.models import CrontabSchedule

@receiver(pre_save, sender=CrontabSchedule)
def fix_crontab_empty_fields(sender, instance, **kwargs):
    """
    自動修復 CrontabSchedule 的空欄位，避免 Celery Beat ParseException
    """
    # 自動填入空欄位為 '*'
    if not instance.hour or instance.hour == '':
        instance.hour = '*'
    if not instance.day_of_week or instance.day_of_week == '':
        instance.day_of_week = '*'
    if not instance.day_of_month or instance.day_of_month == '':
        instance.day_of_month = '*'
    if not instance.month_of_year or instance.month_of_year == '':
        instance.month_of_year = '*'