from django.urls import path

from . import views

app_name = "funcionarios"

urlpatterns = [
    path("funcionarios/", views.FuncionarioListView.as_view(), name="list"),
    path("funcionarios/novo/", views.FuncionarioCreateView.as_view(), name="create"),
    path("funcionarios/<int:pk>/editar/", views.FuncionarioUpdateView.as_view(), name="update"),
    path("funcionarios/<int:pk>/", views.FuncionarioDetailView.as_view(), name="detail"),
    path("funcionarios/afastamentos/", views.AfastamentoListView.as_view(), name="afastamentos_list"),
    path(
        "funcionarios/afastamentos/novo/",
        views.AfastamentoCreateView.as_view(),
        name="afastamentos_create",
    ),
    path(
        "funcionarios/afastamentos/<int:pk>/editar/",
        views.AfastamentoUpdateView.as_view(),
        name="afastamentos_update",
    ),
]
