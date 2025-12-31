from django.urls import path

from . import views

app_name = "tipos_funcionario"

urlpatterns = [
    path("tipos_funcionario/", views.TipoFuncionarioListView.as_view(), name="list"),
    path("tipos_funcionario/novo/", views.TipoFuncionarioCreateView.as_view(), name="create"),
    path("tipos_funcionario/<int:pk>/editar/", views.TipoFuncionarioUpdateView.as_view(), name="update"),
]
