from apps.core.views import (
    BaseTenantCreateView,
    BaseTenantDetailView,
    BaseTenantListView,
    BaseTenantUpdateView,
)
from .forms import FuncionarioForm
from .models import Funcionario


class FuncionarioListView(BaseTenantListView):
    model = Funcionario
    template_name = "funcionarios/list.html"
    form_class = FuncionarioForm
    title = "Funcionarios"
    headers = ["Nome", "Cargo", "Setor", "Tipo", "Ativo"]
    row_fields = ["nome", "cargo", "setor", "tipo", "ativo"]
    filter_definitions = [
        {"name": "nome", "label": "Nome", "lookup": "icontains", "type": "text"},
        {
            "name": "ativo",
            "label": "Ativo",
            "lookup": "exact_bool",
            "type": "select",
            "options": [("", "Todos"), ("1", "Ativo"), ("0", "Inativo")],
        },
    ]
    create_url_name = "funcionarios:create"
    update_url_name = "funcionarios:update"


class FuncionarioCreateView(BaseTenantCreateView):
    model = Funcionario
    form_class = FuncionarioForm
    success_url_name = "funcionarios:list"


class FuncionarioUpdateView(BaseTenantUpdateView):
    model = Funcionario
    form_class = FuncionarioForm
    success_url_name = "funcionarios:list"


class FuncionarioDetailView(BaseTenantDetailView):
    model = Funcionario
    template_name = "funcionarios/detail.html"
