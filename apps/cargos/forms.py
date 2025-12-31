from apps.core.forms import BootstrapModelForm
from .models import Cargo


class CargoForm(BootstrapModelForm):
    class Meta:
        model = Cargo
        fields = ["nome", "descricao", "setor", "ativo"]
