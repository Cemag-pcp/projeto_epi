from apps.core.views import BaseTenantCreateView, BaseTenantListView, BaseTenantUpdateView
from .forms import FornecedorForm
from .models import Fornecedor


class FornecedorListView(BaseTenantListView):
    model = Fornecedor
    template_name = "fornecedores/list.html"
    form_class = FornecedorForm
    title = "Fornecedores"
    headers = ["Nome", "Documento", "Email", "Ativo"]
    row_fields = ["nome", "documento", "email", "ativo"]
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
    create_url_name = "fornecedores:create"
    update_url_name = "fornecedores:update"


class FornecedorCreateView(BaseTenantCreateView):
    model = Fornecedor
    form_class = FornecedorForm
    success_url_name = "fornecedores:list"


class FornecedorUpdateView(BaseTenantUpdateView):
    model = Fornecedor
    form_class = FornecedorForm
    success_url_name = "fornecedores:list"
