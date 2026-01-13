from django import forms

from apps.core.forms import BootstrapModelForm
from apps.funcionarios.models import Funcionario, Planta
from apps.produtos.models import Produto
from .models import AcessoEPI, ConsumoParceiro, EmpresaParceira, Terceiro


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
        fields = ["empresa_parceira", "terceiro", "produto", "quantidade", "data", "observacao"]
        widgets = {
            "data": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
        }

    def __init__(self, *args, tenant=None, **kwargs):
        super().__init__(*args, **kwargs)
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
            self.add_error("terceiro", "Selecione um funcionario da empresa escolhida.")
        return cleaned
