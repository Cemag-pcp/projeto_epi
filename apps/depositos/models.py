from django.db import models

from apps.core.models import TenantModel


class Deposito(TenantModel):
    nome = models.CharField(max_length=200)
    endereco = models.TextField(blank=True)
    planta = models.ForeignKey("funcionarios.Planta", on_delete=models.PROTECT)
    bloquear_movimento_negativo = models.BooleanField(default=False)
    ativo = models.BooleanField(default=True)

    def __str__(self):
        return self.nome
