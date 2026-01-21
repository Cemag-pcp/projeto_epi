from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone

from apps.core.models import TenantModel

MAX_ATTACHMENT_SIZE = 3 * 1024 * 1024  # 3MB


def validate_attachment_size(value):
    if value.size > MAX_ATTACHMENT_SIZE:
        raise ValidationError("Arquivo excede o limite de 3MB.")


class Produto(TenantModel):
    nome = models.CharField(max_length=200)
    foto = models.ImageField(upload_to="produtos/fotos/", null=True, blank=True)
    codigo = models.CharField(max_length=80)
    ca = models.CharField(max_length=50, blank=True)
    data_vencimento_ca = models.DateField(null=True, blank=True)
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
    fornecedores = models.ManyToManyField(
        "fornecedores.Fornecedor", through="ProdutoFornecedor", related_name="produtos", blank=True
    )
    estoque_minimo = models.PositiveIntegerField(default=0, null=True, blank=True)
    estoque_ideal = models.PositiveIntegerField(default=0, null=True, blank=True)
    ativo = models.BooleanField(default=True)
    fabricante = models.ForeignKey(
        "Fabricante",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="produtos",
    )

    def __str__(self):
        return self.nome

    def periodicidade_label(self):
        if not self.periodicidade:
            return "-"
        quantidade = self.periodicidade_quantidade or 0
        return f"{quantidade} {self.periodicidade}"

    def clean(self):
        if self.controle_epi:
            if not self.ca:
                raise ValidationError("Produto EPI deve possuir CA.")
            if not self.data_vencimento_ca:
                raise ValidationError("Produto EPI deve possuir data de validade do CA.")
            if self.data_vencimento_ca < timezone.now().date():
                raise ValidationError("CA vencido.")
            if not self.fabricante:
                raise ValidationError("Produto EPI deve possuir fabricante.")

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["company", "codigo"],
                condition=~Q(codigo=""),
                name="produtos_produto_company_codigo_uniq",
            )
        ]



class ProdutoFornecedor(TenantModel):
    produto = models.ForeignKey(Produto, on_delete=models.CASCADE, related_name="fornecedores_rel")
    fornecedor = models.ForeignKey("fornecedores.Fornecedor", on_delete=models.CASCADE)
    codigo_barras = models.CharField(max_length=64, null=True, blank=True)
    codigo_fornecedor = models.CharField(max_length=80, null=True, blank=True)
    valor = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
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

class Fabricante(TenantModel):
    nome = models.CharField(max_length=200)
    nome_fantasia = models.CharField(max_length=200, blank=True)
    cnpj = models.CharField(max_length=18, blank=True)  # pode validar depois
    ie = models.CharField(max_length=30, blank=True)

    email = models.EmailField(blank=True)
    telefone = models.CharField(max_length=30, blank=True)
    site = models.URLField(blank=True)

    endereco = models.CharField(max_length=255, blank=True)
    cidade = models.CharField(max_length=120, blank=True)
    uf = models.CharField(max_length=2, blank=True)
    cep = models.CharField(max_length=12, blank=True)

    observacao = models.TextField(blank=True, null=True)
    ativo = models.BooleanField(default=True)

    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Fabricante"
        verbose_name_plural = "Fabricantes"
        ordering = ["nome"]
        indexes = [
            models.Index(fields=["nome"]),
            models.Index(fields=["cnpj"]),
        ]

    def __str__(self):
        return self.nome

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
