from django import forms

from apps.core.forms import BootstrapModelForm
from apps.funcionarios.models import Funcionario, Planta
from apps.produtos.models import Produto
from apps.depositos.models import Deposito
from apps.estoque.models import Estoque
from .models import AcessoEPI, ConsumoParceiro, EmpresaParceira, Terceiro


class ConsumoParceiroBatchForm(forms.Form):
    empresa_parceira = forms.ModelChoiceField(
        queryset=EmpresaParceira.objects.none(),
        required=True,
        label="Empresa parceira",
    )
    terceiro = forms.ModelChoiceField(
        queryset=Terceiro.objects.none(),
        required=True,
        label="Terceiro",
    )
    produto = forms.ModelChoiceField(
        queryset=Produto.objects.none(),
        required=False,
        label="Produto",
    )
    deposito = forms.ModelChoiceField(
        queryset=Deposito.objects.none(),
        required=False,
        label="Deposito",
    )
    quantidade = forms.DecimalField(
        required=False,
        label="Quantidade",
        min_value=0,
        decimal_places=2,
        max_digits=10,
        initial=1,
        widget=forms.NumberInput(attrs={"min": "0.01", "step": "0.01"}),
    )
    data = forms.DateField(
        required=True,
        label="Data",
        widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
        input_formats=["%Y-%m-%d"],
    )
    observacao = forms.CharField(
        required=False,
        label="Observacao",
        widget=forms.Textarea(attrs={"rows": 2}),
    )

    def __init__(self, *args, tenant=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.tenant = tenant
        self.fields["terceiro"].queryset = Terceiro.objects.none()
        self.fields["deposito"].queryset = Deposito.objects.none()
        if tenant is None:
            return
        self.fields["empresa_parceira"].queryset = EmpresaParceira.objects.filter(
            company=tenant,
            ativo=True,
        ).order_by("nome")
        self.fields["produto"].queryset = Produto.objects.filter(
            company=tenant,
            ativo=True,
        ).order_by("nome")
        depositos = Deposito.objects.filter(company=tenant, ativo=True)
        produto_id = None
        if self.is_bound:
            produto_id = self.data.get("produto") or None
        if produto_id:
            depositos = depositos.filter(estoque__produto_id=produto_id).distinct()
        self.fields["deposito"].queryset = depositos.order_by("nome")
        empresa_id = None
        if self.is_bound:
            empresa_id = self.data.get("empresa_parceira") or None
        if empresa_id:
            self.fields["terceiro"].queryset = Terceiro.objects.filter(
                company=tenant,
                ativo=True,
                empresa_parceira_id=empresa_id,
            ).order_by("nome")

        for field in self.fields.values():
            widget = field.widget
            widget_class = widget.__class__.__name__
            if getattr(widget, "input_type", "") == "checkbox":
                css_class = "form-check-input"
            elif widget_class in {"Select", "SelectMultiple"}:
                css_class = "form-select"
            else:
                css_class = "form-control"
            existing = widget.attrs.get("class", "")
            widget.attrs["class"] = f"{existing} {css_class}".strip()

    def clean(self):
        cleaned = super().clean()
        empresa = cleaned.get("empresa_parceira")
        terceiro = cleaned.get("terceiro")
        if empresa and terceiro and terceiro.empresa_parceira_id != empresa.pk:
            self.add_error("terceiro", "Selecione um terceiro da empresa escolhida.")
        return cleaned


class EmpresaParceiraForm(BootstrapModelForm):
    class Meta:
        model = EmpresaParceira
        fields = ["nome", "documento", "contato", "ativo"]


class TerceiroForm(BootstrapModelForm):
    class Meta:
        model = Terceiro
        fields = ["nome", "documento", "empresa_parceira", "telefone", "ativo"]

    def __init__(self, *args, tenant=None, **kwargs):
        super().__init__(*args, **kwargs)
        if tenant is not None:
            self.fields["empresa_parceira"].queryset = EmpresaParceira.objects.filter(
                company=tenant,
                ativo=True,
            ).order_by("nome")


class AcessoEPIForm(BootstrapModelForm):
    class Meta:
        model = AcessoEPI
        fields = [
            "tipo_pessoa",
            "funcionario",
            "terceiro",
            "planta",
            "data_hora",
            "status_epi",
            "status_treinamento",
            "permitido",
            "observacao",
        ]
        widgets = {
            "data_hora": forms.DateTimeInput(attrs={"type": "datetime-local"}),
        }

    def __init__(self, *args, tenant=None, **kwargs):
        super().__init__(*args, **kwargs)
        if tenant is not None:
            self.fields["funcionario"].queryset = Funcionario.objects.filter(
                company=tenant,
                ativo=True,
            ).order_by("nome")
            self.fields["terceiro"].queryset = Terceiro.objects.filter(
                company=tenant,
                ativo=True,
            ).order_by("nome")
            self.fields["planta"].queryset = Planta.objects.filter(
                company=tenant,
                ativo=True,
            ).order_by("nome")

    def clean(self):
        cleaned = super().clean()
        tipo = cleaned.get("tipo_pessoa")
        funcionario = cleaned.get("funcionario")
        terceiro = cleaned.get("terceiro")
        if tipo == "funcionario" and not funcionario:
            self.add_error("funcionario", "Selecione o funcionario.")
        if tipo == "terceiro" and not terceiro:
            self.add_error("terceiro", "Selecione o terceiro.")
        if tipo == "funcionario":
            cleaned["terceiro"] = None
        if tipo == "terceiro":
            cleaned["funcionario"] = None
        return cleaned


class ConsumoParceiroForm(BootstrapModelForm):
    empresa_parceira = forms.ModelChoiceField(
        queryset=EmpresaParceira.objects.none(),
        required=True,
        label="Empresa parceira",
    )

    class Meta:
        model = ConsumoParceiro
        fields = ["empresa_parceira", "terceiro", "produto", "deposito", "quantidade", "data", "observacao"]
        widgets = {
            "data": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
        }

    def __init__(self, *args, tenant=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.tenant = tenant
        self.fields["data"].input_formats = ["%Y-%m-%d"]
        self.fields["terceiro"].queryset = Terceiro.objects.none()
        if tenant is not None:
            self.fields["empresa_parceira"].queryset = EmpresaParceira.objects.filter(
                company=tenant,
                ativo=True,
            ).order_by("nome")
            terceiro_qs = Terceiro.objects.filter(
                company=tenant,
                ativo=True,
            )
            self.fields["produto"].queryset = Produto.objects.filter(
                company=tenant,
                ativo=True,
            ).order_by("nome")
            depositos = Deposito.objects.filter(company=tenant, ativo=True)
            produto_id = None
            if self.is_bound:
                produto_id = self.data.get(self.add_prefix("produto")) or None
            elif self.instance and self.instance.pk:
                produto_id = self.instance.produto_id
            if produto_id:
                deposito_ids = list(
                    Estoque.objects.filter(company=tenant, produto_id=produto_id)
                    .values_list("deposito_id", flat=True)
                    .distinct()
                )
                depositos = depositos.filter(pk__in=deposito_ids)
            self.fields["deposito"].queryset = depositos.order_by("nome")
            empresa_id = None
            if self.is_bound:
                empresa_id = self.data.get(self.add_prefix("empresa_parceira")) or None
            elif self.instance and self.instance.pk:
                empresa_id = (
                    self.instance.terceiro.empresa_parceira_id
                    if self.instance.terceiro
                    else None
                )
                if empresa_id:
                    self.fields["empresa_parceira"].initial = empresa_id
            if empresa_id:
                terceiro_qs = terceiro_qs.filter(empresa_parceira_id=empresa_id)
            else:
                terceiro_qs = terceiro_qs.none()
            self.fields["terceiro"].queryset = terceiro_qs

    def clean(self):
        cleaned = super().clean()
        empresa = cleaned.get("empresa_parceira")
        terceiro = cleaned.get("terceiro")
        if empresa and terceiro and terceiro.empresa_parceira_id != empresa.pk:
            self.add_error("terceiro", "Selecione um terceiro da empresa escolhida.")
        produto = cleaned.get("produto")
        deposito = cleaned.get("deposito")
        if (
            produto
            and deposito
            and self.tenant is not None
            and not Estoque.objects.filter(company=self.tenant, produto=produto, deposito=deposito).exists()
        ):
            self.add_error("deposito", "Este produto nao esta cadastrado no deposito escolhido.")
        return cleaned
