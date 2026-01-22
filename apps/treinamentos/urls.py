from django.urls import path

from . import views

app_name = "treinamentos"

urlpatterns = [
    path("treinamentos/", views.TreinamentoListView.as_view(), name="list"),
    path("treinamentos/agenda/", views.TreinamentoAgendaView.as_view(), name="agenda"),
    path("treinamentos/novo/", views.TreinamentoCreateView.as_view(), name="create"),
    path("treinamentos/<int:pk>/editar/", views.TreinamentoUpdateView.as_view(), name="update"),
    path("treinamentos/<int:pk>/toggle/", views.TreinamentoToggleActiveView.as_view(), name="toggle"),
    path("treinamentos/instrutores/", views.InstrutorListView.as_view(), name="instrutores_list"),
    path("treinamentos/instrutores/novo/", views.InstrutorCreateView.as_view(), name="instrutores_create"),
    path(
        "treinamentos/instrutores/<int:pk>/editar/",
        views.InstrutorUpdateView.as_view(),
        name="instrutores_update",
    ),
    path(
        "treinamentos/instrutores/<int:pk>/toggle/",
        views.InstrutorToggleActiveView.as_view(),
        name="instrutores_toggle_active",
    ),
    path(
        "treinamentos/instrutores/<int:pk>/excluir/",
        views.InstrutorDeleteView.as_view(),
        name="instrutores_delete",
    ),
    path("treinamentos/documentos/", views.DocumentoTemplateListView.as_view(), name="documentos_list"),
    path("treinamentos/documentos/novo/", views.DocumentoTemplateCreateView.as_view(), name="documentos_create"),
    path("treinamentos/documentos/<int:pk>/editar/", views.DocumentoTemplateUpdateView.as_view(), name="documentos_update"),
    path("treinamentos/documentos/<int:pk>/excluir/", views.DocumentoTemplateDeleteView.as_view(), name="documentos_delete"),
    path("treinamentos/certificados/<int:pk>/imprimir/", views.CertificadoPrintView.as_view(), name="certificados_print"),
    path("treinamentos/turmas/", views.TurmaListView.as_view(), name="turmas_list"),
    path("treinamentos/turmas/novo/", views.TurmaCreateView.as_view(), name="turmas_create"),
    path("treinamentos/turmas/<int:pk>/editar/", views.TurmaUpdateView.as_view(), name="turmas_update"),
    path("treinamentos/turmas/<int:pk>/finalizar/", views.TurmaFinalizarView.as_view(), name="turmas_finalizar"),
    path("treinamentos/turmas/<int:pk>/presenca/", views.TurmaPresencaView.as_view(), name="turmas_presenca"),
    path("treinamentos/turmas/<int:pk>/avaliacao/", views.TurmaAvaliacaoView.as_view(), name="turmas_avaliacao"),
]
