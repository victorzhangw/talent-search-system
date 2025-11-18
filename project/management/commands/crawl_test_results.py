from django.core.management.base import BaseCommand
from core.models import TestInvitation
from utils.crawler_service import PITestResultCrawler

class Command(BaseCommand):
    help = '批量爬取測驗結果'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--invitation-ids',
            type=str,
            help='指定要爬取的邀請 ID，用逗號分隔'
        )
        parser.add_argument(
            '--all-completed',
            action='store_true',
            help='爬取所有已完成但未爬取的邀請'
        )
    
    def handle(self, *args, **options):
        crawler = PITestResultCrawler()
        
        if options['invitation_ids']:
            # 爬取指定的邀請
            invitation_ids = options['invitation_ids'].split(',')
            for invitation_id in invitation_ids:
                try:
                    result = crawler.crawl_test_result(int(invitation_id.strip()))
                    self.stdout.write(
                        self.style.SUCCESS(f'成功爬取邀請 {invitation_id}')
                    )
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f'爬取邀請 {invitation_id} 失敗：{str(e)}')
                    )
        
        elif options['all_completed']:
            # 爬取所有已完成但未爬取的邀請
            invitations = TestInvitation.objects.filter(
                status='completed',
                test_project__isnull=False
            ).exclude(
                testprojectresult__crawl_status='completed'
            )
            
            self.stdout.write(f'找到 {invitations.count()} 個待爬取的邀請')
            
            for invitation in invitations:
                try:
                    result = crawler.crawl_test_result(invitation.id)
                    self.stdout.write(
                        self.style.SUCCESS(f'成功爬取邀請 {invitation.id}')
                    )
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f'爬取邀請 {invitation.id} 失敗：{str(e)}')
                    )