# utils/email_service.py

from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.urls import reverse
from django.utils import timezone
import uuid
import logging

# 設定 logger
logger = logging.getLogger(__name__)

class EmailService:
    @staticmethod
    def send_verification_email(user):
        """發送Email驗證郵件"""
        try:
            # 生成新的驗證令牌
            user.email_verification_token = uuid.uuid4()
            user.save()
            
            # 建立驗證連結
            verification_url = f"{settings.SITE_URL}{reverse('email_verify', kwargs={'token': user.email_verification_token})}"
            
            # 準備郵件內容
            subject = '【Traitty特質評鑑】Email驗證通知'
            
            context = {
                'user': user,
                'verification_url': verification_url,
                'site_name': 'Traitty特質評鑑',
                'header_image_url': f"{settings.SITE_URL}{settings.STATIC_URL}email/emal_header.png?v=2025110401"
            }
            
            html_content = render_to_string('email/verification_email.html', context)
            text_content = f'''
親愛的 {user.username}，您好！

感謝您註冊Traitty特質評鑑！請點擊以下連結驗證您的電子郵件地址：

{verification_url}

如果您沒有註冊此帳號，請忽略此郵件。
            '''
            
            send_mail(
                subject=subject,
                message=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                html_message=html_content,
                fail_silently=False,
            )
            
            logger.info(f"驗證郵件發送成功：{user.email}")
            return True
            
        except Exception as e:
            logger.error(f"驗證郵件發送失敗：{str(e)}")
            return False

    @staticmethod
    def send_password_reset_email(user):
        """發送密碼重設郵件"""
        try:
            # 生成新的密碼重設令牌
            user.password_reset_token = uuid.uuid4()
            user.password_reset_token_created = timezone.now()
            user.save()
            
            # 建立密碼重設連結
            reset_url = f"{settings.SITE_URL}{reverse('password_reset_confirm', kwargs={'token': user.password_reset_token})}"
            
            # 準備郵件內容
            subject = '密碼重設請求 - Traitty特質評鑑'
            
            context = {
                'user': user,
                'reset_url': reset_url,
                'site_name': 'Traitty特質評鑑',
                'expire_hours': 24  # 24小時後過期
            }
            
            html_content = render_to_string('email/password_reset_email.html', context)
            text_content = f'''
親愛的 {user.username}，您好！

我們收到了您的密碼重設請求。請點擊以下連結重設您的密碼：

{reset_url}

此連結將在24小時後失效。

如果您沒有要求重設密碼，請忽略此郵件。

此郵件由系統自動發送，請勿直接回覆。
© 2024 Traitty特質評鑑 - 版權所有
            '''
            
            send_mail(
                subject=subject,
                message=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                html_message=html_content,
                fail_silently=False,
            )
            
            logger.info(f"密碼重設郵件發送成功：{user.email}")
            return True
            
        except Exception as e:
            logger.error(f"密碼重設郵件發送失敗：{str(e)}")
            return False
        
    @staticmethod
    def send_enterprise_approval_email(user, approved=True, reason=''):
        """發送企業審核結果郵件"""
        try:
            enterprise_profile = user.enterprise_profile
            
            if approved:
                subject = '企業審核通過 - Traitty特質評鑑'
                template_name = 'email/enterprise_approved_email.html'
            else:
                subject = '企業審核未通過 - Traitty特質評鑑'
                template_name = 'email/enterprise_rejected_email.html'
            
            context = {
                'user': user,
                'enterprise_profile': enterprise_profile,
                'site_name': 'Traitty特質評鑑',
                'approved': approved,
                'rejection_reason': reason,
                'login_url': f"{settings.SITE_URL}{reverse('login')}"
            }
            
            html_content = render_to_string(template_name, context)
            
            if approved:
                text_content = f'''
親愛的 {enterprise_profile.contact_person}，您好！

恭喜！您的企業註冊申請已通過審核。

公司名稱：{enterprise_profile.company_name}
統一編號：{enterprise_profile.tax_id}

您現在可以登入系統開始使用各項功能。

登入網址：{context["login_url"]}

感謝您選擇Traitty特質評鑑！
                '''
            else:
                text_content = f'''
親愛的 {enterprise_profile.contact_person}，您好！

很抱歉，您的企業註冊申請未通過審核。

公司名稱：{enterprise_profile.company_name}
統一編號：{enterprise_profile.tax_id}
未通過原因：{reason}

如有疑問，請聯繫我們的客服團隊。

Traitty特質評鑑 客服團隊
                '''
            
            send_mail(
                subject=subject,
                message=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                html_message=html_content,
                fail_silently=False,
            )
            
            logger.info(f"企業審核郵件發送成功：{user.email} - {'通過' if approved else '未通過'}")
            return True
            
        except Exception as e:
            logger.error(f"企業審核通知郵件發送失敗：{str(e)}")
            return False

    @staticmethod
    def send_test_invitation_email(invitation):
        """發送測驗邀請郵件"""
        try:
            invitee = invitation.invitee
            project = invitation.test_project
            enterprise = invitation.enterprise
            
            # 獲取短網址
            test_url = invitation.result_data.get('short_url', project.test_link)
            
            subject = f'【{enterprise.enterprise_profile.company_name}】Traitty 特質評鑑邀請'
            
            # 計算剩餘天數
            remaining_days = max(0, (invitation.expires_at - timezone.now()).days)
            
            # 取得企業聯絡電話
            enterprise_phone = enterprise.enterprise_profile.contact_phone
            logger.info(f"企業聯絡電話: '{enterprise_phone}', 企業: {enterprise.enterprise_profile.company_name}")
            
            context = {
                'invitee_name': invitee.name,
                'invitee_email': invitee.email,
                'project_name': project.name,
                'project_description': project.description,
                'enterprise_name': enterprise.enterprise_profile.company_name,
                'test_url': test_url,
                'expires_at': invitation.expires_at,
                'remaining_days': remaining_days,
                'custom_message': invitation.custom_message,
                'invitation_code': invitation.invitation_code,
                'enterprise_contact': enterprise.enterprise_profile.contact_person,
                'enterprise_phone': enterprise_phone or '請聯繫邀請企業',
                'logo': f"{settings.SITE_URL}/static/img/Traitty logo.png",
                'header_image_url': f"{settings.SITE_URL}{settings.STATIC_URL}email/emal_header.png?v=2025110401",
            }
            
            # 使用HTML模板
            html_content = render_to_string('email/test_invitation_email.html', context)
            
            # 純文字版本（與HTML版本對應）
            text_content = f'''親愛的 {invitee.name}，您好！

{enterprise.enterprise_profile.company_name} 誠摯邀請您參加以下測驗：

測驗項目：{project.name}
{f"測驗說明：{project.description}" if project.description else ""}
邀請企業：{enterprise.enterprise_profile.company_name}

{f"特別說明：{invitation.custom_message}" if invitation.custom_message else ""}

開始測驗：{test_url}

測驗截止時間：{invitation.expires_at.strftime('%Y年%m月%d日 %H:%M')}
{f"還有 {remaining_days} 天" if remaining_days > 0 else "即將到期，請盡快完成"}

注意事項：
• 請在測驗截止時間前完成
• 測驗過程中請保持網路連線穩定
• 建議使用電腦或平板進行測驗，以獲得最佳體驗
• 如有技術問題，請聯繫邀請企業

邀請碼（供查詢使用）：{invitation.invitation_code}

{enterprise.enterprise_profile.company_name}
此郵件由Traitty特質評鑑自動發送，請勿直接回覆
如有疑問，請聯繫邀請企業或平台客服'''
            
            send_mail(
                subject=subject,
                message=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[invitee.email],
                html_message=html_content,
                fail_silently=False,
            )
            
            logger.info(f"測驗邀請郵件發送成功：{invitee.email} - {project.name}")
            return True
            
        except Exception as e:
            logger.error(f"測驗邀請郵件發送失敗：{str(e)}")
            return False

    @staticmethod
    def resend_test_invitation_email(invitation):
        """重新發送測驗邀請郵件"""
        try:
            # 檢查邀請是否還有效
            if invitation.status == 'expired':
                logger.warning(f"嘗試重發已過期的邀請：{invitation.id}")
                return False
            
            if invitation.status == 'completed':
                logger.warning(f"嘗試重發已完成的邀請：{invitation.id}")
                return False
            
            # 更新邀請狀態為待執行
            invitation.status = 'pending'
            invitation.save()
            
            # 發送郵件
            success = EmailService.send_test_invitation_email(invitation)
            
            if success:
                logger.info(f"重新發送測驗邀請郵件成功：{invitation.invitee.email}")
            
            return success
            
        except Exception as e:
            logger.error(f"重新發送測驗邀請郵件失敗：{str(e)}")
            return False

    @staticmethod
    def send_test_completion_notification(invitation):
        """發送測驗完成通知郵件（給企業）"""
        try:
            enterprise = invitation.enterprise
            invitee = invitation.invitee
            project = invitation.test_project
            
            subject = f'測驗完成通知 - {invitee.name} 已完成 {project.name}'
            header_image_url = f"{settings.SITE_URL}{settings.STATIC_URL}email/emal_header.png?v=2025110401"

            context = {
                'enterprise_name': enterprise.enterprise_profile.company_name,
                'invitee_name': invitee.name,
                'project_name': project.name,
                'header_image_url': header_image_url,
                'site_url': settings.SITE_URL,
            }

            text_content = f'''
提醒您

{invitee.name} 已完成測驗
請登入 Traitty 查看結果

            '''

            html_content = render_to_string('email/test_completion_notification_email.html', context)

            send_mail(
                subject=subject,
                message=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[enterprise.email],
                html_message=html_content,
                fail_silently=False,
            )
            
            logger.info(f"測驗完成通知郵件發送成功：{enterprise.email} - {invitee.name}")
            return True
            
        except Exception as e:
            logger.error(f"測驗完成通知郵件發送失敗：{str(e)}")
            return False
