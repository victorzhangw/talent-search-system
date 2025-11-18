# core/bulk_invitation_views.py

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.db import transaction
from django.utils import timezone
from datetime import timedelta
import uuid
import csv
import logging

from .decorators import enterprise_required
from .models import TestInvitee, TestInvitation, TestProject, TestProjectAssignment
from .purchase_services import log_quota_usage
from .bulk_invitation_forms import BulkInvitationForm, CSVTemplateForm
from utils.email_service import EmailService
from utils.url_shortener import URLShortenerService

logger = logging.getLogger(__name__)

@login_required
@enterprise_required
def bulk_invitation(request):
    """批量邀請頁面"""
    
    if request.method == 'POST':
        form = BulkInvitationForm(request.user, request.POST, request.FILES)
        
        if form.is_valid():
            return process_bulk_invitation(request, form)
    else:
        form = BulkInvitationForm(request.user)
    
    context = {
        'form': form,
        'csv_template_form': CSVTemplateForm(),
    }
    
    return render(request, 'test_management/bulk_invitation.html', context)


def process_bulk_invitation(request, form):
    """處理批量邀請邏輯"""
    
    try:
        with transaction.atomic():
            test_project = form.cleaned_data['test_project']
            expires_in_days = form.cleaned_data['expires_in_days']
            custom_message = form.cleaned_data['custom_message']
            send_immediately = form.cleaned_data['send_immediately']
            skip_duplicates = form.cleaned_data['skip_duplicates']
            
            csv_data = form.get_parsed_data()
            
            assignment = TestProjectAssignment.objects.select_for_update().filter(
                test_project=test_project,
                enterprise_user=request.user
            ).first()

            expires_at = timezone.now() + timedelta(days=expires_in_days)
            
            # 處理結果統計
            stats = {
                'total': len(csv_data),
                'created': 0,
                'updated': 0,
                'skipped': 0,
                'invited': 0,
                'errors': []
            }
            
            created_invitations = []
            
            consumed_slots = 0
            for row_data in csv_data:
                try:
                    # 處理受測者資料
                    invitee_result = process_invitee_data(
                        request.user, row_data, skip_duplicates
                    )
                    
                    if invitee_result['action'] == 'skipped':
                        stats['skipped'] += 1
                        continue
                    elif invitee_result['action'] == 'created':
                        stats['created'] += 1
                    elif invitee_result['action'] == 'updated':
                        stats['updated'] += 1
                    
                    invitee = invitee_result['invitee']
                    
                    # 檢查是否已有相同測驗項目的邀請
                    existing_invitation = TestInvitation.objects.filter(
                        enterprise=request.user,
                        invitee=invitee,
                        test_project=test_project,
                        status__in=['pending', 'in_progress']
                    ).first()
                    
                    if existing_invitation:
                        stats['errors'].append(f'{invitee.name}({invitee.email}) 已有進行中的邀請')
                        continue
                    
                    if assignment and not assignment.has_available_quota(consumed_slots + 1):
                        remaining = assignment.remaining_quota if assignment.remaining_quota is not None else 0
                        stats['errors'].append(f'可用份數不足（剩餘 {remaining} 份），停止後續邀請。')
                        break

                    invitation_code = uuid.uuid4()
                    
                    # 建立邀請
                    invitation = TestInvitation.objects.create(
                        enterprise=request.user,
                        invitee=invitee,
                        test_project=test_project,
                        invitation_code=invitation_code,
                        custom_message=custom_message,
                        expires_at=expires_at,
                        points_consumed=1,
                        status='pending'
                    )
                    
                    # 生成短網址
                    short_url_data = URLShortenerService.generate_short_url(
                        original_url=test_project.test_link,
                        invitation_id=invitation.id
                    )
                    
                    invitation.result_data = {
                        'short_url': short_url_data['short_url'],
                        'short_code': short_url_data['short_code'],
                        'original_url': short_url_data['original_url']
                    }
                    invitation.save()
                    
                    # 更新受測者統計
                    invitee.invited_count += 1
                    invitee.save()
                    
                    created_invitations.append(invitation)
                    stats['invited'] += 1
                    consumed_slots += 1
                    if assignment:
                        assignment.consume_quota()
                        log_quota_usage(
                            assignment=assignment,
                            invitation=invitation,
                            action='consume',
                            created_by=request.user,
                        )

                except Exception as e:
                    logger.error(f"處理受測者 {row_data.get('name', 'Unknown')} 時發生錯誤：{str(e)}")
                    stats['errors'].append(f"{row_data.get('name', 'Unknown')}：{str(e)}")
            # 發送邀請信
            if send_immediately and created_invitations:
                email_stats = send_bulk_invitations(created_invitations)
                stats.update(email_stats)
            
            # 顯示處理結果
            success_message = f"批量邀請處理完成！"
            if stats['invited'] > 0:
                success_message += f" 成功邀請 {stats['invited']} 人"
            if stats['created'] > 0:
                success_message += f"，新增 {stats['created']} 位受測者"
            if stats['updated'] > 0:
                success_message += f"，更新 {stats['updated']} 位受測者"
            if stats['skipped'] > 0:
                success_message += f"，跳過 {stats['skipped']} 位重複受測者"
            
            messages.success(request, success_message)
            
            if stats['errors']:
                error_message = f"發生 {len(stats['errors'])} 個錯誤：" + "；".join(stats['errors'][:5])
                if len(stats['errors']) > 5:
                    error_message += f"...等共{len(stats['errors'])}個錯誤"
                messages.warning(request, error_message)
            
            return redirect('invitation_list')
            
    except Exception as e:
        logger.error(f"批量邀請處理失敗：{str(e)}")
        messages.error(request, f'批量邀請處理失敗：{str(e)}')
        
        return render(request, 'test_management/bulk_invitation.html', {
            'form': form,
            'csv_template_form': CSVTemplateForm(),
        })


