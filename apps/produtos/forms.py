from apps.core.forms import BootstrapModelForm
from .models import (
    FamiliaProduto,
    LocalizacaoProduto,
    LocalRetirada,
    Periodicidade,
    Produto,
    SubfamiliaProduto,
    TipoProduto,
)


class ProdutoForm(BootstrapModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        fornecedor_field = self.fields.get("fornecedor")
        if fornecedor_field is not None:
            fornecedor_field.queryset = fornecedor_field.queryset.filter(ativo=True)
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

    class Meta:
        model = Produto
        fields = [
            "nome",
            "foto",
            "sku",
            "codigo_externo",
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
            "monitora_uso",
            "troca_funcionario",
            "controle_epi",
            "obrigar_entrega",
            "dias_entrega",
            "fornecedor",
            "estoque_minimo",
            "estoque_ideal",
            "ativo",
        ]


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
