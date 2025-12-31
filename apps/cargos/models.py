from django.db import models

from apps.core.models import TenantModel


class Cargo(TenantModel):
    nome = models.CharField(max_length=150)
    descricao = models.TextField(blank=True)
    setor = models.ForeignKey("setores.Setor", on_delete=models.SET_NULL, null=True, blank=True)
    ativo = models.BooleanField(default=True)

    def __str__(self):
        return self.nome