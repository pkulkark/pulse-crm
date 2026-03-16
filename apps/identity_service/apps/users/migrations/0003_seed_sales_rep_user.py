import uuid

from django.contrib.auth.hashers import make_password
from django.db import migrations


DEFAULT_COMPANY_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
SALES_REP_USER_ID = uuid.UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")


def seed_sales_rep_user(apps, _schema_editor):
    user_model = apps.get_model("users", "User")
    user, _created = user_model.objects.update_or_create(
        email="salesrep@example.com",
        defaults={
            "company_id": DEFAULT_COMPANY_ID,
            "id": SALES_REP_USER_ID,
            "is_active": True,
            "name": "Sample Sales Rep",
            "role": "sales_rep",
        },
    )
    user.password = make_password("secret")
    user.save(update_fields=["password"])


def unseed_sales_rep_user(apps, _schema_editor):
    user_model = apps.get_model("users", "User")
    user_model.objects.filter(email="salesrep@example.com").delete()


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0002_seed_default_users"),
    ]

    operations = [
        migrations.RunPython(seed_sales_rep_user, unseed_sales_rep_user),
    ]
