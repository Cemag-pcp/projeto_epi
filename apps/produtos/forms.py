from django import forms
from django.utils import timezone

from django_tenants.utils import schema_context

from apps.core.forms import BootstrapModelForm
from apps.caepi.models import CaEPI
from apps.fornecedores.models import Fornecedor
from .models import (
    FamiliaProduto,
    Fabricante,
    LocalizacaoProduto,
    LocalRetirada,
    Periodicidade,
    Produto,
    SubfamiliaProduto,
    TipoProduto,
    UnidadeProduto,
)


class ProdutoForm(BootstrapModelForm):
    fornecedor = forms.ModelChoiceField(
        queryset=Fornecedor.objects.none(),
        required=False,
        label="Fornecedor",
    )

    def __init__(self, *args, tenant=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.tenant = tenant
        ca_field = self.fields.get("ca")
        if ca_field is not None:
            ca_field.required = False
            ca_field.widget.attrs.setdefault("autocomplete", "off")
            ca_field.widget.attrs.setdefault("inputmode", "numeric")
        vencimento_field = self.fields.get("data_vencimento_ca")
        if vencimento_field is not None:
            vencimento_field.widget.attrs.pop("readonly", None)

        fornecedor_field = self.fields.get("fornecedor")
        if fornecedor_field is not None:
            fornecedor_field.queryset = Fornecedor.objects.filter(ativo=True).order_by("nome")
        familia_field = self.fields.get("familia")
        if familia_field is not None:
            familia_field.queryset = familia_field.queryset.filter(ativo=True)
        subfamilia_field = self.fields.get("subfamilia")
        if subfamilia_field is not None:
            subfamilia_field.queryset = subfamilia_field.queryset.filter(ativo=True)
        localizacao_field = self.fields.get("localizacao")
        if localizacao_field is not None:
            localizacao_field.queryset = localizacao_field.queryset.filter(ativo=True).order_by("ordem", "nome")
        periodicidade_field = self.fields.get("periodicidade")
        if periodicidade_field is not None:
            periodicidade_field.queryset = periodicidade_field.queryset.filter(ativo=True)
        fabricante_field = self.fields.get("fabricante")
        if fabricante_field is not None:
            fabricante_field.queryset = Fabricante.objects.filter(ativo=True).order_by("nome")
            existing = fabricante_field.widget.attrs.get("class", "")
            if "d-none" not in existing.split():
                fabricante_field.widget.attrs["class"] = f"{existing} d-none".strip()
            fabricante_field.widget.attrs.setdefault("tabindex", "-1")
            fabricante_field.widget.attrs.setdefault("aria-hidden", "true")

    def clean_ca(self):
        ca = (self.cleaned_data.get("ca") or "").strip()
        return ca

    def clean_codigo(self):
        codigo = (self.cleaned_data.get("codigo") or "").strip()
        if not codigo:
            raise forms.ValidationError("Informe o codigo.")
        if getattr(self.instance, "company_id", None):
            qs = Produto.objects.filter(company_id=self.instance.company_id)
        elif self.tenant is not None:
            qs = Produto.objects.filter(company=self.tenant)
        else:
            qs = Produto.objects.none()
        if getattr(self.instance, "pk", None):
            qs = qs.exclude(pk=self.instance.pk)
        if qs.filter(codigo__iexact=codigo).exists():
            raise forms.ValidationError("Codigo ja cadastrado.")
        return codigo

    def clean(self):
        cleaned_data = super().clean()
        ca = (cleaned_data.get("ca") or "").strip()
        if not ca:
            return cleaned_data

        today = timezone.localdate()
        with schema_context("public"):
            caepi = (
                CaEPI.objects.filter(registro_ca=ca)
                .order_by("-data_validade", "-ultima_atualizacao")
                .first()
            )
        if caepi and caepi.data_validade:
            if not cleaned_data.get("data_vencimento_ca"):
                cleaned_data["data_vencimento_ca"] = caepi.data_validade
            if caepi.data_validade < today:
                self.add_error("ca", "CA vencido.")
        return cleaned_data

    class Meta:
        model = Produto
        fields = [
            "nome",
            "foto",
            "codigo",
            "ca",
            "data_vencimento_ca",
            "referencia",
            "periodicidade_quantidade",
            "periodicidade",
            "unidade",
            "tipo",
            "familia",
            "subfamilia",
            "localizacao",
            "imposto_ipi",
            "imposto_st",
            "imposto_outros",
            "marca",
            "fabricante",
            "monitora_uso",
            "troca_funcionario",
            "controle_epi",
            "obrigar_entrega",
            "dias_entrega",
            "estoque_minimo",
            "estoque_ideal",
            "ativo",
        ]
        widgets = {
            "data_vencimento_ca": forms.DateInput(attrs={"type": "date"}),
        }


class TipoProdutoForm(BootstrapModelForm):
    class Meta:
        model = TipoProduto
        fields = ["nome"]


class FamiliaProdutoForm(BootstrapModelForm):
    class Meta:
        model = FamiliaProduto
        fields = ["nome", "ativo"]


class SubfamiliaProdutoForm(BootstrapModelForm):
    class Meta:
        model = SubfamiliaProduto
        fields = ["nome", "ativo"]


class LocalRetiradaForm(BootstrapModelForm):
    class Meta:
        model = LocalRetirada
        fields = ["nome", "ativo"]


class PeriodicidadeForm(BootstrapModelForm):
    class Meta:
        model = Periodicidade
        fields = ["nome", "fator_dias", "ativo"]


class LocalizacaoProdutoForm(BootstrapModelForm):
    class Meta:
        model = LocalizacaoProduto
        fields = ["nome", "ordem", "ativo"]


class UnidadeProdutoForm(BootstrapModelForm):
    class Meta:
        model = UnidadeProduto
        fields = ["nome", "sigla"]
