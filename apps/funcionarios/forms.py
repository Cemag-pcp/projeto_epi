from apps.core.forms import BootstrapModelForm
from .models import Funcionario


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
