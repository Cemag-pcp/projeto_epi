from apps.core.views import BaseTenantCreateView, BaseTenantListView, BaseTenantUpdateView
from .forms import DepositoForm
from .models import Deposito


class DepositoListView(BaseTenantListView):
    model = Deposito
    template_name = "depositos/list.html"
    form_class = DepositoForm
    title = "Depositos"
    headers = ["Nome", "Endereco", "Ativo"]
    row_fields = ["nome", "endereco", "ativo"]
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
    create_url_name = "depositos:create"
    update_url_name = "depositos:update"


class DepositoCreateView(BaseTenantCreateView):
    model = Deposito
    form_class = DepositoForm
    success_url_name = "depositos:list"


class DepositoUpdateView(BaseTenantUpdateView):
    model = Deposito
    form_class = DepositoForm
    success_url_name = "depositos:list"
