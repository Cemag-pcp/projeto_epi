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
    VALIDACAO_RECEBIMENTO_CHOICES = [
        ("nenhum", "Nenhum"),
        ("senha", "Senha"),
        ("assinatura", "Assinatura"),
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
    validacao_recebimento = models.CharField(
        max_length=10,
        choices=VALIDACAO_RECEBIMENTO_CHOICES,
        default="nenhum",
    )
    motivo_cancelamento = models.TextField(blank=True)
    assinatura = models.ImageField(upload_to="entregas/assinaturas/", blank=True, null=True)

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
    grade = models.CharField(max_length=50, blank=True)
    observacao = models.TextField(blank=True)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"{self.entrega} - {self.produto}"


class Devolucao(TenantModel):
    entrega = models.ForeignKey(Entrega, on_delete=models.PROTECT, related_name="devolucoes")
    devolvida_em = models.DateTimeField(default=timezone.now)
    observacao = models.TextField(blank=True)
    assinatura = models.ImageField(upload_to="entregas/devolucoes/assinaturas/", blank=True, null=True)

    class Meta:
        ordering = ["-devolvida_em", "-id"]

    def __str__(self):
        return f"Devolucao #{self.pk} - Entrega #{self.entrega_id}"


class DevolucaoItem(TenantModel):
    CONDICAO_BOA = "boa"
    CONDICAO_USADA = "usada"
    CONDICAO_DANIFICADA = "danificada"
    CONDICAO_VENCIDA = "vencida"
    CONDICAO_OUTRA = "outra"

    CONDICAO_CHOICES = [
        (CONDICAO_BOA, "Boa"),
        (CONDICAO_USADA, "Usada"),
        (CONDICAO_DANIFICADA, "Danificada"),
        (CONDICAO_VENCIDA, "Vencida"),
        (CONDICAO_OUTRA, "Outra"),
    ]

    devolucao = models.ForeignKey(Devolucao, on_delete=models.CASCADE, related_name="itens")
    entrega_item = models.ForeignKey(
        EntregaItem,
        on_delete=models.PROTECT,
        related_name="devolucoes_itens",
    )
    quantidade = models.DecimalField(max_digits=12, decimal_places=2)
    condicao = models.CharField(max_length=20, choices=CONDICAO_CHOICES)
    motivo = models.TextField(blank=True)
    volta_para_estoque = models.BooleanField(default=True)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"{self.devolucao} - {self.entrega_item.produto}"

    def clean(self):
        super().clean()
        if self.quantidade is None or self.quantidade <= 0:
            raise ValidationError({"quantidade": "Quantidade deve ser maior que zero."})
        if self.condicao == self.CONDICAO_OUTRA and not (self.motivo or "").strip():
            raise ValidationError({"motivo": "Informe o motivo para a condicao 'Outra'."})
