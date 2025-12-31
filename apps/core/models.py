from django.db import models

from apps.tenants.models import Company


class TenantModel(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="%(class)s_set")

    class Meta:
        abstract = True
