from django.conf import settings
from django.db import models

from apps.core.models import TenantModel


class UserProfile(TenantModel):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    funcionario = models.OneToOneField(
        "funcionarios.Funcionario",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="acesso",
    )
    setor = models.ForeignKey(
        "setores.Setor",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    planta = models.ForeignKey(
        "funcionarios.Planta",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    def group_label(self):
        group = self.user.groups.first()
        return group.name if group else "-"

    def __str__(self):
        return self.user.get_full_name() or self.user.username
