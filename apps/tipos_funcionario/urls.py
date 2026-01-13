from django.urls import path

from . import views

app_name = "tipos_funcionario"

urlpatterns = [
    path("tipos_funcionario/", views.TipoFuncionarioListView.as_view(), name="list"),
    path("tipos_funcionario/novo/", views.TipoFuncionarioCreateView.as_view(), name="create"),
    path("tipos_funcionario/<int:pk>/editar/", views.TipoFuncionarioUpdateView.as_view(), name="update"),
    path("tipos_funcionario/<int:pk>/toggle/", views.TipoFuncionarioToggleActiveView.as_view(), name="toggle"),
    path("tipos_funcionario/<int:pk>/excluir/", views.TipoFuncionarioDeleteView.as_view(), name="delete"),
    path("tipos_funcionario/<int:pk>/uso/", views.TipoFuncionarioUsoView.as_view(), name="usage"),
    path("tipos_funcionario/produtos/", views.TipoFuncionarioProdutoListView.as_view(), name="produtos_list"),
    path("tipos_funcionario/produtos/novo/", views.TipoFuncionarioProdutoCreateView.as_view(), name="produtos_create"),
    path("tipos_funcionario/produtos/<int:pk>/editar/", views.TipoFuncionarioProdutoUpdateView.as_view(), name="produtos_update"),
    path("tipos_funcionario/produtos/<int:pk>/excluir/", views.TipoFuncionarioProdutoDeleteView.as_view(), name="produtos_delete"),
]
