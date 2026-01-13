from apps.core.forms import BootstrapModelForm
from apps.funcionarios.models import Planta
from .models import Deposito


class DepositoForm(BootstrapModelForm):
    def __init__(self, *args, tenant=None, planta_id=None, **kwargs):
        super().__init__(*args, **kwargs)
        plantas = Planta.objects.none()
        if tenant is not None:
            plantas = Planta.objects.filter(company=tenant, ativo=True)
        if planta_id:
            plantas = plantas.filter(pk=planta_id)
        self.fields["planta"].queryset = plantas.order_by("nome")
        if planta_id and plantas.exists():
            self.fields["planta"].initial = planta_id

    class Meta:
        model = Deposito
        fields = ["nome", "endereco", "planta", "bloquear_movimento_negativo", "ativo"]
