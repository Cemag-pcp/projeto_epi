from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from apps.core.models import TenantModel


class Entrega(TenantModel):
    STATUS_CHOICES = [
        ("entregue", "Entregue"),
        ("cancelada", "Cancelada"),
        ("aguardando", "Aguardando entrega"),
    ]

    funcionario = models.ForeignKey(
        "funcionarios.Funcionario",
        on_delete=models.PROTECT,
        related_name="entregas",
    )
    produto = models.ForeignKey("produtos.Produto", on_delete=models.PROTECT, related_name="entregas")
    deposito = models.ForeignKey("depositos.Deposito", on_delete=models.PROTECT, related_name="entregas")
    quantidade = models.DecimalField(max_digits=12, decimal_places=2)
    ca = models.CharField(max_length=50, blank=True)
    observacao = models.TextField(blank=True)
    entregue_em = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="entregue")
    motivo_cancelamento = models.TextField(blank=True)

    class Meta:
        ordering = ["-entregue_em"]

    def __str__(self):
        return f"{self.funcionario} - {self.produto}"

    def clean(self):
        super().clean()
        if self.quantidade is None or self.quantidade <= 0:
            raise ValidationError({"quantidade": "Quantidade deve ser maior que zero."})


class EntregaItem(TenantModel):
    entrega = models.ForeignKey(Entrega, on_delete=models.CASCADE, related_name="itens")
    produto = models.ForeignKey("produtos.Produto", on_delete=models.PROTECT, related_name="entregas_itens")
    deposito = models.ForeignKey("depositos.Deposito", on_delete=models.PROTECT, related_name="entregas_itens")
    quantidade = models.DecimalField(max_digits=12, decimal_places=2)
    ca = models.CharField(max_length=50, blank=True)
    observacao = models.TextField(blank=True)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"{self.entrega} - {self.produto}"
