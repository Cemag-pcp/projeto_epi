from apps.core.forms import BootstrapModelForm
from apps.produtos.models import ProdutoFornecedor
from .models import TipoFuncionario, TipoFuncionarioProduto


class TipoFuncionarioForm(BootstrapModelForm):
    class Meta:
        model = TipoFuncionario
        fields = ["nome", "descricao", "ativo"]


class TipoFuncionarioProdutoForm(BootstrapModelForm):
    class Meta:
        model = TipoFuncionarioProduto
        fields = ["tipo_funcionario", "produto_fornecedor"]
        labels = {"tipo_funcionario": "Tipo de funcionario", "produto_fornecedor": "Produto / CA"}

    def __init__(self, *args, tenant=None, **kwargs):
        super().__init__(*args, **kwargs)
        tipos = TipoFuncionario.objects.filter(ativo=True)
        produtos = ProdutoFornecedor.objects.select_related("produto", "fornecedor")
        if tenant is not None:
            tipos = tipos.filter(company=tenant)
            produtos = produtos.filter(company=tenant, produto__ativo=True)
        self.fields["tipo_funcionario"].queryset = tipos.order_by("nome")
        self.fields["produto_fornecedor"].queryset = produtos.order_by("produto__nome", "fornecedor__nome")
        self.fields["produto_fornecedor"].label_from_instance = (
            lambda obj: f"{obj.produto} | CA {obj.ca or '-'} | {obj.fornecedor}"
        )
