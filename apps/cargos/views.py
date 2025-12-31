from apps.core.views import BaseTenantCreateView, BaseTenantListView, BaseTenantUpdateView
from .forms import CargoForm
from .models import Cargo


class CargoListView(BaseTenantListView):
    model = Cargo
    template_name = "cargos/list.html"
    form_class = CargoForm
    title = "Cargos"
    headers = ["Nome", "Setor", "Ativo"]
    row_fields = ["nome", "setor", "ativo"]
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
    create_url_name = "cargos:create"
    update_url_name = "cargos:update"


class CargoCreateView(BaseTenantCreateView):
    model = Cargo
    form_class = CargoForm
    success_url_name = "cargos:list"


class CargoUpdateView(BaseTenantUpdateView):
    model = Cargo
    form_class = CargoForm
    success_url_name = "cargos:list"
