from django import forms
from django.db.models import Q

from apps.core.forms import BootstrapModelForm
from apps.depositos.models import Deposito
from apps.estoque.models import Estoque
from apps.funcionarios.models import Funcionario, FuncionarioProduto
from apps.produtos.models import ProdutoFornecedor
from apps.tipos_funcionario.models import TipoFuncionarioProduto
from .models import Entrega


class EntregaForm(BootstrapModelForm):
    produto_fornecedor = forms.ModelChoiceField(
        label="Produto / CA",
        queryset=ProdutoFornecedor.objects.none(),
    )

    class Meta:
        model = Entrega
        fields = ["funcionario", "produto_fornecedor", "deposito", "quantidade", "observacao"]

    def __init__(self, *args, tenant=None, planta_id=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.tenant = tenant
        funcionarios = Funcionario.objects.all()
        depositos = Deposito.objects.none()
        produtos_fornecedor = ProdutoFornecedor.objects.none()
        if tenant is not None:
            funcionarios = funcionarios.filter(company=tenant, ativo=True)
            depositos = depositos.filter(company=tenant, ativo=True)
            produtos_fornecedor = produtos_fornecedor.filter(company=tenant)
        if planta_id:
            funcionarios = funcionarios.filter(planta_id=planta_id)
            depositos = depositos.filter(planta_id=planta_id)
        self.fields["funcionario"].queryset = funcionarios.order_by("nome")
        self.fields["deposito"].queryset = depositos
        self.fields["produto_fornecedor"].queryset = produtos_fornecedor
        self.fields["produto_fornecedor"].label_from_instance = (
            lambda obj: f"{obj.produto} | CA {obj.produto.ca or '-'} | {obj.fornecedor}"
        )
        self.fields["produto_fornecedor"].widget.attrs.update({"class": "form-select"})
        self.fields["produto_fornecedor"].widget.attrs["disabled"] = True
        self.fields["deposito"].widget.attrs["disabled"] = True
        self.fields["quantidade"].widget.attrs.update({"min": "0.01", "step": "0.01"})

        if self.data:
            funcionario_id = self.data.get("funcionario")
            if funcionario_id and tenant is not None:
                restrictions_exist = (
                    FuncionarioProduto.objects.filter(company=tenant).exists()
                    or TipoFuncionarioProduto.objects.filter(company=tenant).exists()
                )
                if not restrictions_exist:
                    produtos_fornecedor = (
                        ProdutoFornecedor.objects.filter(company=tenant, produto__ativo=True)
                        .select_related("produto", "fornecedor")
                        .order_by("produto__nome", "fornecedor__nome")
                    )
                    self.fields["produto_fornecedor"].queryset = produtos_fornecedor
                    self.fields["produto_fornecedor"].widget.attrs.pop("disabled", None)
                else:
                    produtos_fornecedor = ProdutoFornecedor.objects.filter(
                        company=tenant,
                        funcionarios_disponiveis__funcionario_id=funcionario_id,
                        funcionarios_disponiveis__ativo=True,
                        produto__ativo=True,
                    ).select_related("produto", "fornecedor")
                    tipo_id = (
                        Funcionario.objects.filter(company=tenant, pk=funcionario_id)
                        .values_list("tipo_id", flat=True)
                        .first()
                    )
                    if tipo_id:
                        produtos_fornecedor = ProdutoFornecedor.objects.filter(
                            company=tenant,
                            produto__ativo=True,
                        ).filter(
                            Q(funcionarios_disponiveis__funcionario_id=funcionario_id)
                            | Q(tipos_funcionario_disponiveis__tipo_funcionario_id=tipo_id)
                        ).select_related("produto", "fornecedor").distinct()
                    if produtos_fornecedor.exists():
                        self.fields["produto_fornecedor"].queryset = produtos_fornecedor.order_by(
                            "produto__nome", "fornecedor__nome"
                        )
                        self.fields["produto_fornecedor"].widget.attrs.pop("disabled", None)
            produto_fornecedor_id = self.data.get("produto_fornecedor")
            if produto_fornecedor_id and tenant is not None:
                produto_id = (
                    ProdutoFornecedor.objects.filter(company=tenant, pk=produto_fornecedor_id)
                    .values_list("produto_id", flat=True)
                    .first()
                )
                if produto_id:
                    depositos_filters = {
                        "company": tenant,
                        "produto_id": produto_id,
                        "deposito__ativo": True,
                    }
                    if planta_id:
                        depositos_filters["deposito__planta_id"] = planta_id
                    depositos = (
                        Estoque.objects.filter(**depositos_filters)
                        .select_related("deposito")
                        .order_by("deposito__nome")
                    )
                    deposito_ids = [item.deposito_id for item in depositos]
                    self.fields["deposito"].queryset = Deposito.objects.filter(pk__in=deposito_ids)
                    self.fields["deposito"].widget.attrs.pop("disabled", None)

    def save(self, commit=True):
        instance = super().save(commit=False)
        produto_fornecedor = self.cleaned_data.get("produto_fornecedor")
        if produto_fornecedor:
            instance.produto = produto_fornecedor.produto
            instance.ca = (produto_fornecedor.produto.ca or "").strip()
        if commit:
            instance.save()
        return instance
