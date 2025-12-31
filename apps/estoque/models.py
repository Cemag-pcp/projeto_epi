from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction

from apps.core.models import TenantModel


class Estoque(TenantModel):
    produto = models.ForeignKey("produtos.Produto", on_delete=models.CASCADE)
    deposito = models.ForeignKey("depositos.Deposito", on_delete=models.CASCADE)
    quantidade = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("produto", "deposito")

    def __str__(self):
        return f"{self.produto} - {self.deposito}"


class MovimentacaoEstoque(TenantModel):
    ENTRADA = "entrada"
    SAIDA = "saida"
    TRANSFERENCIA = "transferencia"
    TIPO_CHOICES = (
        (ENTRADA, "Entrada"),
        (SAIDA, "Saida"),
        (TRANSFERENCIA, "Transferencia"),
    )

    estoque = models.ForeignKey(Estoque, on_delete=models.CASCADE, related_name="movimentacoes")
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    quantidade = models.DecimalField(max_digits=12, decimal_places=2)
    deposito_destino = models.ForeignKey(
        "depositos.Deposito", on_delete=models.SET_NULL, null=True, blank=True
    )
    observacao = models.TextField(blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.get_tipo_display()} - {self.estoque}"

    def clean(self):
        super().clean()
        if self.tipo == self.TRANSFERENCIA and not self.deposito_destino:
            raise ValidationError({"deposito_destino": "Informe o deposito de destino."})

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        self.full_clean()
        with transaction.atomic():
            super().save(*args, **kwargs)
            if not is_new:
                return
            origem = Estoque.objects.select_for_update().get(pk=self.estoque_id)
            if self.tipo == self.ENTRADA:
                origem.quantidade += self.quantidade
                origem.save(update_fields=["quantidade"])
                ActionLog.log(self.company, self, "entrada", {"quantidade": str(self.quantidade)})
                return
            if self.tipo == self.SAIDA:
                origem.quantidade -= self.quantidade
                origem.save(update_fields=["quantidade"])
                ActionLog.log(self.company, self, "saida", {"quantidade": str(self.quantidade)})
                return
            if self.tipo == self.TRANSFERENCIA:
                destino, _ = Estoque.objects.select_for_update().get_or_create(
                    company=self.company,
                    produto=origem.produto,
                    deposito=self.deposito_destino,
                    defaults={"quantidade": 0},
                )
                origem.quantidade -= self.quantidade
                destino.quantidade += self.quantidade
                origem.save(update_fields=["quantidade"])
                destino.save(update_fields=["quantidade"])
                ActionLog.log(
                    self.company,
                    self,
                    "transferencia",
                    {"quantidade": str(self.quantidade), "deposito_destino_id": self.deposito_destino_id},
                )


class ActionLog(TenantModel):
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    action = models.CharField(max_length=50)
    reference = models.CharField(max_length=200)
    payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    @classmethod
    def log(cls, company, instance, action, payload=None):
        reference = f"{instance.__class__.__name__}:{instance.pk}"
        cls.objects.create(company=company, action=action, reference=reference, payload=payload or {})
