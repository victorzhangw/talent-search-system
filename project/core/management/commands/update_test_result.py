from django.core.management.base import BaseCommand
from datetime import datetime
from django.utils import timezone
import pytz
from core.models import TestProjectResult


class Command(BaseCommand):
    help = '更新測驗結果的完成時間'

    def add_arguments(self, parser):
        parser.add_argument('--id', type=int, required=True, help='測驗結果ID')
        parser.add_argument('--datetime', type=str, required=True, help='完成時間 (格式: 2025-05-08 09:12:41)')

    def handle(self, *args, **options):
        result_id = options['id']
        datetime_str = options['datetime']
        
        try:
            # 解析日期時間並設定為台灣時區
            naive_datetime = datetime.strptime(datetime_str, '%Y-%m-%d %H:%M:%S')
            taiwan_tz = pytz.timezone('Asia/Taipei')
            completed_time = taiwan_tz.localize(naive_datetime)
            
            # 查找測驗結果
            result = TestProjectResult.objects.get(id=result_id)
            
            self.stdout.write(f'找到測驗結果: ID={result.id}')
            self.stdout.write(f'對應的邀請: {result.test_invitation}')
            self.stdout.write(f'目前完成時間: {result.test_invitation.completed_at}')
            
            # 更新完成時間
            result.test_invitation.completed_at = completed_time
            result.test_invitation.save()
            
            self.stdout.write(self.style.SUCCESS(f'✅ 成功更新完成時間為: {completed_time} (台灣時區)'))
            
        except TestProjectResult.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'❌ 找不到 ID={result_id} 的測驗結果'))
        except ValueError as e:
            self.stdout.write(self.style.ERROR(f'❌ 日期格式錯誤: {e}'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ 發生錯誤: {e}'))