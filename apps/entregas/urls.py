from django.urls import path

from . import views

app_name = "entregas"

urlpatterns = [
    path("entregas/", views.EntregaListView.as_view(), name="list"),
    path("entregas/novo/", views.EntregaCreateView.as_view(), name="create"),
    path("entregas/solicitar/", views.EntregaSolicitacaoCreateView.as_view(), name="solicitar"),
    path("entregas/depositos/", views.EntregaDepositosView.as_view(), name="depositos"),
    path("entregas/produtos/", views.EntregaProdutosView.as_view(), name="produtos"),
    path("entregas/<int:pk>/detalhes/", views.EntregaDetailView.as_view(), name="detail"),
    path("entregas/<int:pk>/itens/", views.EntregaItensView.as_view(), name="itens"),
    path("entregas/<int:pk>/entregar/", views.EntregaAtenderView.as_view(), name="entregar"),
    path("entregas/<int:pk>/cancelar/", views.EntregaCancelView.as_view(), name="cancel"),
]
