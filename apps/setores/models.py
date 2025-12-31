from django.db import models

from apps.core.models import TenantModel


class Setor(TenantModel):
    nome = models.CharField(max_length=150)
    descricao = models.TextField(blank=True)
    ativo = models.BooleanField(default=True)

    def __str__(self):
        return self.nome