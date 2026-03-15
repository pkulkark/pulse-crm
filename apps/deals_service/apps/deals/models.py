import uuid

from django.db import models


class DealStatus(models.TextChoices):
    NEW = "NEW", "New"
    QUALIFIED = "QUALIFIED", "Qualified"
    WON = "WON", "Won"
    LOST = "LOST", "Lost"


class Deal(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company_id = models.UUIDField(db_index=True)
    primary_contact_id = models.UUIDField(blank=True, null=True)
    status = models.CharField(
        max_length=20,
        choices=DealStatus.choices,
        default=DealStatus.NEW,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at", "-created_at", "id"]

    def __str__(self):
        return f"Deal {self.id} ({self.status})"
