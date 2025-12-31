from django.db import models

from apps.core.models import TenantModel


class Fornecedor(TenantModel):
    nome = models.CharField(max_length=200)
    documento = models.CharField(max_length=50, blank=True)
    email = models.EmailField(blank=True)
    telefone = models.CharField(max_length=40, blank=True)
    ativo = models.BooleanField(default=True)

    def __str__(self):
        return self.nome