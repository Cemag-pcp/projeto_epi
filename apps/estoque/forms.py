from django import forms

from apps.core.forms import BootstrapModelForm
from .models import Estoque, MovimentacaoEstoque


class MovimentacaoEstoqueForm(BootstrapModelForm):
    class Meta:
        model = MovimentacaoEstoque
        fields = ["estoque", "tipo", "quantidade", "deposito_destino", "observacao"]
        widgets = {
            "estoque": forms.HiddenInput(),
        }


class EstoqueForm(BootstrapModelForm):
    class Meta:
        model = Estoque
        fields = ["produto", "deposito", "quantidade"]