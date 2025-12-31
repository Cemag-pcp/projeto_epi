from apps.core.forms import BootstrapModelForm
from .models import Produto


class ProdutoForm(BootstrapModelForm):
    class Meta:
        model = Produto
        fields = ["nome", "sku", "fornecedor", "ativo"]
