from django import forms

from apps.core.forms import BootstrapModelForm
from .models import Afastamento, Funcionario


class FuncionarioForm(BootstrapModelForm):
    class Meta:
        model = Funcionario
        fields = [
            "foto",
            "registro",
            "nome",
            "turno",
            "email",
            "telefone",
            "cargo",
            "setor",
            "centro_custo",
            "ghe",
            "lider",
            "gestor",
            "tipo",
            "data_admissao",
            "ativo",
        ]


class AfastamentoForm(BootstrapModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name in ("data_inicio", "data_fim"):
            field = self.fields.get(field_name)
            if field:
                field.input_formats = ["%Y-%m-%d"]
                field.widget.format = "%Y-%m-%d"

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
