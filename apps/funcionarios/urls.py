from django.urls import path

from . import views

app_name = "funcionarios"

urlpatterns = [
    path("funcionarios/", views.FuncionarioListView.as_view(), name="list"),
    path("funcionarios/novo/", views.FuncionarioCreateView.as_view(), name="create"),
    path("funcionarios/<int:pk>/editar/", views.FuncionarioUpdateView.as_view(), name="update"),
    path(
        "funcionarios/<int:pk>/toggle/",
        views.FuncionarioToggleActiveView.as_view(),
        name="toggle_active",
    ),
    path(
        "funcionarios/<int:pk>/validacao/",
        views.FuncionarioValidacaoRecebimentoView.as_view(),
        name="validacao_recebimento",
    ),
    path(
        "funcionarios/anexos/novo/",
        views.FuncionarioAnexoCreateView.as_view(),
        name="anexos_create",
    ),
    path(
        "funcionarios/<int:pk>/anexos/",
        views.FuncionarioAnexoListView.as_view(),
        name="anexos_list",
    ),
    path("funcionarios/<int:pk>/", views.FuncionarioDetailView.as_view(), name="detail"),
    path("funcionarios/advertencias/", views.AdvertenciaListView.as_view(), name="advertencias_list"),
    path(
        "funcionarios/advertencias/novo/",
        views.AdvertenciaCreateView.as_view(),
        name="advertencias_create",
    ),
    path(
        "funcionarios/advertencias/<int:pk>/editar/",
        views.AdvertenciaUpdateView.as_view(),
        name="advertencias_update",
    ),
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
    path("funcionarios/riscos/", views.RiscoListView.as_view(), name="riscos_list"),
    path("funcionarios/riscos/novo/", views.RiscoCreateView.as_view(), name="riscos_create"),
    path(
        "funcionarios/riscos/<int:pk>/editar/",
        views.RiscoUpdateView.as_view(),
        name="riscos_update",
    ),
    path(
        "funcionarios/riscos/<int:pk>/excluir/",
        views.RiscoDeleteView.as_view(),
        name="riscos_delete",
    ),
    path(
        "funcionarios/<int:pk>/riscos/atribuir/",
        views.RiscoAssignView.as_view(),
        name="riscos_assign",
    ),
    path(
        "funcionarios/<int:pk>/riscos/<int:risco_pk>/remover/",
        views.RiscoUnassignView.as_view(),
        name="riscos_unassign",
    ),
    path(
        "funcionarios/<int:pk>/historico/",
        views.FuncionarioHistoricoListView.as_view(),
        name="historico_list",
    ),
    path(
        "funcionarios/<int:pk>/historico-entregas/",
        views.FuncionarioHistoricoEntregaListView.as_view(),
        name="historico_entregas_list",
    ),
    path("funcionarios/produtos/", views.FuncionarioProdutoListView.as_view(), name="produtos_list"),
    path("funcionarios/produtos/novo/", views.FuncionarioProdutoCreateView.as_view(), name="produtos_create"),
    path(
        "funcionarios/produtos/<int:pk>/editar/",
        views.FuncionarioProdutoUpdateView.as_view(),
        name="produtos_update",
    ),
    path(
        "funcionarios/produtos/<int:pk>/excluir/",
        views.FuncionarioProdutoDeleteView.as_view(),
        name="produtos_delete",
    ),
    path(
        "funcionarios/produtos/<int:pk>/toggle/",
        views.FuncionarioProdutoToggleActiveView.as_view(),
        name="produtos_toggle",
    ),
    path(
        "centros_custo/",
        views.CentroCustoListView.as_view(),
        name="centro_custo_list",
    ),
    path(
        "centros_custo/novo/",
        views.CentroCustoCreateView.as_view(),
        name="centro_custo_create",
    ),
    path(
        "centros_custo/<int:pk>/editar/",
        views.CentroCustoUpdateView.as_view(),
        name="centro_custo_update",
    ),
    path(
        "centros_custo/<int:pk>/toggle/",
        views.CentroCustoToggleActiveView.as_view(),
        name="centro_custo_toggle",
    ),
    path(
        "centros_custo/<int:pk>/excluir/",
        views.CentroCustoDeleteView.as_view(),
        name="centro_custo_delete",
    ),
    path(
        "centros_custo/<int:pk>/uso/",
        views.CentroCustoUsoView.as_view(),
        name="centro_custo_uso",
    ),
    path("ghes/", views.GHEListView.as_view(), name="ghe_list"),
    path("ghes/novo/", views.GHECreateView.as_view(), name="ghe_create"),
    path("ghes/<int:pk>/editar/", views.GHEUpdateView.as_view(), name="ghe_update"),
    path("ghes/<int:pk>/toggle/", views.GHEToggleActiveView.as_view(), name="ghe_toggle"),
    path("ghes/<int:pk>/excluir/", views.GHEDeleteView.as_view(), name="ghe_delete"),
    path("ghes/<int:pk>/uso/", views.GHEUsoView.as_view(), name="ghe_uso"),
    path("turnos/", views.TurnoListView.as_view(), name="turnos_list"),
    path("turnos/novo/", views.TurnoCreateView.as_view(), name="turnos_create"),
    path("turnos/<int:pk>/editar/", views.TurnoUpdateView.as_view(), name="turnos_update"),
    path("turnos/<int:pk>/toggle/", views.TurnoToggleActiveView.as_view(), name="turnos_toggle"),
    path("turnos/<int:pk>/excluir/", views.TurnoDeleteView.as_view(), name="turnos_delete"),
    path(
        "motivos_afastamento/",
        views.MotivoAfastamentoListView.as_view(),
        name="motivos_afastamento_list",
    ),
    path(
        "motivos_afastamento/novo/",
        views.MotivoAfastamentoCreateView.as_view(),
        name="motivos_afastamento_create",
    ),
    path(
        "motivos_afastamento/<int:pk>/editar/",
        views.MotivoAfastamentoUpdateView.as_view(),
        name="motivos_afastamento_update",
    ),
    path(
        "motivos_afastamento/<int:pk>/toggle/",
        views.MotivoAfastamentoToggleActiveView.as_view(),
        name="motivos_afastamento_toggle",
    ),
    path(
        "motivos_afastamento/<int:pk>/excluir/",
        views.MotivoAfastamentoDeleteView.as_view(),
        name="motivos_afastamento_delete",
    ),
    path("plantas/", views.PlantaListView.as_view(), name="plantas_list"),
    path("plantas/novo/", views.PlantaCreateView.as_view(), name="plantas_create"),
    path("plantas/<int:pk>/editar/", views.PlantaUpdateView.as_view(), name="plantas_update"),
    path("plantas/<int:pk>/toggle/", views.PlantaToggleActiveView.as_view(), name="plantas_toggle"),
    path("plantas/<int:pk>/excluir/", views.PlantaDeleteView.as_view(), name="plantas_delete"),
]
