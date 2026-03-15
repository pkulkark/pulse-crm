import uuid

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Q


class Company(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    parent_company = models.ForeignKey(
        "self",
        blank=True,
        null=True,
        on_delete=models.PROTECT,
        related_name="child_companies",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=~Q(id=F("parent_company")),
                name="crm_company_not_own_parent",
            ),
        ]
        ordering = ["name", "id"]

    def __str__(self):
        return self.name

    def clean(self):
        super().clean()

        if self.parent_company_id is None:
            return

        if self.parent_company_id == self.id:
            raise ValidationError(
                {"parent_company": "A company cannot be its own parent."},
            )

        parent = self.parent_company
        visited = set()

        while parent is not None:
            if parent.id == self.id:
                raise ValidationError(
                    {
                        "parent_company": (
                            "Company hierarchy cannot contain cycles."
                        )
                    },
                )

            if parent.id in visited:
                break

            visited.add(parent.id)
            parent = parent.parent_company


class Contact(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(
        Company,
        on_delete=models.PROTECT,
        related_name="contacts",
    )
    name = models.CharField(max_length=255)
    email = models.EmailField()
    job_title = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["company", "email"],
                name="crm_contact_company_email_unique",
            ),
        ]
        ordering = ["name", "id"]

    def __str__(self):
        return f"{self.name} <{self.email}>"

    def save(self, *args, **kwargs):
        if isinstance(self.email, str):
            self.email = self.email.strip().lower()

        super().save(*args, **kwargs)

