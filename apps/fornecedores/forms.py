from apps.core.forms import BootstrapModelForm
from .models import Fornecedor


class FornecedorForm(BootstrapModelForm):
    class Meta:
        model = Fornecedor
        fields = ["nome", "documento", "email", "telefone", "ativo"]
