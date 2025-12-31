from apps.core.forms import BootstrapModelForm
from .models import Deposito


class DepositoForm(BootstrapModelForm):
    class Meta:
        model = Deposito
        fields = ["nome", "endereco", "ativo"]
