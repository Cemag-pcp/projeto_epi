from django.db import models
from django.utils import timezone

from apps.core.models import TenantModel


class EmpresaParceira(TenantModel):
    nome = models.CharField(max_length=200)
    documento = models.CharField(max_length=40, blank=True)
    contato = models.CharField(max_length=120, blank=True)
    ativo = models.BooleanField(default=True)

    class Meta:
        ordering = ["nome"]

    def __str__(self):
        return self.nome


class Terceiro(TenantModel):
    nome = models.CharField(max_length=200)
    documento = models.CharField(max_length=40, blank=True)
    empresa_parceira = models.ForeignKey(
        EmpresaParceira,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="terceiros",
    )
    telefone = models.CharField(max_length=40, blank=True)
    ativo = models.BooleanField(default=True)

    class Meta:
        ordering = ["nome"]

    def __str__(self):
        return self.nome


class AcessoEPI(TenantModel):
    TIPO_PESSOA_CHOICES = [
        ("funcionario", "Funcionario"),
        ("terceiro", "Terceiro"),
    ]
    STATUS_EPI_CHOICES = [
        ("em_dia", "Em dia"),
        ("pendente", "Pendente"),
        ("nao_informado", "Nao informado"),
    ]
    STATUS_TREINAMENTO_CHOICES = [
        ("em_dia", "Em dia"),
        ("pendente", "Pendente"),
        ("nao_aplicavel", "Nao aplicavel"),
    ]

    tipo_pessoa = models.CharField(max_length=20, choices=TIPO_PESSOA_CHOICES, default="funcionario")
    funcionario = models.ForeignKey(
        "funcionarios.Funcionario",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="acessos_epi",
    )
    terceiro = models.ForeignKey(
        Terceiro,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="acessos_epi",
    )
    planta = models.ForeignKey(
        "funcionarios.Planta",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    data_hora = models.DateTimeField(default=timezone.now)
    status_epi = models.CharField(max_length=20, choices=STATUS_EPI_CHOICES, default="nao_informado")
    status_treinamento = models.CharField(
        max_length=20,
        choices=STATUS_TREINAMENTO_CHOICES,
        default="nao_aplicavel",
    )
    permitido = models.BooleanField(default=True)
    observacao = models.TextField(blank=True)

    class Meta:
        ordering = ["-data_hora"]

    def __str__(self):
        return f"{self.get_tipo_pessoa_display()} - {self.identificacao_label()}"

    def identificacao_label(self):
        if self.tipo_pessoa == "terceiro":
            return self.terceiro or "-"
        return self.funcionario or "-"

    def status_epi_label(self):
        return self.get_status_epi_display()

    def status_treinamento_label(self):
        return self.get_status_treinamento_display()

    def data_hora_label(self):
        if not self.data_hora:
            return "-"
        return self.data_hora.strftime("%d/%m/%Y %H:%M")


class ConsumoParceiro(TenantModel):
    terceiro = models.ForeignKey(
        Terceiro,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="consumos",
    )
    deposito = models.ForeignKey(
        "depositos.Deposito",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="consumos_parceiros",
    )
    assinatura = models.ImageField(
        upload_to="acessos/consumos/assinaturas/",
        null=True,
        blank=True,
    )
    produto = models.ForeignKey(
        "produtos.Produto",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="consumos_parceiros",
    )
    quantidade = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    data = models.DateField(default=timezone.localdate)
    observacao = models.TextField(blank=True)

    class Meta:
        ordering = ["-data"]

    def __str__(self):
        return f"{self.terceiro or '-'} - {self.produto or '-'}"

    def empresa_parceira_label(self):
        if self.terceiro and self.terceiro.empresa_parceira:
            return self.terceiro.empresa_parceira
        return "-"
