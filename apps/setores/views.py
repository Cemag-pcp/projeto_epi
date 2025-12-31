from apps.core.views import BaseTenantCreateView, BaseTenantListView, BaseTenantUpdateView
from .forms import SetorForm
from .models import Setor


class SetorListView(BaseTenantListView):
    model = Setor
    template_name = "setores/list.html"
    form_class = SetorForm
    title = "Setores"
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
    create_url_name = "setores:create"
    update_url_name = "setores:update"


class SetorCreateView(BaseTenantCreateView):
    model = Setor
    form_class = SetorForm
    success_url_name = "setores:list"


class SetorUpdateView(BaseTenantUpdateView):
    model = Setor
    form_class = SetorForm
    success_url_name = "setores:list"
