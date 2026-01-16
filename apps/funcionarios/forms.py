from django import forms
from django.contrib.auth.hashers import make_password

from apps.core.forms import BootstrapModelForm
from .models import (
    Afastamento,
    CentroCusto,
    Funcionario,
    FuncionarioAnexo,
    FuncionarioProduto,
    GHE,
    Advertencia,
    MotivoAfastamento,
    Planta,
    Risco,
    Turno,
)
from apps.produtos.models import ProdutoFornecedor


class FuncionarioForm(BootstrapModelForm):
    senha_recebimento = forms.CharField(
        label="Senha para recebimento",
        required=False,
        widget=forms.PasswordInput(render_value=False),
    )
    senha_recebimento_confirm = forms.CharField(
        label="Confirmar senha",
        required=False,
        widget=forms.PasswordInput(render_value=False),
    )

    def __init__(self, *args, include_validacao=True, **kwargs):
        self.include_validacao = include_validacao
        super().__init__(*args, **kwargs)
        foto_field = self.fields.get("foto")
        if foto_field:
            foto_field.widget.attrs.update(
                {
                    "class": "visually-hidden",
                    "data-avatar-input": "1",
                    "accept": "image/*",
                }
            )
        for field_name in ("data_nascimento", "data_admissao", "data_demissao", "inicio_ferias", "fim_ferias"):
            field = self.fields.get(field_name)
            if field:
                field.input_formats = ["%Y-%m-%d"]
                field.widget = forms.DateInput(
                    attrs={"type": "date", "class": "form-control"},
                    format="%Y-%m-%d",
                )
        for field_name in ("ativo", "temporario", "afastado"):
            field = self.fields.get(field_name)
            if field:
                field.widget = forms.Select(
                    choices=[("1", "Sim"), ("0", "Nao")],
                    attrs={"class": "form-select"},
                )
                if field_name in {"temporario", "afastado"}:
                    field.initial = "0"
        if not include_validacao:
            self.fields.pop("validacao_recebimento", None)
            self.fields.pop("senha_recebimento", None)
            self.fields.pop("senha_recebimento_confirm", None)
        ghe_field = self.fields.get("ghe")
        if ghe_field is not None:
            ghe_field.queryset = ghe_field.queryset.filter(ativo=True)
        planta_field = self.fields.get("planta")
        if planta_field is not None:
            planta_field.queryset = planta_field.queryset.filter(ativo=True)

    def clean(self):
        cleaned_data = super().clean()
        data_admissao = cleaned_data.get("data_admissao")
        data_demissao = cleaned_data.get("data_demissao")
        inicio_ferias = cleaned_data.get("inicio_ferias")
        fim_ferias = cleaned_data.get("fim_ferias")
        if data_admissao and data_demissao and data_admissao > data_demissao:
            self.add_error("data_demissao", "Data de demissao deve ser maior ou igual a data de admissao.")
        if inicio_ferias and fim_ferias and inicio_ferias > fim_ferias:
            self.add_error("fim_ferias", "Fim de ferias deve ser maior ou igual ao inicio.")
        if self.include_validacao:
            validacao = cleaned_data.get("validacao_recebimento")
            senha = cleaned_data.get("senha_recebimento")
            senha_confirm = cleaned_data.get("senha_recebimento_confirm")
            if validacao == "senha":
                if not senha:
                    self.add_error("senha_recebimento", "Informe a senha para recebimento.")
                if not senha_confirm:
                    self.add_error("senha_recebimento_confirm", "Confirme a senha para recebimento.")
                if senha and senha_confirm and senha != senha_confirm:
                    self.add_error("senha_recebimento_confirm", "As senhas nao conferem.")
            else:
                cleaned_data["senha_recebimento"] = ""
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.include_validacao:
            validacao = self.cleaned_data.get("validacao_recebimento")
            senha = self.cleaned_data.get("senha_recebimento")
            if validacao == "senha" and senha:
                instance.senha_recebimento = make_password(senha)
            if validacao != "senha":
                instance.senha_recebimento = ""
        if commit:
            instance.save()
        return instance

    class Meta:
        model = Funcionario
        fields = [
            "foto",
            "identificador",
            "registro",
            "nome",
            "rg",
            "cpf",
            "pis",
            "data_nascimento",
            "turno",
            "email",
            "telefone",
            "cargo",
            "setor",
            "planta",
            "centro_custo",
            "ghe",
            "lider",
            "gestor",
            "tipo",
            "data_admissao",
            "data_demissao",
            "categoria_cnh",
            "validacao_recebimento",
            "senha_recebimento",
            "senha_recebimento_confirm",
            "ativo",
            "temporario",
            "afastado",
            "inicio_ferias",
            "fim_ferias",
        ]


