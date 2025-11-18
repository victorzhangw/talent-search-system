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

# 導入模型
from core.models import TestCategory

# 查詢最低分類的劣勢分析內容
categories = TestCategory.objects.all()
for category in categories:
    if category.disadvantage_analysis:
        print(f"分類: {category.name}")
        print(f"劣勢分析內容: {repr(category.disadvantage_analysis)}")
        print("-" * 50)