# core/tasks.py
from celery import shared_task
from django.utils import timezone
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)

@shared_task
def crawl_test_result_async(invitation_id):
    '''異步爬取測驗結果'''
    try:
        from utils.crawler_service import PITestResultCrawler
        
        crawler = PITestResultCrawler()
        result = crawler.crawl_test_result(invitation_id)
        
        # 檢查返回值類型和內容
        if isinstance(result, dict):
            # 直接返回爬蟲的字典結果
            return result
        elif result:
            # 傳統的 TestProjectResult 物件返回
            return {
                'success': True,
                'result_id': result.id,
                'message': '爬取完成'
            }
        else:
            return {
                'success': False,
                'message': '爬取完成但無結果資料'
            }
    except Exception as e:
        logger.error(f"異步爬取失敗：{str(e)}")
        return {
            'success': False,
            'error': str(e)
        }

@shared_task
def crawl_all_pending_results():
    '''批量爬取所有待處理的測驗結果'''
    from core.models import CrawlerLog, CrawlerDetailLog, TestInvitation
    
    # 先創建日誌記錄，確保無論如何都有記錄
    main_log = CrawlerLog.objects.create(
        task_name='crawl_all_pending_results',
        status='running',
        success_count=0,
        fail_count=0,
        total_count=0,
        executed_at=timezone.now(),
        message="爬蟲任務開始執行..."
    )
    
    try:
        from utils.crawler_service import PITestResultCrawler
        
        logger.info("開始執行定期爬蟲任務")
        
        # 查找所有已完成或進行中但未爬取的邀請
        pending_invitations = TestInvitation.objects.filter(
            status__in=['completed', 'in_progress'],
            test_project__isnull=False
        ).exclude(
            testprojectresult__crawl_status='completed'
        )
        
        # 更新日誌記錄的總數
        main_log.total_count = pending_invitations.count()
        main_log.message = f"找到 {pending_invitations.count()} 個待爬取的邀請"
        main_log.save()
        
        crawler = PITestResultCrawler()
        success_count = 0
        fail_count = 0
        
        logger.info(f"找到 {pending_invitations.count()} 個待爬取的邀請")
        
        for invitation in pending_invitations:
            start_time = timezone.now()
            detail_log = None
            
            try:
                # 創建詳細日誌記錄
                detail_log = CrawlerDetailLog.objects.create(
                    crawler_log=main_log,
                    test_invitation=invitation,
                    invitee_name=invitation.invitee.name,
                    invitee_email=invitation.invitee.email,
                    test_project_name=invitation.test_project.name,
                    status='failed',  # 預設為失敗，成功時會更新
                    executed_at=start_time
                )
                
                result = crawler.crawl_test_result(invitation.id)
                execution_time = (timezone.now() - start_time).total_seconds()
                
                # 檢查返回值類型和內容
                if isinstance(result, dict):
                    # 處理字典返回值（包括 CI 檢查失敗的情況）
                    if result.get('success') == False and result.get('status') == 'incomplete_test':
                        # 測驗未完成，不算失敗，保持待處理狀態
                        detail_log.status = 'incomplete'
                        detail_log.error_message = result.get('message', '測驗尚未完成')
                        logger.info(f"邀請 {invitation.id} 測驗尚未完成，保持待處理狀態")
                        # 不增加 success_count 或 fail_count
                    elif result.get('success') == True:
                        success_count += 1
                        detail_log.status = 'success'
                        detail_log.data_found = True
                        logger.info(f"成功爬取邀請 {invitation.id}")
                    else:
                        fail_count += 1
                        detail_log.error_message = result.get('message', '爬取失敗')
                        logger.error(f"爬取邀請 {invitation.id} 失敗: {result.get('message')}")
                elif result:
                    # 傳統的 TestProjectResult 物件返回
                    success_count += 1
                    detail_log.status = 'success'
                    detail_log.data_found = True
                    detail_log.crawled_data_size = len(str(result.raw_data)) if hasattr(result, 'raw_data') else 0
                    logger.info(f"成功爬取邀請 {invitation.id}")
                else:
                    fail_count += 1
                    detail_log.error_message = "爬取成功但無結果資料"
                    logger.warning(f"爬取邀請 {invitation.id} 無結果")
                
                detail_log.execution_time = execution_time
                detail_log.save()
                
            except Exception as e:
                fail_count += 1
                execution_time = (timezone.now() - start_time).total_seconds()
                error_msg = str(e)
                
                logger.error(f"爬取邀請 {invitation.id} 失敗：{error_msg}")
                
                if detail_log:
                    detail_log.status = 'failed'
                    detail_log.error_message = error_msg
                    detail_log.execution_time = execution_time
                    detail_log.error_details = {
                        'error_type': type(e).__name__,
                        'error_message': error_msg,
                        'invitation_id': invitation.id,
                        'invitation_status': invitation.status
                    }
                    detail_log.save()
        
        # 更新主日誌記錄
        main_log.status = 'completed'
        main_log.success_count = success_count
        main_log.fail_count = fail_count
        main_log.message = f"成功: {success_count}, 失敗: {fail_count}, 總計: {pending_invitations.count()}"
        main_log.save()
        
        return {
            'success': True,
            'total': pending_invitations.count(),
            'success_count': success_count,
            'fail_count': fail_count,
            'message': f'定期爬蟲任務完成: 成功 {success_count}, 失敗 {fail_count}'
        }
        
    except Exception as e:
        # 確保即使發生嚴重異常也會更新日誌記錄
        logger.error(f"定期爬蟲任務失敗：{str(e)}")
        
        try:
            main_log.status = 'failed'
            main_log.message = f"任務執行失敗: {str(e)}"
            main_log.error_details = str(e)
            main_log.save()
        except Exception as log_error:
            logger.error(f"無法更新日誌記錄：{str(log_error)}")
        
        return {
            'success': False,
            'error': str(e)
        }

