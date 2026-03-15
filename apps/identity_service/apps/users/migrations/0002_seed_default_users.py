import uuid

from django.contrib.auth.hashers import make_password
from django.db import migrations


DEFAULT_COMPANY_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
ADMIN_USER_ID = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
MANAGER_USER_ID = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")


def seed_users(apps, _schema_editor):
    user_model = apps.get_model("users", "User")

    users = [
        {
            "company_id": DEFAULT_COMPANY_ID,
            "email": "admin@example.com",
            "id": ADMIN_USER_ID,
            "name": "Sample Admin",
            "password": "secret",
            "role": "admin",
        },
        {
            "company_id": DEFAULT_COMPANY_ID,
            "email": "manager@example.com",
            "id": MANAGER_USER_ID,
            "name": "Sample Manager",
            "password": "secret",
            "role": "manager",
        },
    ]

    for user_data in users:
        password = user_data.pop("password")
        user, _created = user_model.objects.update_or_create(
            email=user_data["email"],
            defaults=user_data,
        )
        user.password = make_password(password)
        user.save(update_fields=["password"])


def unseed_users(apps, _schema_editor):
    user_model = apps.get_model("users", "User")
    user_model.objects.filter(
        email__in=["admin@example.com", "manager@example.com"],
    ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_users, unseed_users),
    ]
