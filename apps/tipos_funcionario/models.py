from django.db import models

from apps.core.models import TenantModel


class TipoFuncionario(TenantModel):
    nome = models.CharField(max_length=150)
    descricao = models.TextField(blank=True)
    ativo = models.BooleanField(default=True)

    def __str__(self):
        return self.nome


class TipoFuncionarioProduto(TenantModel):
    tipo_funcionario = models.ForeignKey(
        TipoFuncionario,
        on_delete=models.CASCADE,
        related_name="produtos_disponiveis",
    )
    produto_fornecedor = models.ForeignKey(
        "produtos.ProdutoFornecedor",
        on_delete=models.CASCADE,
        related_name="tipos_funcionario_disponiveis",
    )

    class Meta:
        unique_together = ("tipo_funcionario", "produto_fornecedor")

    def __str__(self):
        return f"{self.tipo_funcionario} - {self.produto_fornecedor}"
