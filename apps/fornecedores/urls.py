from django.urls import path

from . import views

app_name = "fornecedores"

urlpatterns = [
    path("fornecedores/", views.FornecedorListView.as_view(), name="list"),
    path("fornecedores/novo/", views.FornecedorCreateView.as_view(), name="create"),
    path("fornecedores/<int:pk>/editar/", views.FornecedorUpdateView.as_view(), name="update"),
]
