from django.db import models

from apps.core.models import TenantModel


class Relatorio(TenantModel):
    nome = models.CharField(max_length=120)
    descricao = models.TextField(blank=True)
    widgets = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return self.nome
