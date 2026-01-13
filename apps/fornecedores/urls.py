from django.urls import path

from . import views

app_name = "fornecedores"

urlpatterns = [
    path("fornecedores/", views.FornecedorListView.as_view(), name="list"),
    path("fornecedores/novo/", views.FornecedorCreateView.as_view(), name="create"),
    path("fornecedores/<int:pk>/editar/", views.FornecedorUpdateView.as_view(), name="update"),
    path("fornecedores/<int:pk>/toggle/", views.FornecedorToggleActiveView.as_view(), name="toggle_active"),
    path("fornecedores/<int:pk>/excluir/", views.FornecedorDeleteView.as_view(), name="delete"),
    path("fornecedores/<int:pk>/uso/", views.FornecedorUsoView.as_view(), name="usage"),
]
