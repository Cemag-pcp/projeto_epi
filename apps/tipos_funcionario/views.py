from apps.core.views import BaseTenantCreateView, BaseTenantListView, BaseTenantUpdateView
from .forms import TipoFuncionarioForm
from .models import TipoFuncionario


class TipoFuncionarioListView(BaseTenantListView):
    model = TipoFuncionario
    template_name = "tipos_funcionario/list.html"
    form_class = TipoFuncionarioForm
    title = "Tipos de Funcionario"
    headers = ["Nome", "Descricao", "Ativo"]
    row_fields = ["nome", "descricao", "ativo"]
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
    create_url_name = "tipos_funcionario:create"
    update_url_name = "tipos_funcionario:update"


class TipoFuncionarioCreateView(BaseTenantCreateView):
    model = TipoFuncionario
    form_class = TipoFuncionarioForm
    success_url_name = "tipos_funcionario:list"


class TipoFuncionarioUpdateView(BaseTenantUpdateView):
    model = TipoFuncionario
    form_class = TipoFuncionarioForm
    success_url_name = "tipos_funcionario:list"
