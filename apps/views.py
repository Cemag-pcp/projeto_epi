from django.urls import reverse_lazy
from apps.core.views import BaseTenantCreateView, BaseTenantListView, BaseTenantUpdateView
from .forms import Form
from .models import 

class ListView(BaseTenantListView):
    model = 
    form_class = Form
    title = ""
    headers = [""]
    row_fields = [""]
    filter_definitions = [
        {"name": "nome", "label": "Nome", "lookup": "icontains", "type": "text"},
        {"name": "ativo", "label": "Ativo", "lookup": "exact_bool", "type": "select", "options": [("", "Todos"), ("1", "Ativo"), ("0", "Inativo")]},
    ]
    create_url_name = ""
    update_url_name = ""
class CreateView(BaseTenantCreateView):
    model = 
    form_class = Form
    success_url_name = ""
class UpdateView(BaseTenantUpdateView):
    model = 
    form_class = Form
    success_url_name = ""