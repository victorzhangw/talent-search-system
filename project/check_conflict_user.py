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
from django.contrib.auth import get_user_model
User = get_user_model()

# 檢查衝突用戶
conflict_email = 'ouborhorng@gmail.com'

print(f"檢查使用信箱 '{conflict_email}' 的用戶...")
print("=" * 50)

try:
    user = User.objects.get(email=conflict_email)
    
    print(f"用戶詳情:")
    print(f"  ID: {user.id}")
    print(f"  用戶名: {user.username}")
    print(f"  信箱: {user.email}")
    print(f"  用戶類型: {user.user_type}")
    print(f"  是否啟用: {user.is_active}")
    print(f"  註冊時間: {user.date_joined}")
    print(f"  最後登入: {user.last_login}")
    
    # 檢查是否有相關檔案
    if user.user_type == 'individual' and hasattr(user, 'individual_profile'):
        print(f"  個人檔案: 存在")
    elif user.user_type == 'enterprise' and hasattr(user, 'enterprise_profile'):
        print(f"  企業檔案: 存在")
    
    print(f"\n建議處理方式:")
    if not user.is_active or user.last_login is None:
        print(f"  ✅ 該用戶似乎未曾使用，可以安全刪除")
    else:
        print(f"  ⚠️  該用戶有登入記錄，建議謹慎處理")

except User.DoesNotExist:
    print(f"未找到使用此信箱的用戶")

print("\n" + "=" * 50)