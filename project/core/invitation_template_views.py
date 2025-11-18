# core/invitation_template_views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db import transaction
from django.core.paginator import Paginator
from django.views.decorators.http import require_POST
from django.urls import reverse
from .decorators import enterprise_required
from .models import InvitationTemplate
from django.forms import ModelForm
from django import forms
import logging

logger = logging.getLogger(__name__)

class InvitationTemplateForm(ModelForm):
    """邀請模板表單"""
    
    class Meta:
        model = InvitationTemplate
        fields = ['name', 'template_type', 'subject_template', 'message_template', 'is_default']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '輸入模板名稱'
            }),
            'template_type': forms.Select(attrs={
                'class': 'form-select'
            }),
            'subject_template': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '郵件主旨模板'
            }),
            'message_template': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 10,
                'placeholder': '郵件內容模板'
            }),
            'is_default': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            })
        }
    
    def __init__(self, enterprise_user=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.enterprise_user = enterprise_user
        
        # 添加幫助文字
        self.fields['subject_template'].help_text = '可用變數：{invitee_name}, {enterprise_name}, {test_name}, {company_name}'
        self.fields['message_template'].help_text = '可用變數：{invitee_name}, {enterprise_name}, {test_name}, {company_name}, {test_url}, {expires_date}'
    
    def save(self, commit=True):
        template = super().save(commit=False)
        template.enterprise = self.enterprise_user
        
        if commit:
            # 如果設為預設模板，先取消其他預設模板
            if template.is_default:
                InvitationTemplate.objects.filter(
                    enterprise=self.enterprise_user,
                    is_default=True
                ).update(is_default=False)
            
            template.save()
        return template

@login_required
@enterprise_required
def invitation_template_list(request):
    """邀請模板列表"""
    templates = InvitationTemplate.objects.filter(
        enterprise=request.user,
        is_active=True
    ).order_by('-is_default', '-last_used_at', '-created_at')
    
    # 分頁
    paginator = Paginator(templates, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # 統計資訊
    stats = {
        'total_templates': templates.count(),
        'default_template': templates.filter(is_default=True).first(),
        'most_used': templates.filter(usage_count__gt=0).order_by('-usage_count').first(),
    }
    
    context = {
        'page_obj': page_obj,
        'stats': stats,
    }
    
    return render(request, 'test_management/invitation_template_list.html', context)

@login_required
@enterprise_required
def invitation_template_create(request):
    """建立邀請模板"""
    if request.method == 'POST':
        form = InvitationTemplateForm(enterprise_user=request.user, data=request.POST)
        if form.is_valid():
            template = form.save()
            messages.success(request, f'模板「{template.name}」建立成功！')
            return redirect('invitation_template_list')
    else:
        form = InvitationTemplateForm(enterprise_user=request.user)
    
    context = {
        'form': form,
        'action': 'create',
        'title': '建立邀請模板',
    }
    
    return render(request, 'test_management/invitation_template_form.html', context)

@login_required
@enterprise_required
def invitation_template_edit(request, template_id):
    """編輯邀請模板"""
    template = get_object_or_404(
        InvitationTemplate,
        id=template_id,
        enterprise=request.user,
        is_active=True
    )
    
    if request.method == 'POST':
        form = InvitationTemplateForm(
            enterprise_user=request.user,
            data=request.POST,
            instance=template
        )
        if form.is_valid():
            template = form.save()
            messages.success(request, f'模板「{template.name}」更新成功！')
            return redirect('invitation_template_list')
    else:
        form = InvitationTemplateForm(enterprise_user=request.user, instance=template)
    
    context = {
        'form': form,
        'template': template,
        'action': 'edit',
        'title': f'編輯模板 - {template.name}',
    }
    
    return render(request, 'test_management/invitation_template_form.html', context)

@login_required
@enterprise_required
def invitation_template_detail(request, template_id):
    """邀請模板詳情"""
    template = get_object_or_404(
        InvitationTemplate,
        id=template_id,
        enterprise=request.user,
        is_active=True
    )
    
    # 示範渲染內容
    sample_context = {
        'invitee_name': '張三',
        'enterprise_name': request.user.enterprise_profile.company_name if hasattr(request.user, 'enterprise_profile') else '您的企業',
        'test_name': 'PI人格特質測驗',
        'company_name': '科技公司',
        'test_url': 'https://example.com/test/abc123',
        'expires_date': '2025年01月15日',
    }
    
    context = {
        'template': template,
        'sample_subject': template.render_subject(sample_context),
        'sample_message': template.render_message(sample_context),
        'sample_context': sample_context,
    }
    
    return render(request, 'test_management/invitation_template_detail.html', context)

@login_required
@enterprise_required
@require_POST
def invitation_template_delete(request, template_id):
    """刪除邀請模板"""
    template = get_object_or_404(
        InvitationTemplate,
        id=template_id,
        enterprise=request.user,
        is_active=True
    )
    
    # 檢查是否為預設模板
    if template.is_default:
        return JsonResponse({
            'success': False,
            'message': '無法刪除預設模板，請先設定其他模板為預設。'
        })
    
    template_name = template.name
    template.is_active = False
    template.save()
    
    return JsonResponse({
        'success': True,
        'message': f'模板「{template_name}」已刪除。'
    })

@login_required
@enterprise_required
@require_POST
def invitation_template_set_default(request, template_id):
    """設定為預設模板"""
    template = get_object_or_404(
        InvitationTemplate,
        id=template_id,
        enterprise=request.user,
        is_active=True
    )
    
    try:
        template.set_as_default()
        return JsonResponse({
            'success': True,
            'message': f'已將「{template.name}」設為預設模板。'
        })
    except Exception as e:
        logger.error(f"設定預設模板失敗：{str(e)}")
        return JsonResponse({
            'success': False,
            'message': '設定預設模板失敗，請稍後再試。'
        })

@login_required
@enterprise_required
def invitation_template_preview(request, template_id):
    """預覽模板渲染效果"""
    template = get_object_or_404(
        InvitationTemplate,
        id=template_id,
        enterprise=request.user,
        is_active=True
    )
    
    # 獲取預覽參數
    invitee_name = request.GET.get('invitee_name', '張三')
    test_name = request.GET.get('test_name', 'PI人格特質測驗')
    company_name = request.GET.get('company_name', '科技公司')
    
    # 構建渲染內容
    context = {
        'invitee_name': invitee_name,
        'enterprise_name': request.user.enterprise_profile.company_name if hasattr(request.user, 'enterprise_profile') else '您的企業',
        'test_name': test_name,
        'company_name': company_name,
        'test_url': 'https://example.com/test/abc123',
        'expires_date': '2025年01月15日',
    }
    
    return JsonResponse({
        'success': True,
        'subject': template.render_subject(context),
        'message': template.render_message(context),
    })

@login_required
@enterprise_required
def create_default_templates(request):
    """為企業建立預設模板"""
    if request.method == 'POST':
        try:
            created_templates = InvitationTemplate.create_default_templates(request.user)
            if created_templates:
                template_names = [t.name for t in created_templates]
                messages.success(
                    request, 
                    f'成功建立 {len(created_templates)} 個預設模板：{", ".join(template_names)}'
                )
            else:
                messages.info(request, '預設模板已存在，無需重複建立。')
        except Exception as e:
            logger.error(f"建立預設模板失敗：{str(e)}")
            messages.error(request, '建立預設模板失敗，請稍後再試。')
    
    return redirect('invitation_template_list')

@login_required
@enterprise_required
def invitation_template_copy(request, template_id):
    """複製模板"""
    original_template = get_object_or_404(
        InvitationTemplate,
        id=template_id,
        enterprise=request.user,
        is_active=True
    )
    
    if request.method == 'POST':
        # 建立複製
        new_template = InvitationTemplate.objects.create(
            enterprise=request.user,
            name=f"{original_template.name} - 副本",
            template_type='custom',
            subject_template=original_template.subject_template,
            message_template=original_template.message_template,
            is_default=False,
            is_active=True
        )
        
        messages.success(request, f'模板「{new_template.name}」複製成功！')
        return redirect('invitation_template_edit', template_id=new_template.id)
    
    return redirect('invitation_template_detail', template_id=template_id)