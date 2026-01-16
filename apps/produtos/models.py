from django.core.exceptions import ValidationError
from django.db import models

from apps.core.models import TenantModel

MAX_ATTACHMENT_SIZE = 3 * 1024 * 1024  # 3MB


def validate_attachment_size(value):
    if value.size > MAX_ATTACHMENT_SIZE:
        raise ValidationError("Arquivo excede o limite de 3MB.")


class Produto(TenantModel):
    nome = models.CharField(max_length=200)
    foto = models.ImageField(upload_to="produtos/fotos/", null=True, blank=True)
    sku = models.CharField(max_length=80, blank=True)
    codigo_externo = models.CharField(max_length=64, blank=True)
    referencia = models.CharField(max_length=120, blank=True)
    periodicidade_quantidade = models.PositiveIntegerField(default=1, verbose_name="Quantidade")
    periodicidade = models.ForeignKey(
        "Periodicidade",
        on_delete=models.PROTECT,
    )
    unidade = models.ForeignKey("UnidadeProduto", on_delete=models.SET_NULL, null=True, blank=True)
    tipo = models.ForeignKey("TipoProduto", on_delete=models.SET_NULL, null=True, blank=True)
    familia = models.ForeignKey("FamiliaProduto", on_delete=models.SET_NULL, null=True, blank=True)
    subfamilia = models.ForeignKey("SubfamiliaProduto", on_delete=models.SET_NULL, null=True, blank=True)
    localizacao = models.ForeignKey("LocalizacaoProduto", on_delete=models.SET_NULL, null=True, blank=True)
    imposto_ipi = models.DecimalField(max_digits=5, decimal_places=2, default=0, null=True, blank=True)
    imposto_st = models.DecimalField(max_digits=5, decimal_places=2, default=0, null=True, blank=True)
    imposto_outros = models.DecimalField(max_digits=5, decimal_places=2, default=0, null=True, blank=True)
    marca = models.ForeignKey("MarcaProduto", on_delete=models.SET_NULL, null=True, blank=True)
    monitora_uso = models.BooleanField(default=False)
    troca_funcionario = models.BooleanField(default=False)
    controle_epi = models.BooleanField(default=False)
    obrigar_entrega = models.BooleanField(default=False)
    dias_entrega = models.PositiveIntegerField(default=0)
    fornecedor = models.ForeignKey("fornecedores.Fornecedor", on_delete=models.SET_NULL, null=True, blank=True)
    fornecedores = models.ManyToManyField(
        "fornecedores.Fornecedor", through="ProdutoFornecedor", related_name="produtos", blank=True
    )
    estoque_minimo = models.PositiveIntegerField(default=0, null=True, blank=True)
    estoque_ideal = models.PositiveIntegerField(default=0, null=True, blank=True)
    ativo = models.BooleanField(default=True)

    def __str__(self):
        return self.nome

    def periodicidade_label(self):
        if not self.periodicidade:
            return "-"
        quantidade = self.periodicidade_quantidade or 0
        return f"{quantidade} {self.periodicidade}"


class ProdutoFornecedor(TenantModel):
    produto = models.ForeignKey(Produto, on_delete=models.CASCADE, related_name="fornecedores_rel")
    fornecedor = models.ForeignKey("fornecedores.Fornecedor", on_delete=models.CASCADE)
    ca = models.CharField(max_length=50, blank=True)
    codigo_barras = models.CharField(max_length=64, null=True, blank=True)
    codigo_fornecedor = models.CharField(max_length=80, null=True, blank=True)
    valor = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    data_vencimento = models.DateField(null=True, blank=True)
    fator_compra = models.DecimalField(max_digits=12, decimal_places=4, default=1, null=True, blank=True)
    observacao = models.TextField(null=True, blank=True)

    class Meta:
        unique_together = ("produto", "fornecedor")

    def __str__(self):
        return f"{self.produto} - {self.fornecedor}"


class ProdutoAnexo(TenantModel):
    produto = models.ForeignKey(Produto, on_delete=models.CASCADE, related_name="anexos")
    arquivo = models.FileField(upload_to="produtos/anexos/", validators=[validate_attachment_size])
    descricao = models.CharField(max_length=255, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.produto} - {self.descricao or self.arquivo.name}"


class MarcaProduto(TenantModel):
    nome = models.CharField(max_length=120)

    class Meta:
        ordering = ["nome"]

    def __str__(self):
        return self.nome


class UnidadeProduto(TenantModel):
    nome = models.CharField(max_length=60)
    sigla = models.CharField(max_length=10, blank=True)

    class Meta:
        ordering = ["nome"]

    def __str__(self):
        return self.sigla or self.nome


class TipoProduto(TenantModel):
    nome = models.CharField(max_length=120)
    ativo = models.BooleanField(default=True)

    class Meta:
        ordering = ["nome"]

    def __str__(self):
        return self.nome


class FamiliaProduto(TenantModel):
    nome = models.CharField(max_length=120)
    ativo = models.BooleanField(default=True)

    class Meta:
        ordering = ["nome"]

    def __str__(self):
        return self.nome


class SubfamiliaProduto(TenantModel):
    nome = models.CharField(max_length=120)
    ativo = models.BooleanField(default=True)

    class Meta:
        ordering = ["nome"]

    def __str__(self):
        return self.nome


class LocalRetirada(TenantModel):
    nome = models.CharField(max_length=120)
    ativo = models.BooleanField(default=True)

    class Meta:
        ordering = ["nome"]

    def __str__(self):
        return self.nome


class Periodicidade(TenantModel):
    nome = models.CharField(max_length=120)
    fator_dias = models.PositiveIntegerField(default=1)
    ativo = models.BooleanField(default=True)

    class Meta:
        ordering = ["nome"]

    def __str__(self):
        return self.nome


class LocalizacaoProduto(TenantModel):
    nome = models.CharField(max_length=120)
    ordem = models.PositiveIntegerField(default=1)
    ativo = models.BooleanField(default=True)

    class Meta:
        ordering = ["ordem", "nome"]

    def __str__(self):
        return self.nome