class AfastamentoForm(BootstrapModelForm):
    motivo = forms.ChoiceField(choices=(), required=True)

    def __init__(self, *args, tenant=None, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name in ("data_inicio", "data_fim"):
            field = self.fields.get(field_name)
            if field:
                field.input_formats = ["%Y-%m-%d"]
                field.widget.format = "%Y-%m-%d"
        queryset = MotivoAfastamento.objects.all()
        if tenant is not None:
            queryset = queryset.filter(company=tenant)
        active_choices = [(motivo.nome, motivo.nome) for motivo in queryset.filter(ativo=True)]
        current_motivo = (getattr(self.instance, "motivo", "") or "").strip()
        if current_motivo and current_motivo not in {value for value, _ in active_choices}:
            self.fields["motivo"].choices = [(current_motivo, current_motivo)] + active_choices
        else:
            self.fields["motivo"].choices = active_choices

    def clean(self):
        cleaned_data = super().clean()
        data_inicio = cleaned_data.get("data_inicio")
        data_fim = cleaned_data.get("data_fim")
        if data_inicio and data_fim and data_inicio > data_fim:
            self.add_error("data_fim", "Data fim deve ser maior ou igual a data inicio.")
        return cleaned_data

    class Meta:
        model = Afastamento
        fields = [
            "funcionario",
            "data_inicio",
            "data_fim",
            "motivo",
            "arquivo",
        ]
        widgets = {
            "data_inicio": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "data_fim": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
        }


class RiscoForm(BootstrapModelForm):
    class Meta:
        model = Risco
        fields = ["nome", "descricao", "nivel", "ativo"]


class RiscoAssignForm(forms.Form):
    riscos = forms.ModelMultipleChoiceField(queryset=Risco.objects.none(), required=False)

    def __init__(self, *args, tenant=None, funcionario=None, **kwargs):
        super().__init__(*args, **kwargs)
        queryset = Risco.objects.all()
        if tenant is not None:
            queryset = queryset.filter(company=tenant)
        self.fields["riscos"].queryset = queryset
        self.fields["riscos"].widget.attrs.update({"class": "form-select", "size": "6"})
        if funcionario is not None:
            self.fields["riscos"].initial = funcionario.riscos.values_list("pk", flat=True)


class FuncionarioAnexoForm(BootstrapModelForm):
    class Meta:
        model = FuncionarioAnexo
        fields = ["arquivo", "descricao"]


class AdvertenciaForm(BootstrapModelForm):
    class Meta:
        model = Advertencia
        fields = ["funcionario", "data", "tipo", "descricao"]
        widgets = {
            "data": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, tenant=None, **kwargs):
        super().__init__(*args, **kwargs)
        if tenant is not None:
            self.fields["funcionario"].queryset = Funcionario.objects.filter(
                company=tenant,
                ativo=True,
            ).order_by("nome")
        data_field = self.fields.get("data")
        if data_field:
            data_field.input_formats = ["%Y-%m-%d"]
            data_field.widget.format = "%Y-%m-%d"


class CentroCustoForm(BootstrapModelForm):
    class Meta:
        model = CentroCusto
        fields = ["nome", "ativo"]


class GHEForm(BootstrapModelForm):
    class Meta:
        model = GHE
        fields = ["codigo", "descricao", "responsavel", "ativo"]


class TurnoForm(BootstrapModelForm):
    class Meta:
        model = Turno
        fields = ["nome", "ativo"]


class MotivoAfastamentoForm(BootstrapModelForm):
    class Meta:
        model = MotivoAfastamento
        fields = ["nome", "ativo"]


class PlantaForm(BootstrapModelForm):
    class Meta:
        model = Planta
        fields = ["nome", "ativo"]


class FuncionarioProdutoForm(BootstrapModelForm):
    def __init__(self, *args, tenant=None, **kwargs):
        super().__init__(*args, **kwargs)
        if tenant is None:
            return
        self.fields["funcionario"].queryset = Funcionario.objects.filter(
            company=tenant,
            ativo=True,
        ).order_by("nome")
        self.fields["produto_fornecedor"].queryset = (
            ProdutoFornecedor.objects.filter(company=tenant, produto__ativo=True)
            .select_related("produto", "fornecedor")
            .order_by("produto__nome", "fornecedor__nome")
        )
        self.fields["produto_fornecedor"].label_from_instance = (
            lambda obj: f"{obj.produto} | CA {obj.ca or '-'} | {obj.fornecedor}"
        )

    class Meta:
        model = FuncionarioProduto
        fields = ["funcionario", "produto_fornecedor"]


class FuncionarioValidacaoForm(forms.Form):
    validacao_recebimento = forms.ChoiceField(
        choices=Funcionario.VALIDACAO_RECEBIMENTO_CHOICES,
        required=True,
        label="Tipo de validacao",
    )
    senha_recebimento = forms.CharField(
        label="Senha para recebimento",
        required=False,
        widget=forms.PasswordInput(render_value=False),
    )
    senha_recebimento_confirm = forms.CharField(
        label="Confirmar senha",
        required=False,
        widget=forms.PasswordInput(render_value=False),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
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
        cleaned_data = super().clean()
        validacao = cleaned_data.get("validacao_recebimento")
        senha = cleaned_data.get("senha_recebimento")
        senha_confirm = cleaned_data.get("senha_recebimento_confirm")
        if validacao == "senha":
            if not senha:
                self.add_error("senha_recebimento", "Informe a senha para recebimento.")
            if not senha_confirm:
                self.add_error("senha_recebimento_confirm", "Confirme a senha para recebimento.")
            if senha and senha_confirm and senha != senha_confirm:
                self.add_error("senha_recebimento_confirm", "As senhas nao conferem.")
        else:
            cleaned_data["senha_recebimento"] = ""
            cleaned_data["senha_recebimento_confirm"] = ""
        return cleaned_data
