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

# 檢查指定的信箱
emails_to_check = [
    
]

print("檢查資料庫中的用戶信箱...")
print("=" * 50)

for email in emails_to_check:
    print(f"\n檢查信箱: {email}")
    users = User.objects.filter(email=email)
    
    if users.exists():
        for user in users:
            print(f"  ✓ 找到用戶:")
            print(f"    ID: {user.id}")
            print(f"    用戶名: {user.username}")
            print(f"    信箱: {user.email}")
            print(f"    用戶類型: {user.user_type}")
            print(f"    是否啟用: {user.is_active}")
            print(f"    註冊時間: {user.date_joined}")
            
            # 檢查個人或企業檔案
            try:
                if user.user_type == 'individual' and hasattr(user, 'individual_profile'):
                    profile = user.individual_profile
                    print(f"    個人檔案存在")
                    # 列出個人檔案的所有欄位
                    for field in profile._meta.fields:
                        field_name = field.name
                        field_value = getattr(profile, field_name, None)
                        if field_value:
                            print(f"      {field_name}: {field_value}")
                elif user.user_type == 'enterprise' and hasattr(user, 'enterprise_profile'):
                    profile = user.enterprise_profile
                    print(f"    企業檔案存在")
                    # 列出企業檔案的重要欄位
                    for field in profile._meta.fields:
                        field_name = field.name
                        field_value = getattr(profile, field_name, None)
                        if field_value and field_name in ['company_name', 'verification_status', 'tax_id']:
                            print(f"      {field_name}: {field_value}")
            except Exception as e:
                print(f"    檔案資訊讀取錯誤: {e}")
            print()
    else:
        print(f"  ✗ 未找到使用此信箱的用戶")

print("\n" + "=" * 50)
print("檢查完成")