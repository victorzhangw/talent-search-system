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

# 更新管理員信箱
old_email = 'obo.ou@dejia.com.tw'
new_email = 'admin@dejia.com'

print("更新管理員信箱...")
print("=" * 50)

try:
    # 先檢查新信箱是否已被使用
    existing_user = User.objects.filter(email=new_email).first()
    if existing_user:
        print(f"❌ 錯誤: 新信箱 '{new_email}' 已被其他用戶使用!")
        print(f"   衝突用戶: {existing_user.username} (ID: {existing_user.id})")
        sys.exit(1)
    
    # 找到管理員帳號
    admin_user = User.objects.get(email=old_email, user_type='admin')
    
    print(f"找到管理員帳號:")
    print(f"  ID: {admin_user.id}")
    print(f"  用戶名: {admin_user.username}")
    print(f"  舊信箱: {admin_user.email}")
    print(f"  用戶類型: {admin_user.user_type}")
    
    # 更新信箱
    admin_user.email = new_email
    admin_user.save()
    
    print(f"\n✅ 成功更新管理員信箱:")
    print(f"  新信箱: {admin_user.email}")
    
    # 驗證更新結果
    updated_user = User.objects.get(id=admin_user.id)
    print(f"  驗證結果: {updated_user.email}")

except User.DoesNotExist:
    print(f"❌ 錯誤: 找不到信箱為 '{old_email}' 的管理員帳號")
except Exception as e:
    print(f"❌ 更新失敗: {e}")

print("\n" + "=" * 50)
print("更新完成")