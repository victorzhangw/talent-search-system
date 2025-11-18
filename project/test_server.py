#!/usr/bin/env python
"""測試伺服器啟動"""

import os
import sys
import django
from django.conf import settings
from django.test.utils import get_runner

if __name__ == "__main__":
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')
    
    try:
        django.setup()
        print("✅ Django 設定成功！")
        
        # 測試各個模組的導入
        print("🔍 測試模組導入...")
        
        # 測試 core 模組
        from core.models import User, TestProject
        print("  ✅ core 模組導入成功")
        
        # 測試 API 模組
        from api.views import UserRegistrationView
        print("  ✅ API 模組導入成功")
        
        # 測試 REST framework
        from rest_framework.views import APIView
        print("  ✅ REST Framework 導入成功")
        
        # 測試 JWT
        from rest_framework_simplejwt.tokens import RefreshToken
        print("  ✅ JWT 導入成功")
        
        # 測試 CORS
        import corsheaders
        print("  ✅ CORS 導入成功")
        
        # 測試 Django Filter
        import django_filters
        print("  ✅ Django Filter 導入成功")
        
        # 測試 Rate Limit
        from django_ratelimit.decorators import ratelimit
        print("  ✅ Rate Limit 導入成功")
        
        print("\n🎉 所有模組測試通過！")
        print("📝 您可以安全地運行 'python manage.py runserver'")
        
    except Exception as e:
        print(f"❌ 錯誤: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)