@shared_task
def cleanup_old_crawl_logs():
    '''清理舊的爬蟲日誌記錄'''
    try:
        from core.models import CrawlerLog
        
        # 刪除30天前的日誌記錄
        cutoff_date = timezone.now() - timedelta(days=30)
        deleted_count = CrawlerLog.objects.filter(
            executed_at__lt=cutoff_date
        ).delete()[0]
        
        logger.info(f"清理了 {deleted_count} 筆舊的爬蟲日誌記錄")
        
        return {
            'success': True,
            'deleted_count': deleted_count,
            'message': f'清理了 {deleted_count} 筆舊記錄'
        }
        
    except Exception as e:
        logger.error(f"清理舊日誌失敗：{str(e)}")
        return {
            'success': False,
            'error': str(e)
        }

@shared_task
def force_recrawl_test_result(invitation_id):
    '''強制重新爬取測驗結果（管理員專用）'''
    try:
        from core.models import TestInvitation, TestProjectResult
        from utils.crawler_service import PITestResultCrawler
        
        logger.info(f"開始強制重新爬取測驗結果，邀請ID: {invitation_id}")
        
        # 獲取測驗邀請
        test_invitation = TestInvitation.objects.select_related('test_project', 'invitee').get(
            id=invitation_id
        )
        
        # 重置或創建測驗結果記錄
        test_result, created = TestProjectResult.objects.get_or_create(
            test_invitation=test_invitation,
            defaults={
                'test_project': test_invitation.test_project,
                'crawl_status': 'crawling',
                'crawled_at': timezone.now()
            }
        )
        
        if not created:
            # 如果已存在，重置狀態
            test_result.crawl_status = 'crawling'
            test_result.crawled_at = timezone.now()
            test_result.raw_data = {}  # 設為空字典而不是 None
            test_result.processed_data = {}  # 設為空字典而不是 None
            test_result.save()
        
        # 執行爬蟲
        crawler = PITestResultCrawler()
        result = crawler.crawl_test_result(invitation_id)
        
        return {
            'success': True,
            'result_id': result.id if result else None,
            'message': '強制重新爬取完成'
        }
        
    except Exception as e:
        logger.error(f"強制重新爬取失敗：{str(e)}")
        
        # 更新失敗狀態
        try:
            test_result = TestProjectResult.objects.filter(
                test_invitation_id=invitation_id
            ).first()
            if test_result:
                test_result.crawl_status = 'failed'
                test_result.save()
        except:
            pass
            
        return {
            'success': False,
            'error': str(e)
        }

@shared_task
def manual_crawl():
    '''手動爬取任務（可用於測試或特殊情況）'''
    try:
        from core.models import CrawlerLog
        
        # 記錄手動執行
        log = CrawlerLog.objects.create(
            task_name='manual_crawl',
            status='running',
            message='手動爬取任務開始執行'
        )
        
        start_time = timezone.now()
        
        # 這裡可以放入手動爬取的邏輯
        # 例如：特定的爬取任務或測試
        
        # 模擬執行時間
        import time
        time.sleep(2)
        
        # 更新日誌狀態
        duration = timezone.now() - start_time
        log.status = 'completed'
        log.duration = duration
        log.success_count = 1
        log.total_count = 1
        log.message = '手動爬取任務執行完成'
        log.save()
        
        logger.info("手動爬取任務執行完成")
        
        return {
            'success': True,
            'message': '手動爬取任務執行完成'
        }
        
    except Exception as e:
        # 如果日誌已創建，更新錯誤狀態
        if 'log' in locals():
            log.status = 'failed'
            log.error_details = str(e)
            log.save()
        
        logger.error(f"手動爬取任務失敗：{str(e)}")
        return {
            'success': False,
            'error': str(e)
        }