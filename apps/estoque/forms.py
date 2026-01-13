from django import forms

from apps.core.forms import BootstrapModelForm
from apps.depositos.models import Deposito
from .models import Estoque, MovimentacaoEstoque


class MovimentacaoEstoqueForm(BootstrapModelForm):
    def __init__(self, *args, tenant=None, planta_id=None, **kwargs):
        super().__init__(*args, **kwargs)
        if "deposito_destino" in self.fields:
            depositos = Deposito.objects.none()
            if tenant is not None:
                depositos = Deposito.objects.filter(company=tenant, ativo=True)
            if planta_id:
                depositos = depositos.filter(planta_id=planta_id)
            self.fields["deposito_destino"].queryset = depositos.order_by("nome")

    class Meta:
        model = MovimentacaoEstoque
        fields = ["estoque", "tipo", "quantidade", "deposito_destino", "observacao"]
        widgets = {
            "estoque": forms.HiddenInput(),
        }


class EstoqueForm(BootstrapModelForm):
    def __init__(self, *args, tenant=None, planta_id=None, **kwargs):
        super().__init__(*args, **kwargs)
        depositos = Deposito.objects.none()
        if tenant is not None:
            depositos = Deposito.objects.filter(company=tenant, ativo=True)
        if planta_id:
            depositos = depositos.filter(planta_id=planta_id)
        if "deposito" in self.fields:
            self.fields["deposito"].queryset = depositos.order_by("nome")

    class Meta:
        model = Estoque
        fields = ["produto", "deposito", "quantidade"]
