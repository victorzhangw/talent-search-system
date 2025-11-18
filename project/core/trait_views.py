from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import IntegrityError
from django.db.models import Count, Q, OuterRef, Subquery, IntegerField
from django.db.models.functions import Coalesce
from django.urls import reverse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from urllib.parse import parse_qsl, urlencode

from .models import TestProjectCategoryTrait, Trait


def admin_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if not request.user.is_staff and getattr(request.user, 'user_type', '') != 'admin':
            messages.error(request, '此功能僅限管理員使用')
            return redirect('dashboard')
        return view_func(request, *args, **kwargs)

    return wrapper


@login_required
@admin_required
def trait_list(request):
    search = request.GET.get('search', '').strip()
    scroll_to = request.GET.get('scroll_to', '').strip()

    category_usage_subquery = (
        TestProjectCategoryTrait.objects
        .filter(trait=OuterRef('pk'))
        .values('trait')
        .annotate(total=Count('category_id', distinct=True))
        .values('total')
    )

    traits_qs = (
        Trait.objects.annotate(
            usage_count=Coalesce(
                Subquery(category_usage_subquery, output_field=IntegerField()),
                0,
            )
        )
        .prefetch_related('categories__test_project')
        .order_by('-created_at', '-id')
    )

    if search:
        traits_qs = traits_qs.filter(
            Q(chinese_name__icontains=search) | Q(system_name__icontains=search)
        )

    paginator = Paginator(traits_qs, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    page_offset = page_obj.start_index() - 1 if paginator.count else 0

    query_params = request.GET.copy()
    if 'scroll_to' in query_params:
        query_params = query_params.copy()
        query_params.pop('scroll_to')
    current_query = query_params.urlencode()

    trait_usage_map = {}
    for trait in page_obj.object_list:
        usage_entries = []
        seen_pairs = set()
        for category in trait.categories.all():
            test_project = getattr(category, 'test_project', None)
            if not test_project:
                continue
            key = (test_project.id, category.id)
            if key in seen_pairs:
                continue
            seen_pairs.add(key)
            usage_entries.append({
                'project_name': test_project.name,
                'category_name': category.name or '未命名分類',
                'url': reverse('test_project_edit', args=[test_project.id]),
            })
        trait_usage_map[str(trait.id)] = usage_entries

    context = {
        'page_obj': page_obj,
        'page_offset': page_offset,
        'search': search,
        'trait_usage_map': trait_usage_map,
        'current_query': current_query,
        'scroll_to': scroll_to,
    }
    return render(request, 'admin/trait_list.html', context)


@login_required
@admin_required
def trait_create(request):
    form_data = {}
    form_errors = []
    field_errors = {}
    return_query = request.GET.get('return_query', '')
    if request.method == 'POST':
        return_query = request.POST.get('return_query', return_query)

    if request.method == 'POST':
        chinese_name = request.POST.get('chinese_name', '').strip()
        system_name = request.POST.get('system_name', '').strip()
        description = request.POST.get('description', '').strip()
        form_data = {
            'chinese_name': chinese_name,
            'system_name': system_name,
            'description': description,
        }

        missing_fields = []
        if not chinese_name:
            field_errors['chinese_name'] = '請填寫中文特質名稱'
            missing_fields.append('中文特質名稱')
        if not system_name:
            field_errors['system_name'] = '請填寫系統對應名稱'
            missing_fields.append('系統對應名稱')

        if missing_fields:
            error_msg = '請完整填寫中文名稱與系統名稱'
            form_errors.append(error_msg)
            messages.error(request, error_msg)
        elif Trait.objects.filter(system_name=system_name).exists():
            error_msg = '系統名稱已存在，請使用其他名稱'
            form_errors.append(error_msg)
            field_errors['system_name'] = error_msg
            messages.error(request, error_msg)
        else:
            Trait.objects.create(
                chinese_name=chinese_name,
                system_name=system_name,
                description=description,
            )
            messages.success(request, '特質建立成功')
            return redirect('trait_list')

    if return_query:
        return_url = f"{reverse('trait_list')}?{return_query}"
    else:
        return_url = reverse('trait_list')

    context = {
        'is_edit': False,
        'form_data': form_data,
        'form_errors': form_errors,
        'field_errors': field_errors,
        'return_query': return_query,
        'return_url': return_url,
    }
    return render(request, 'admin/trait_form.html', context)


@login_required
@admin_required
def trait_edit(request, trait_id):
    trait = get_object_or_404(Trait, id=trait_id)
    form_errors = []
    field_errors = {}
    return_query = request.GET.get('return_query', '')
    if request.method == 'POST':
        return_query = request.POST.get('return_query', return_query)

    if request.method == 'POST':
        chinese_name = request.POST.get('chinese_name', '').strip()
        system_name = request.POST.get('system_name', '').strip()
        description = request.POST.get('description', '').strip()

        missing_fields = []
        if not chinese_name:
            field_errors['chinese_name'] = '請填寫中文特質名稱'
            missing_fields.append('中文特質名稱')
        if not system_name:
            field_errors['system_name'] = '請填寫系統對應名稱'
            missing_fields.append('系統對應名稱')

        if missing_fields:
            error_msg = '請完整填寫中文名稱與系統名稱'
            form_errors.append(error_msg)
            messages.error(request, error_msg)
        elif Trait.objects.exclude(id=trait.id).filter(system_name=system_name).exists():
            error_msg = '系統名稱已存在，請使用其他名稱'
            form_errors.append(error_msg)
            field_errors['system_name'] = error_msg
            messages.error(request, error_msg)
        else:
            trait.chinese_name = chinese_name
            trait.system_name = system_name
            trait.description = description
            try:
                trait.save(update_fields=['chinese_name', 'system_name', 'description', 'updated_at'])
            except IntegrityError:
                error_msg = '系統名稱已存在，請使用其他名稱'
                form_errors.append(error_msg)
                field_errors['system_name'] = error_msg
                messages.error(request, error_msg)
            else:
                messages.success(request, '特質更新成功')
                redirect_url = reverse('trait_list')
                query_pairs = []
                if return_query:
                    query_pairs = [
                        (k, v) for k, v in parse_qsl(return_query) if k != 'scroll_to'
                    ]
                query_pairs.append(('scroll_to', str(trait.id)))
                if query_pairs:
                    redirect_url = f"{redirect_url}?{urlencode(query_pairs, doseq=True)}"
                return redirect(redirect_url)

        # 更新 trait 物件以顯示使用者輸入值
        trait.chinese_name = chinese_name
        trait.system_name = system_name
        trait.description = description

    if return_query:
        return_url = f"{reverse('trait_list')}?{return_query}"
    else:
        return_url = reverse('trait_list')

    context = {
        'is_edit': True,
        'trait': trait,
        'form_errors': form_errors,
        'field_errors': field_errors,
        'return_query': return_query,
        'return_url': return_url,
    }
    return render(request, 'admin/trait_form.html', context)


@login_required
@admin_required
@require_POST
def trait_delete(request, trait_id):
    trait = get_object_or_404(Trait, id=trait_id)

    if TestProjectCategoryTrait.objects.filter(trait=trait).exists():
        messages.error(request, '特質已被分類使用，無法刪除')
    else:
        trait.delete()
        messages.success(request, '特質已刪除')

    return redirect('trait_list')
