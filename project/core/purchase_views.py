from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils import timezone

from .purchase_forms import EnterprisePurchaseRecordForm
from .purchase_services import record_enterprise_purchase, generate_order_number
from .models import EnterprisePurchaseRecord, TestProjectAssignment, User


def admin_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if not (request.user.is_staff or request.user.user_type == 'admin'):
            messages.error(request, '此功能僅限管理員使用')
            return redirect('dashboard')
        return view_func(request, *args, **kwargs)

    return wrapper


@login_required
@admin_required
def purchase_record_create(request):
    initial = {
        'order_number': generate_order_number(),
        'payment_date': timezone.now().strftime('%Y-%m-%d %H:%M:%S'),
    }

    if request.method == 'POST':
        form = EnterprisePurchaseRecordForm(request.POST)
        if form.is_valid():
            enterprise_user = form.cleaned_data['enterprise_user']
            test_project = form.cleaned_data['test_project']
            quantity = form.cleaned_data['quantity']

            try:
                record_enterprise_purchase(
                    enterprise_user=enterprise_user,
                    test_project=test_project,
                    quantity=quantity,
                    created_by=request.user,
                    order_number=form.cleaned_data['order_number'],
                    payment_date=form.cleaned_data['payment_date'],
                    payment_method=form.cleaned_data['payment_method'],
                    payment_amount=form.cleaned_data['payment_amount'],
                    invoice_number=form.cleaned_data['invoice_number'],
                    invoice_random_code=form.cleaned_data['invoice_random_code'],
                    invoice_info=form.cleaned_data['invoice_info'],
                    coupon_code=form.cleaned_data['coupon_code'],
                    notes=form.cleaned_data['notes'],
                )
            except Exception as exc:
                messages.error(request, f'儲存失敗：{exc}')
            else:
                messages.success(request, '購買紀錄已建立並追加企業可用份數')
                return redirect('purchase_record_create')
    else:
        form = EnterprisePurchaseRecordForm(initial=initial)

    context = {
        'form': form,
    }
    return render(request, 'admin/purchase_record_form.html', context)
