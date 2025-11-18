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

# 企業資訊
target_email = 'obo.ou@dejia.com.tw'
target_username = 'obo.ou'
target_company = '台灣普德股份有限公司'
target_tax_id = '54536515'

print("重設企業審核狀態...")
print("=" * 50)

try:
    # 先嘗試用信箱找用戶
    user = None
    try:
        user = User.objects.get(email=target_email, user_type='enterprise')
        print(f"✓ 透過信箱找到企業用戶")
    except User.DoesNotExist:
        print(f"未找到信箱為 {target_email} 的企業用戶")
        
        # 嘗試用用戶名找
        try:
            user = User.objects.get(username=target_username, user_type='enterprise')
            print(f"✓ 透過用戶名找到企業用戶")
        except User.DoesNotExist:
            print(f"未找到用戶名為 {target_username} 的企業用戶")
    
    if not user:
        # 嘗試用統編找
        from core.models import EnterpriseProfile
        try:
            enterprise_profile = EnterpriseProfile.objects.get(tax_id=target_tax_id)
            user = enterprise_profile.user
            print(f"✓ 透過統編找到企業用戶")
        except EnterpriseProfile.DoesNotExist:
            print(f"未找到統編為 {target_tax_id} 的企業檔案")
    
    if not user:
        print("❌ 無法找到指定的企業用戶")
        sys.exit(1)
    
    enterprise_profile = user.enterprise_profile
    
    print(f"\n找到企業用戶:")
    print(f"  ID: {user.id}")
    print(f"  用戶名: {user.username}")
    print(f"  信箱: {user.email}")
    print(f"  公司名稱: {enterprise_profile.company_name}")
    print(f"  統一編號: {enterprise_profile.tax_id}")
    print(f"  當前狀態: {enterprise_profile.verification_status}")
    print(f"  是否啟用: {user.is_active}")
    print(f"  審核時間: {enterprise_profile.verified_at}")
    
    # 確認是否要重設
    if enterprise_profile.verification_status == 'pending':
        print(f"\n⚠️  該企業已經是待審核狀態")
    else:
        print(f"\n🔄 重設審核狀態...")
        
        # 重設為待審核狀態
        enterprise_profile.verification_status = 'pending'
        enterprise_profile.verified_at = None
        enterprise_profile.save()
        
        # 設為非啟用狀態
        user.is_active = False
        user.save()
        
        print(f"✅ 成功重設企業審核狀態:")
        print(f"  審核狀態: {enterprise_profile.verification_status}")
        print(f"  用戶啟用: {user.is_active}")
        print(f"  審核時間: {enterprise_profile.verified_at}")
        
except Exception as e:
    print(f"❌ 重設失敗: {e}")

print("\n" + "=" * 50)
print("重設完成")