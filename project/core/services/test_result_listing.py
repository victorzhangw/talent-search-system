"""Shared utilities for test result listings."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Dict, Any

from django.core.paginator import Paginator
from django.db.models import (
    Q,
    F,
    FloatField,
    Value,
    Case,
    When,
    IntegerField,
)
from django.db.models.functions import Coalesce, Cast
from django.utils import timezone

from core.models import TestInvitation, TestInvitee, TestProject

CRAWL_STATUS_CHOICES = [
    ('pending', '待取得'),
    ('crawling', '取得中'),
    ('completed', '測驗完成'),
    ('failed', '取得失敗'),
]

ORDER_CHOICES = [
    ('completion_desc', '完成時間（由近至遠）'),
    ('completion_asc', '完成時間（由遠至近）'),
    ('score_desc', '分數（由高到低）'),
    ('score_asc', '分數（由低到高）'),
]


@dataclass
class ListingOptions:
    user: Any
    per_page: int = 50
    allow_project_filter: bool = True
    locked_project_id: Optional[int] = None


def _parse_numeric(value):
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        cleaned = value.strip()
        if not cleaned:
            return None
        import re

        match = re.search(r'-?\d+(?:\.\d+)?', cleaned.replace(',', ''))
        if match:
            try:
                return float(match.group(0))
            except ValueError:
                return None
    return None


def _extract_prediction(invitation):
    result = getattr(invitation, 'testprojectresult', None)
    if not result:
        return None

    project = invitation.test_project
    prediction_key = (getattr(project, 'prediction_field_system', '') or '').strip()
    raw_data = result.raw_data if isinstance(result.raw_data, dict) else {}
    performance = raw_data.get('performance_metrics')

    candidates = []

    if isinstance(performance, dict):
        if prediction_key:
            candidates.append(performance.get(prediction_key))
        candidates.append(performance.get('Prediction'))
        candidates.append(performance.get('prediction'))
        candidates.append(performance.get('CI_Prediction_Value'))

    if raw_data:
        if prediction_key:
            candidates.append(raw_data.get(prediction_key))
        candidates.append(raw_data.get('Prediction'))
        candidates.append(raw_data.get('prediction'))

    if getattr(result, 'prediction_value', None):
        candidates.append(result.prediction_value)

    for candidate in candidates:
        numeric = _parse_numeric(candidate)
        if numeric is not None:
            return numeric
    return None


def _extract_ci(invitation):
    result = getattr(invitation, 'testprojectresult', None)
    project = invitation.test_project
    score_key = (getattr(project, 'score_field_system', '') or '').strip()

    candidates = []

    if result:
        raw_data = result.raw_data if isinstance(result.raw_data, dict) else {}
        performance = raw_data.get('performance_metrics')

        if isinstance(performance, dict):
            candidates.append(performance.get('CI_Raw_Value'))
            if score_key:
                candidates.append(performance.get(score_key))

        if raw_data:
            candidates.append(raw_data.get('CI_Raw_Value'))
            if score_key:
                candidates.append(raw_data.get(score_key))

        candidates.append(getattr(result, 'score_value', None))

    candidates.append(getattr(invitation, 'effective_score', None))
    candidates.append(getattr(invitation, 'score', None))

    for candidate in candidates:
        numeric = _parse_numeric(candidate)
        if numeric is not None:
            return numeric
    return None


def _normalize_dt(value):
    if not value:
        return None
    if timezone.is_aware(value):
        return timezone.make_naive(value)
    return value


def _sort_invitations(invitations, order_option):
    def score_desc_key(invitation):
        pred = invitation._prediction_score
        ci = invitation._ci_score
        has_any = invitation._has_score
        pred_present = pred is not None
        ci_val = ci if ci is not None else float('-inf')
        pred_val = pred if pred_present else (ci if ci is not None else float('-inf'))
        completed = _normalize_dt(getattr(invitation, 'effective_completed_at', None))
        completed_ts = completed.timestamp() if completed else float('-inf')
        return (
            0 if has_any else 1,
            0 if pred_present else 1,
            -pred_val,
            -ci_val,
            -completed_ts,
        )

    def score_asc_key(invitation):
        pred = invitation._prediction_score
        ci = invitation._ci_score
        has_any = invitation._has_score
        pred_present = pred is not None
        ci_val = ci if ci is not None else float('inf')
        pred_val = pred if pred_present else (ci if ci is not None else float('inf'))
        completed = _normalize_dt(getattr(invitation, 'effective_completed_at', None))
        completed_ts = completed.timestamp() if completed else float('inf')
        return (
            0 if has_any else 1,
            0 if pred_present else 1,
            pred_val,
            ci_val,
            completed_ts,
        )

    if order_option == 'score_desc':
        invitations.sort(key=score_desc_key)
    elif order_option == 'score_asc':
        invitations.sort(key=score_asc_key)


def build_test_result_listing(request, base_queryset, *, options: ListingOptions) -> Dict[str, Any]:
    user = options.user
    invitations = base_queryset

    search = request.GET.get('search', '').strip()
    if search:
        invitations = invitations.filter(
            Q(invitee__name__icontains=search)
            | Q(invitee__email__icontains=search)
            | Q(test_project__name__icontains=search)
        )

    status = request.GET.get('status', '')
    if status:
        invitations = invitations.filter(status=status)

    crawl_status = request.GET.get('crawl_status', '')
    if crawl_status == 'pending':
        invitations = invitations.filter(
            Q(testprojectresult__isnull=True)
            | Q(testprojectresult__crawl_status='pending')
        )
    elif crawl_status in ['crawling', 'completed', 'failed']:
        invitations = invitations.filter(testprojectresult__crawl_status=crawl_status)

    project_filter = request.GET.get('project', '')
    if options.locked_project_id:
        invitations = invitations.filter(test_project__id=options.locked_project_id)
        project_filter = str(options.locked_project_id)
    elif options.allow_project_filter and project_filter:
        invitations = invitations.filter(test_project__id=project_filter)
    else:
        project_filter = ''

    identity_filter = request.GET.get('identity', '')
    if identity_filter:
        invitations = invitations.filter(invitee__status=identity_filter)

    position_filter = request.GET.get('position', '')
    if position_filter:
        invitations = invitations.filter(invitee__position=position_filter)

    invitations = invitations.annotate(
        effective_score=Coalesce(
            Cast('score', FloatField()),
            Cast('testprojectresult__score_value', FloatField()),
        ),
        has_completion=Case(
            When(testprojectresult__crawled_at__isnull=False, then=Value(1)),
            When(completed_at__isnull=False, then=Value(1)),
            default=Value(0),
            output_field=IntegerField(),
        ),
        effective_completed_at=Coalesce('completed_at', 'testprojectresult__crawled_at'),
    )

    order_option = request.GET.get('order', 'completion_desc')
    if order_option == 'completion_asc':
        invitations = invitations.order_by(
            F('has_completion').desc(),
            F('effective_completed_at').asc(nulls_last=True),
            '-invited_at',
        )
    else:  # completion_desc default
        invitations = invitations.order_by(
            F('has_completion').desc(),
            F('effective_completed_at').desc(nulls_last=True),
            '-invited_at',
        )

    invitations = list(invitations)

    for invitation in invitations:
        invitation._prediction_score = _extract_prediction(invitation)
        invitation._ci_score = _extract_ci(invitation)
        invitation._has_score = (
            invitation._prediction_score is not None
            or invitation._ci_score is not None
        )

    _sort_invitations(invitations, order_option)

    paginator = Paginator(invitations, options.per_page)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    if user.user_type == 'admin':
        project_choices = TestProject.objects.filter(
            testinvitation__test_project__isnull=False
        ).distinct().order_by('name')
        position_choices = (
            TestInvitee.objects.exclude(position='')
            .order_by('position')
            .values_list('position', flat=True)
            .distinct()
        )
    else:
        project_choices = TestProject.objects.filter(
            testinvitation__enterprise=user,
            testinvitation__test_project__isnull=False,
        ).distinct().order_by('name')
        position_choices = (
            TestInvitee.objects.filter(enterprise=user)
            .exclude(position='')
            .order_by('position')
            .values_list('position', flat=True)
            .distinct()
        )

    query_params = request.GET.copy()
    if 'page' in query_params:
        query_params = query_params.copy()
        query_params.pop('page')

    context = {
        'page_obj': page_obj,
        'search': search,
        'status_filter': status,
        'crawl_status_filter': crawl_status,
        'project_filter': project_filter,
        'identity_filter': identity_filter,
        'position_filter': position_filter,
        'order_option': order_option,
        'status_choices': TestInvitation.STATUS_CHOICES,
        'identity_choices': TestInvitee.STATUS_CHOICES,
        'position_choices': position_choices,
        'order_choices': ORDER_CHOICES,
        'crawl_status_choices': CRAWL_STATUS_CHOICES,
        'project_choices': project_choices,
        'is_admin': user.user_type == 'admin',
        'querystring': query_params.urlencode(),
    }

    return context
