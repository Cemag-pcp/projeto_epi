from apps.core.forms import BootstrapModelForm
from .models import TipoFuncionario


class TipoFuncionarioForm(BootstrapModelForm):
    class Meta:
        model = TipoFuncionario
        fields = ["nome", "descricao", "ativo"]
