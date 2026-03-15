import uuid

from django.db import migrations, models


DEFAULT_ASYNC_TASK_USER_ID = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")


def backfill_task_fields(apps, _schema_editor):
    task_model = apps.get_model("crm", "Task")
    task_model.objects.filter(priority="NORMAL").update(priority="MEDIUM")


class Migration(migrations.Migration):
    dependencies = [
        ("crm", "0002_task"),
    ]

    operations = [
        migrations.AddField(
            model_name="task",
            name="contact_id",
            field=models.UUIDField(blank=True, db_index=True, null=True),
        ),
        migrations.AddField(
            model_name="task",
            name="due_date",
            field=models.DateField(blank=True, db_index=True, null=True),
        ),
        migrations.AddField(
            model_name="task",
            name="user_id",
            field=models.UUIDField(
                db_index=True,
                default=DEFAULT_ASYNC_TASK_USER_ID,
            ),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name="task",
            name="deal_id",
            field=models.UUIDField(blank=True, db_index=True, null=True),
        ),
        migrations.AlterField(
            model_name="task",
            name="priority",
            field=models.CharField(
                choices=[
                    ("LOW", "Low"),
                    ("MEDIUM", "Medium"),
                    ("HIGH", "High"),
                ],
                default="MEDIUM",
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name="task",
            name="source_event_id",
            field=models.CharField(
                blank=True,
                max_length=255,
                null=True,
                unique=True,
            ),
        ),
        migrations.CreateModel(
            name="Activity",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("company_id", models.UUIDField(db_index=True)),
                ("contact_id", models.UUIDField(blank=True, db_index=True, null=True)),
                ("deal_id", models.UUIDField(blank=True, db_index=True, null=True)),
                ("user_id", models.UUIDField(db_index=True)),
                (
                    "type",
                    models.CharField(
                        choices=[
                            ("CALL", "Call"),
                            ("EMAIL", "Email"),
                            ("MEETING", "Meeting"),
                            ("NOTE", "Note"),
                        ],
                        max_length=20,
                    ),
                ),
                ("details", models.TextField()),
                ("occurred_at", models.DateTimeField(db_index=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "ordering": ["-occurred_at", "-created_at", "id"],
            },
        ),
        migrations.RunPython(backfill_task_fields, migrations.RunPython.noop),
    ]
