from django.db.models.signals import post_save
from django.dispatch import receiver
from django_tenants.utils import schema_context

from apps.funcionarios.models import Planta
from .models import Company


@receiver(post_save, sender=Company)
def ensure_default_planta(sender, instance, created, **kwargs):
    if not created:
        return
    with schema_context(instance.schema_name):
        if not Planta.objects.exists():
            Planta.objects.create(
                company_id=instance.id,
                nome="Principal",
                ativo=True,
            )
