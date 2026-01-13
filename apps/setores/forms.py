from apps.core.forms import BootstrapModelForm
from .models import Setor


class SetorForm(BootstrapModelForm):
    class Meta:
        model = Setor
        fields = ["nome", "descricao", "responsaveis", "ativo"]
