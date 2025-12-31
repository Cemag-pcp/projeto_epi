from apps.core.views import BaseTenantCreateView, BaseTenantListView, BaseTenantUpdateView
from .forms import ProdutoForm
from .models import Produto


class ProdutoListView(BaseTenantListView):
    model = Produto
    template_name = "produtos/list.html"
    form_class = ProdutoForm
    title = "Produtos"
    headers = ["Nome", "SKU", "Fornecedor", "Ativo"]
    row_fields = ["nome", "sku", "fornecedor", "ativo"]
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
    create_url_name = "produtos:create"
    update_url_name = "produtos:update"


class ProdutoCreateView(BaseTenantCreateView):
    model = Produto
    form_class = ProdutoForm
    success_url_name = "produtos:list"


class ProdutoUpdateView(BaseTenantUpdateView):
    model = Produto
    form_class = ProdutoForm
    success_url_name = "produtos:list"
