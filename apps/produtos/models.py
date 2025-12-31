from django.core.exceptions import ValidationError
from django.db import models

from apps.core.models import TenantModel

MAX_ATTACHMENT_SIZE = 3 * 1024 * 1024  # 3MB


def validate_attachment_size(value):
    if value.size > MAX_ATTACHMENT_SIZE:
        raise ValidationError("Arquivo excede o limite de 3MB.")


class Produto(TenantModel):
    nome = models.CharField(max_length=200)
    sku = models.CharField(max_length=80, blank=True)
    fornecedor = models.ForeignKey("fornecedores.Fornecedor", on_delete=models.SET_NULL, null=True, blank=True)
    fornecedores = models.ManyToManyField(
        "fornecedores.Fornecedor", through="ProdutoFornecedor", related_name="produtos", blank=True
    )
    ativo = models.BooleanField(default=True)

    def __str__(self):
        return self.nome


class ProdutoFornecedor(TenantModel):
    produto = models.ForeignKey(Produto, on_delete=models.CASCADE, related_name="fornecedores_rel")
    fornecedor = models.ForeignKey("fornecedores.Fornecedor", on_delete=models.CASCADE)
    valor = models.DecimalField(max_digits=12, decimal_places=2)
    observacao = models.TextField(blank=True)

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
