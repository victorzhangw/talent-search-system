# core/management/commands/create_individual_test_data.py

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from core.models import TestProject, IndividualTestRecord, IndividualTestResult
from django.utils import timezone
import random
import json

User = get_user_model()

class Command(BaseCommand):
    help = '為個人用戶創建測試測驗結果數據'

    def add_arguments(self, parser):
        parser.add_argument(
            '--username',
            type=str,
            help='指定用戶名稱（默認為 i_obo）',
            default='i_obo'
        )
        parser.add_argument(
            '--with-results',
            action='store_true',
            help='是否創建測驗結果數據',
        )

    def handle(self, *args, **options):
        username = options['username']
        with_results = options['with_results']
        
        try:
            user = User.objects.get(username=username, user_type='individual')
            self.stdout.write(f'找到用戶: {user.username}')
        except User.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'找不到個人用戶: {username}')
            )
            return

        # 獲取可用的測驗項目
        test_projects = TestProject.get_available_projects_for_user(user)
        if not test_projects.exists():
            self.stdout.write(
                self.style.ERROR('沒有可用的測驗項目')
            )
            return

        # 為每個測驗項目創建記錄
        for project in test_projects:
            record, created = IndividualTestRecord.objects.get_or_create(
                user=user,
                test_project=project,
                defaults={
                    'status': 'in_progress',
                    'points_consumed': 1,
                    'access_count': random.randint(1, 5)
                }
            )
            
            if created:
                self.stdout.write(f'創建測驗記錄: {project.name}')
                
                # 模擬一些進入記錄
                record.mark_accessed()
                
            # 如果需要創建結果數據
            if with_results and not record.has_result():
                self.create_test_result(record)

    def create_test_result(self, record):
        """創建模擬的測驗結果數據"""
        
        # 模擬分類結果（基於企業系統的結構）
        categories = {
            '領導力': {
                'score': round(random.uniform(2.0, 5.0), 1),
                'description': '展現出良好的領導潛能，能夠在團隊中發揮指導作用。'
            },
            '溝通協調': {
                'score': round(random.uniform(2.0, 5.0), 1),
                'description': '具備優秀的溝通技巧，能夠有效協調團隊合作。'
            },
            '創新思維': {
                'score': round(random.uniform(2.0, 5.0), 1),
                'description': '思維靈活，善於提出創新的解決方案。'
            },
            '抗壓能力': {
                'score': round(random.uniform(2.0, 5.0), 1),
                'description': '面對壓力時能保持冷靜，具備良好的抗壓能力。'
            },
            '學習適應': {
                'score': round(random.uniform(2.0, 5.0), 1),
                'description': '學習能力強，能夠快速適應新環境和挑戰。'
            }
        }
        
        # 模擬特質結果
        traits = {
            '外向性': round(random.uniform(1.0, 5.0), 1),
            '親和性': round(random.uniform(1.0, 5.0), 1),
            '責任心': round(random.uniform(1.0, 5.0), 1),
            '情緒穩定性': round(random.uniform(1.0, 5.0), 1),
            '開放性': round(random.uniform(1.0, 5.0), 1)
        }
        
        # 計算整體分數
        overall_score = sum(cat['score'] for cat in categories.values()) / len(categories)
        
        # 模擬原始數據
        raw_data = {
            'test_id': f'test_{record.id}_{random.randint(1000, 9999)}',
            'completion_time': '2024-07-15 14:30:00',
            'total_questions': 120,
            'responses': [random.randint(1, 5) for _ in range(120)],
            'metadata': {
                'browser': 'Chrome',
                'platform': 'Web',
                'duration_minutes': random.randint(15, 45)
            }
        }
        
        # 創建測驗結果
        result = IndividualTestResult.objects.create(
            individual_test_record=record,
            test_project=record.test_project,
            user=record.user,
            score_value=round(overall_score, 2),
            prediction_value=self.generate_prediction(categories),
            category_results=categories,
            trait_results=traits,
            raw_data=raw_data,
            processed_data={
                'analysis_version': '1.0',
                'processed_at': timezone.now().isoformat(),
                'categories': categories,
                'traits': traits
            },
            test_completion_date=timezone.now() - timezone.timedelta(
                days=random.randint(1, 30)
            ),
            external_test_id=f'ext_{random.randint(10000, 99999)}',
            result_status='completed'
        )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'創建測驗結果: {record.test_project.name} (分數: {overall_score:.2f})'
            )
        )
        
        return result
    
    def generate_prediction(self, categories):
        """根據分類結果生成預測描述"""
        highest_category = max(categories.items(), key=lambda x: x[1]['score'])
        lowest_category = min(categories.items(), key=lambda x: x[1]['score'])
        
        prediction = f"""基於您的測驗結果分析：

優勢領域：
• {highest_category[0]}表現突出（{highest_category[1]['score']}/5.0），{highest_category[1]['description']}

發展建議：
• 建議加強{lowest_category[0]}方面的能力（{lowest_category[1]['score']}/5.0）
• 可透過相關訓練課程或實務經驗來提升此領域表現

整體評估：
您展現出均衡的人格特質組合，具備良好的發展潛力。建議持續發揮優勢領域的能力，
同時針對較弱的領域進行有針對性的改善。"""
        
        return prediction