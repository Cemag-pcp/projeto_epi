from django.urls import path

from . import views

app_name = "estoque"

urlpatterns = [
    path("estoque/", views.EstoqueListView.as_view(), name="list"),
    path("estoque/novo/", views.EstoqueCreateView.as_view(), name="create"),
    path("estoque/movimentar/", views.MovimentacaoCreateView.as_view(), name="movimentar"),
]