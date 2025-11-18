# core/management/commands/cleanup_individual_test_data.py

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from core.models import IndividualTestRecord, IndividualTestResult
from django.db import transaction

User = get_user_model()

class Command(BaseCommand):
    help = '清理個人用戶的測試數據，只保留真實的測驗記錄'

    def add_arguments(self, parser):
        parser.add_argument(
            '--username',
            type=str,
            help='指定用戶名稱（默認為 i_obo）',
            default='i_obo'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='模擬運行，不實際刪除數據',
        )
        parser.add_argument(
            '--keep-purchased',
            action='store_true',
            help='保留已購買的記錄，只清理結果數據',
        )

    def handle(self, *args, **options):
        username = options['username']
        dry_run = options['dry_run']
        keep_purchased = options['keep_purchased']
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('⚠️  模擬運行模式 - 不會實際刪除數據')
            )
        
        try:
            user = User.objects.get(username=username, user_type='individual')
            self.stdout.write(f'找到用戶: {user.username}')
        except User.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'找不到個人用戶: {username}')
            )
            return

        # 獲取用戶的所有測驗記錄
        test_records = IndividualTestRecord.objects.filter(user=user)
        test_results = IndividualTestResult.objects.filter(user=user)
        
        self.stdout.write(f'找到 {test_records.count()} 個測驗記錄')
        self.stdout.write(f'找到 {test_results.count()} 個測驗結果')
        
        if not dry_run:
            with transaction.atomic():
                if keep_purchased:
                    # 只刪除測驗結果，保留購買記錄
                    deleted_results = test_results.delete()
                    self.stdout.write(
                        self.style.SUCCESS(f'✅ 已刪除 {deleted_results[0]} 個測驗結果')
                    )
                    
                    # 重置測驗記錄狀態為已購買
                    updated_records = test_records.update(
                        status='purchased',
                        access_count=0,
                        last_access_date=None,
                        first_access_date=None
                    )
                    self.stdout.write(
                        self.style.SUCCESS(f'✅ 已重置 {updated_records} 個測驗記錄狀態')
                    )
                    
                else:
                    # 刪除所有測驗記錄和結果
                    deleted_results = test_results.delete()
                    deleted_records = test_records.delete()
                    
                    self.stdout.write(
                        self.style.SUCCESS(f'✅ 已刪除 {deleted_results[0]} 個測驗結果')
                    )
                    self.stdout.write(
                        self.style.SUCCESS(f'✅ 已刪除 {deleted_records[0]} 個測驗記錄')
                    )
                    
        else:
            # 模擬運行，顯示會執行的操作
            self.stdout.write('\n📋 將要執行的操作:')
            
            if keep_purchased:
                self.stdout.write(f'  - 刪除 {test_results.count()} 個測驗結果')
                self.stdout.write(f'  - 重置 {test_records.count()} 個測驗記錄狀態為「已購買」')
            else:
                self.stdout.write(f'  - 刪除 {test_results.count()} 個測驗結果')
                self.stdout.write(f'  - 刪除 {test_records.count()} 個測驗記錄')
            
            self.stdout.write('\n使用 --dry-run=false 來實際執行清理')
            
        # 顯示詳細的記錄信息
        if test_records.exists():
            self.stdout.write('\n📊 測驗記錄詳情:')
            for record in test_records:
                status_color = (
                    self.style.SUCCESS if record.status == 'purchased' 
                    else self.style.WARNING if record.status == 'in_progress'
                    else self.style.ERROR
                )
                
                self.stdout.write(
                    f'  • {record.test_project.name}: '
                    f'{status_color(record.status)} '
                    f'(進入 {record.access_count} 次)'
                )
                
        if test_results.exists():
            self.stdout.write('\n🧪 測驗結果詳情:')
            for result in test_results:
                completion_status = (
                    f'完成於 {result.test_completion_date.strftime("%Y-%m-%d %H:%M")}'
                    if result.test_completion_date
                    else '未完成'
                )
                
                self.stdout.write(
                    f'  • {result.test_project.name}: '
                    f'分數 {result.score_value or "N/A"} - {completion_status}'
                )