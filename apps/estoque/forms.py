from django import forms

from apps.core.forms import BootstrapModelForm
from apps.depositos.models import Deposito
from apps.produtos.models import Produto
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
    grade = forms.ChoiceField(
        label="Grade",
        required=False,
        choices=[],
    )

    def __init__(self, *args, tenant=None, planta_id=None, **kwargs):
        super().__init__(*args, **kwargs)
        depositos = Deposito.objects.none()
        if tenant is not None:
            depositos = Deposito.objects.filter(company=tenant, ativo=True)
        if planta_id:
            depositos = depositos.filter(planta_id=planta_id)
        if "deposito" in self.fields:
            self.fields["deposito"].queryset = depositos.order_by("nome")

        self.fields["grade"].widget.attrs.update({"class": "form-select"})
        self.fields["grade"].widget.attrs["disabled"] = True
        self.fields["grade"].choices = [("", "Selecione um produto")]

        produto_id = None
        if self.data:
            produto_id = self.data.get("produto")
        elif getattr(self.instance, "produto_id", None):
            produto_id = self.instance.produto_id
        if produto_id and tenant is not None:
            produto = Produto.objects.filter(company=tenant, pk=produto_id).first()
            grades = produto.grade_opcoes() if produto else []
            if grades:
                self.fields["grade"].choices = [("", "Selecione")] + [(g, g) for g in grades]
                self.fields["grade"].widget.attrs.pop("disabled", None)
            else:
                self.fields["grade"].choices = [("", "Sem Grade")]
                self.fields["grade"].widget.attrs["disabled"] = True

    def clean(self):
        cleaned_data = super().clean()
        produto = cleaned_data.get("produto")
        grade = (cleaned_data.get("grade") or "").strip()
        if not produto:
            return cleaned_data
        grades = produto.grade_opcoes() if produto else []
        if grades and not grade:
            self.add_error("grade", "Selecione a grade do produto.")
        if grade and grade not in grades:
            self.add_error("grade", "Grade invalida para o produto selecionado.")
        cleaned_data["grade"] = grade
        return cleaned_data

    class Meta:
        model = Estoque
        fields = ["produto", "grade", "deposito", "quantidade"]
