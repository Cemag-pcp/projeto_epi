from django.urls import path

from . import views

app_name = "acessos"

urlpatterns = [
    path("acessos/empresas/", views.EmpresaParceiraListView.as_view(), name="empresas_list"),
    path("acessos/empresas/novo/", views.EmpresaParceiraCreateView.as_view(), name="empresas_create"),
    path("acessos/empresas/<int:pk>/editar/", views.EmpresaParceiraUpdateView.as_view(), name="empresas_update"),
    path("acessos/terceiros/", views.TerceiroListView.as_view(), name="terceiros_list"),
    path("acessos/terceiros/novo/", views.TerceiroCreateView.as_view(), name="terceiros_create"),
    path("acessos/terceiros/<int:pk>/editar/", views.TerceiroUpdateView.as_view(), name="terceiros_update"),
    path("acessos/terceiros/por-empresa/", views.terceiros_por_empresa, name="terceiros_por_empresa"),
    path(
        "acessos/consumos/depositos/",
        views.depositos_por_produto,
        name="depositos_por_produto",
    ),
    path("acessos/registros/", views.AcessoEPIListView.as_view(), name="acessos_list"),
    path("acessos/registros/novo/", views.AcessoEPICreateView.as_view(), name="acessos_create"),
    path("acessos/registros/<int:pk>/editar/", views.AcessoEPIUpdateView.as_view(), name="acessos_update"),
    path("acessos/consumos/", views.ConsumoParceiroListView.as_view(), name="consumos_list"),
    path("acessos/consumos/novo/", views.ConsumoParceiroCreateView.as_view(), name="consumos_create"),
    path("acessos/consumos/<int:pk>/editar/", views.ConsumoParceiroUpdateView.as_view(), name="consumos_update"),
]
