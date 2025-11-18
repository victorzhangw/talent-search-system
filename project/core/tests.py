from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import (
    TestInvitation,
    TestInvitee,
    TestProject,
    TestProjectResult,
    User,
)


class TestResultListSortingTests(TestCase):
    def setUp(self):
        self.now = timezone.now()
        self.enterprise = User.objects.create_user(
            username='enterprise_user',
            email='enterprise@example.com',
            password='password',
            user_type='enterprise'
        )
        self.project_creator = User.objects.create_user(
            username='project_creator',
            email='creator@example.com',
            password='password',
            user_type='admin',
            is_staff=True
        )
        self.project = TestProject.objects.create(
            name='AI Talent Assessment',
            description='',
            name_abbreviation='AIT',
            test_link='https://example.com/test',
            score_field_chinese='CI Score',
            score_field_system='ci_score',
            prediction_field_chinese='Prediction Score',
            prediction_field_system='pred_score',
            job_role_system_name='job_role_field',
            created_by=self.project_creator
        )

        self.client.force_login(self.enterprise)

        self.alpha = self._create_invitation(
            name='Alpha',
            completed_minutes=10,
            perf_pred='88%',
            perf_ci='77',
            perf_score='77',
            result_score=77,
        )
        self.bravo = self._create_invitation(
            name='Bravo',
            completed_minutes=20,
            perf_ci='90%',
            perf_score='90%',
            result_score=90,
        )
        self.charlie = self._create_invitation(
            name='Charlie',
            completed_minutes=30,
            perf_pred='55 (High)',
            raw_pred='49',
            perf_score='63%',
            raw_score='61',
            result_score=63,
        )
        self.echo = self._create_invitation(
            name='Echo',
            completed_minutes=40,
            result_pred='42%',
            result_score=42,
        )
        self.delta = self._create_invitation(
            name='Delta',
            completed_minutes=50,
            create_result=False
        )

    def _create_invitation(
        self,
        name,
        *,
        completed_minutes=0,
        perf_pred=None,
        raw_pred=None,
        result_pred=None,
        perf_ci=None,
        raw_ci=None,
        perf_score=None,
        raw_score=None,
        result_score=None,
        create_result=True,
    ):
        invitee = TestInvitee.objects.create(
            enterprise=self.enterprise,
            name=name,
            email=f'{name.lower()}@example.com',
            status='employed',
            position='',
        )
        invitation = TestInvitation.objects.create(
            enterprise=self.enterprise,
            invitee=invitee,
            test_project=self.project,
            expires_at=self.now + timedelta(days=7),
            completed_at=self.now - timedelta(minutes=completed_minutes),
            status='completed',
            points_consumed=1,
        )

        if not create_result:
            return invitation

        performance_metrics = {}
        if perf_pred is not None:
            performance_metrics[self.project.prediction_field_system] = perf_pred
        if perf_ci is not None:
            performance_metrics['CI_Raw_Value'] = perf_ci
        if perf_score is not None:
            performance_metrics[self.project.score_field_system] = perf_score

        raw_payload = {}
        if performance_metrics:
            raw_payload['performance_metrics'] = performance_metrics
        if raw_pred is not None:
            raw_payload[self.project.prediction_field_system] = raw_pred
        if raw_ci is not None:
            raw_payload['CI_Raw_Value'] = raw_ci
        if raw_score is not None:
            raw_payload[self.project.score_field_system] = raw_score

        result_kwargs = {
            'test_invitation': invitation,
            'test_project': self.project,
            'raw_data': raw_payload,
            'processed_data': {},
            'crawl_status': 'completed',
            'crawled_at': invitation.completed_at or self.now,
        }
        if result_score is not None:
            result_kwargs['score_value'] = result_score
        if result_pred is not None:
            result_kwargs['prediction_value'] = result_pred

        TestProjectResult.objects.create(**result_kwargs)
        return invitation

    def _fetch_ordered_names(self, order_option):
        response = self.client.get(
            reverse('test_result_list'),
            {'order': order_option}
        )
        self.assertEqual(response.status_code, 200)
        invitations = list(response.context['page_obj'].object_list)
        names = [inv.invitee.name for inv in invitations]
        scores = {
            inv.invitee.name: (inv._prediction_score, inv._ci_score)
            for inv in invitations
        }
        return names, scores

    def test_score_desc_orders_predictions_before_ci_only(self):
        names, scores = self._fetch_ordered_names('score_desc')
        self.assertEqual(
            names,
            ['Alpha', 'Charlie', 'Echo', 'Bravo', 'Delta']
        )
        self.assertEqual(scores['Alpha'], (88.0, 77.0))
        self.assertEqual(scores['Charlie'], (55.0, 63.0))
        self.assertEqual(scores['Echo'], (42.0, 42.0))
        self.assertEqual(scores['Bravo'], (None, 90.0))
        self.assertEqual(scores['Delta'], (None, None))

    def test_score_asc_orders_predictions_lowest_first(self):
        names, _ = self._fetch_ordered_names('score_asc')
        self.assertEqual(
            names,
            ['Echo', 'Charlie', 'Alpha', 'Bravo', 'Delta']
        )

    def test_fallbacks_align_with_template_sources(self):
        names, scores = self._fetch_ordered_names('score_desc')
        self.assertEqual(scores['Charlie'][0], 55.0)  # performance metric overrides raw
        self.assertEqual(scores['Charlie'][1], 63.0)  # falls back to score field
        self.assertEqual(scores['Echo'][0], 42.0)  # prediction_value fallback
        self.assertEqual(scores['Echo'][1], 42.0)  # score_value fallback when CI absent
