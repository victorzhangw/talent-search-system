from datetime import datetime
import uuid

from django.db import transaction
from django.utils import timezone

from .models import (
    EnterprisePurchaseRecord,
    EnterpriseQuotaUsageLog,
    TestProjectAssignment,
)


def generate_order_number(prefix='PO'):
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    random_part = uuid.uuid4().hex[:6].upper()
    return f"{prefix}{timestamp}{random_part}"


@transaction.atomic
def record_enterprise_purchase(
    *,
    enterprise_user,
    test_project,
    quantity,
    created_by,
    assignment=None,
    order_number=None,
    payment_date=None,
    payment_method='',
    payment_amount=None,
    invoice_number='',
    invoice_random_code='',
    invoice_info='',
    coupon_code='',
    notes='',
    adjust_assignment=True,
):
    if quantity <= 0:
        raise ValueError('quantity must be positive')

    if payment_date is None:
        payment_date = timezone.now()

    if order_number is None:
        order_number = generate_order_number()

    created_assignment = False
    if assignment is None:
        assignment, created_assignment = TestProjectAssignment.objects.get_or_create(
            test_project=test_project,
            enterprise_user=enterprise_user,
            defaults={
                'assigned_by': created_by,
                'assigned_quota': quantity,
            }
        )
    
    if adjust_assignment:
        if created_assignment:
            # 已透過 defaults 設定初始配額
            pass
        elif assignment.assigned_quota == 0:
            # 無限配額不變
            pass
        else:
            assignment.assigned_quota += quantity
            assignment.save(update_fields=['assigned_quota'])

    record = EnterprisePurchaseRecord.objects.create(
        enterprise_user=enterprise_user,
        test_project=test_project,
        assignment=assignment,
        order_number=order_number,
        quantity=quantity,
        payment_date=payment_date,
        payment_method=payment_method or '',
        payment_amount=payment_amount,
        invoice_number=invoice_number,
        invoice_random_code=invoice_random_code,
        invoice_info=invoice_info,
        coupon_code=coupon_code,
        notes=notes,
        created_by=created_by,
    )

    return record, assignment


def log_quota_usage(
    *,
    assignment,
    invitation,
    action,
    created_by=None,
    quantity=1,
):
    if assignment is None:
        return None

    remaining = assignment.remaining_quota

    invitee_name = ''
    invitee_email = ''
    if invitation is not None:
        if invitation.invitee:
            invitee_name = invitation.invitee.name or ''
            invitee_email = invitation.invitee.email or ''

    return EnterpriseQuotaUsageLog.objects.create(
        assignment=assignment,
        enterprise_user=assignment.enterprise_user,
        test_project=assignment.test_project,
        invitation=invitation,
        action=action,
        quantity=quantity,
        invitee_name=invitee_name,
        invitee_email=invitee_email,
        remaining_quota=remaining if remaining is not None else None,
        created_by=created_by,
    )
