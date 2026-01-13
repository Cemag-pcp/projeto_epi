from django.db import models
from django.utils import timezone
from django_tenants.models import DomainMixin, TenantMixin


class Company(TenantMixin):
    name = models.CharField(max_length=200)
    paid_until = models.DateField(null=True, blank=True)
    on_trial = models.BooleanField(default=True)
    created_on = models.DateField(default=timezone.now)
    estoque_enabled = models.BooleanField(default=True)

    auto_create_schema = True

    def __str__(self):
        return self.name


class Domain(DomainMixin):
    def __str__(self):
        return self.domain
