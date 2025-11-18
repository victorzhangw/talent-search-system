#!/usr/bin/env python
import os
import sys
import django
from pathlib import Path

# 將項目路徑添加到Python路徑
project_root = Path(__file__).parent
sys.path.append(str(project_root))

# 設定Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')
django.setup()

from django.conf import settings
import logging

print("檢查郵件設定...")
print("=" * 50)

# 檢查郵件設定
print("📧 郵件設定:")
print(f"  EMAIL_BACKEND: {getattr(settings, 'EMAIL_BACKEND', '未設定')}")
print(f"  EMAIL_HOST: {getattr(settings, 'EMAIL_HOST', '未設定')}")
print(f"  EMAIL_PORT: {getattr(settings, 'EMAIL_PORT', '未設定')}")
print(f"  EMAIL_USE_TLS: {getattr(settings, 'EMAIL_USE_TLS', '未設定')}")
print(f"  EMAIL_HOST_USER: {getattr(settings, 'EMAIL_HOST_USER', '未設定')}")
print(f"  EMAIL_HOST_PASSWORD: {'已設定' if getattr(settings, 'EMAIL_HOST_PASSWORD', None) else '未設定'}")
print(f"  DEFAULT_FROM_EMAIL: {getattr(settings, 'DEFAULT_FROM_EMAIL', '未設定')}")

print(f"\n📋 其他相關設定:")
print(f"  DEBUG: {getattr(settings, 'DEBUG', '未設定')}")
print(f"  SITE_URL: {getattr(settings, 'SITE_URL', '未設定')}")

# 檢查日誌設定
print(f"\n📝 日誌設定:")
logging_config = getattr(settings, 'LOGGING', {})
if logging_config:
    print("  LOGGING 已設定")
    if 'handlers' in logging_config:
        for handler_name, handler_config in logging_config.get('handlers', {}).items():
            print(f"    - {handler_name}: {handler_config.get('level', '未設定')}")
else:
    print("  LOGGING 未設定")

print("\n" + "=" * 50)
print("設定檢查完成")