import uuid

from django.db import migrations


DEFAULT_COMPANY_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")


def seed_default_company(apps, _schema_editor):
    company_model = apps.get_model("crm", "Company")
    company_model.objects.update_or_create(
        id=DEFAULT_COMPANY_ID,
        defaults={"name": "Sample Industries"},
    )


def unseed_default_company(apps, _schema_editor):
    company_model = apps.get_model("crm", "Company")
    company_model.objects.filter(id=DEFAULT_COMPANY_ID).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("crm", "0003_task_activity_contract"),
    ]

    operations = [
        migrations.RunPython(seed_default_company, unseed_default_company),
    ]
