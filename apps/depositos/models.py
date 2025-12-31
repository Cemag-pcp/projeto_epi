from django.db import models

from apps.core.models import TenantModel


class Deposito(TenantModel):
    nome = models.CharField(max_length=200)
    endereco = models.TextField(blank=True)
    ativo = models.BooleanField(default=True)

    def __str__(self):
        return self.nome
