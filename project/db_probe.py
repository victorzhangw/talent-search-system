"""db_probe.py

Probe script to inspect DB field names / sample values for:
- company code candidates
- candidate id
- assessment/report id

Usage:
  python project/db_probe.py

Settings:
  - Default: DJANGO_SETTINGS_MODULE=project.settings
  - To force sqlite: DJANGO_SETTINGS_MODULE=project.settings_sqlite python project/db_probe.py

Note:
  If Django isn't installed in your runtime, this script will fall back to printing
  a static field-name map based on this codebase.
"""

import os


def _setup_django() -> bool:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "project.settings")
    try:
        import django  # type: ignore

        django.setup()
        return True
    except Exception as e:
        print("[WARN] Django setup not available:", repr(e))
        return False


def _static_field_map():
    print("=== Static Model Field Map (no Django runtime) ===")
    print()
    print("Company code candidates:")
    print("- EnterpriseProfile.tax_id       # 統一編號; stable company code candidate")
    print("- EnterpriseProfile.company_name # company display name")
    print()
    print("Candidate id:")
    print("- TestInvitee.id                 # primary key (int) used as candidate_id")
    print()
    print("Assessment/report id:")
    print("- TestProjectResult.id           # primary key used as assessment_id")
    print("- TestInvitation.invitee_id      # links assessment to candidate(TestInvitee.id)")


def main():
    if not _setup_django():
        _static_field_map()
        return

    from django.db import connection
    from core.models import EnterpriseProfile, TestInvitee, TestProjectResult

    print("=== Django DB Probe ===")
    print("DJANGO_SETTINGS_MODULE:", os.environ.get("DJANGO_SETTINGS_MODULE"))
    print("DB vendor:", connection.vendor)
    print("DB name:", connection.settings_dict.get("NAME"))
    print()

    print("--- Company code candidates (EnterpriseProfile) ---")
    print("Fields:")
    print("- company_name")
    print("- tax_id")
    ep = EnterpriseProfile.objects.select_related("user").order_by("id").first()
    if ep:
        print("Sample:")
        print(
            {
                "enterprise_user_id": ep.user_id,
                "enterprise_username": ep.user.username,
                "company_name": ep.company_name,
                "tax_id": ep.tax_id,
                "verification_status": ep.verification_status,
            }
        )
    else:
        print("No EnterpriseProfile rows found.")
    print()

    print("--- Candidate id (TestInvitee) ---")
    print("Primary key field: id")
    invitee = TestInvitee.objects.select_related("enterprise").order_by("id").first()
    if invitee:
        print("Sample:")
        print(
            {
                "candidate_id": invitee.id,
                "name": invitee.name,
                "email": invitee.email,
                "enterprise_user_id": invitee.enterprise_id,
                "company": invitee.company,
                "position": invitee.position,
                "last_test_date": invitee.last_test_date.isoformat() if invitee.last_test_date else None,
            }
        )
    else:
        print("No TestInvitee rows found.")
    print()

    print("--- Latest assessment/report (TestProjectResult) ---")
    result = (
        TestProjectResult.objects.select_related("test_invitation", "test_project")
        .order_by("-created_at")
        .first()
    )
    if result:
        inv = result.test_invitation
        print("Sample:")
        print(
            {
                "assessment_id": result.id,
                "test_project_id": result.test_project_id,
                "test_project_name": getattr(result.test_project, "name", None),
                "enterprise_user_id": inv.enterprise_id if inv else None,
                "candidate_id": inv.invitee_id if inv else None,
                "score_value": result.score_value,
                "prediction_value": result.prediction_value,
                "trait_results_keys": list((result.trait_results or {}).keys())[:10],
            }
        )
    else:
        print("No TestProjectResult rows found.")


if __name__ == "__main__":
    main()
