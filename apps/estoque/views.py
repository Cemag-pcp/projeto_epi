from django.urls import reverse_lazy

from apps.core.views import BaseTenantCreateView, BaseTenantListView
from .forms import EstoqueForm, MovimentacaoEstoqueForm
from .models import Estoque, MovimentacaoEstoque


class EstoqueListView(BaseTenantListView):
    model = Estoque
    template_name = "estoque/list.html"
    title = "Estoque"
    headers = ["Produto", "Deposito", "Quantidade", "Status"]
    row_fields = ["produto", "deposito", "quantidade", "status"]
    filter_definitions = [
        {"name": "produto__nome", "label": "Produto", "lookup": "icontains", "type": "text"},
        {"name": "deposito__nome", "label": "Deposito", "lookup": "icontains", "type": "text"},
    ]
    create_url_name = "estoque:create"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["create_form"] = EstoqueForm()
        context["movement_rows"] = [
            {
                "object": obj,
                "form": MovimentacaoEstoqueForm(initial={"estoque": obj}),
                "action_url": reverse_lazy("estoque:movimentar"),
            }
            for obj in context["object_list"]
        ]
        return context


class EstoqueCreateView(BaseTenantCreateView):
    model = Estoque
    form_class = EstoqueForm
    success_url_name = "estoque:list"


class MovimentacaoCreateView(BaseTenantCreateView):
    model = MovimentacaoEstoque
    form_class = MovimentacaoEstoqueForm
    success_url_name = "estoque:list"