def process_invitee_data(enterprise_user, row_data, skip_duplicates):
    """處理單個受測者數據"""
    
    name = row_data.get('name', '').strip()
    email = row_data.get('email', '').strip().lower()
    phone = row_data.get('phone', '').strip()
    position = row_data.get('position', '').strip()
    company = row_data.get('company', '').strip()
    
    # 檢查是否已存在
    existing_invitee = TestInvitee.objects.filter(
        enterprise=enterprise_user,
        email=email
    ).first()
    
    if existing_invitee:
        if skip_duplicates:
            return {'action': 'skipped', 'invitee': existing_invitee}
        else:
            # 更新現有受測者資料
            existing_invitee.name = name
            existing_invitee.phone = phone or existing_invitee.phone
            existing_invitee.position = position or existing_invitee.position
            existing_invitee.company = company or existing_invitee.company
            existing_invitee.save()
            return {'action': 'updated', 'invitee': existing_invitee}
    else:
        # 建立新受測者
        new_invitee = TestInvitee.objects.create(
            enterprise=enterprise_user,
            name=name,
            email=email,
            phone=phone,
            position=position,
            company=company
        )
        return {'action': 'created', 'invitee': new_invitee}


def send_bulk_invitations(invitations):
    """批量發送邀請信"""
    
    email_stats = {
        'email_sent': 0,
        'email_failed': 0
    }
    
    for invitation in invitations:
        try:
            if EmailService.send_test_invitation_email(invitation):
                email_stats['email_sent'] += 1
            else:
                email_stats['email_failed'] += 1
        except Exception as e:
            logger.error(f"發送邀請信失敗 {invitation.invitee.email}：{str(e)}")
            email_stats['email_failed'] += 1
    
    return email_stats


@login_required
@enterprise_required
def download_csv_template(request):
    """下載CSV範本"""
    
    template_type = request.GET.get('type', 'basic')
    
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="bulk_invitation_template_{template_type}.csv"'
    
    # 加入BOM以支援Excel正確顯示中文
    response.write('\ufeff')
    
    writer = csv.writer(response)
    
    if template_type == 'complete':
        writer.writerow(['name', 'email', 'phone', 'position', 'company'])
        writer.writerow(['張三', 'zhang.san@example.com', '0912345678', '軟體工程師', '科技公司'])
        writer.writerow(['李四', 'li.si@example.com', '0987654321', '專案經理', '創新企業'])
    else:
        writer.writerow(['name', 'email'])
        writer.writerow(['張三', 'zhang.san@example.com'])
        writer.writerow(['李四', 'li.si@example.com'])
    
    return response
