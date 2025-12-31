from django.urls import path

from . import views

app_name = "produtos"

urlpatterns = [
    path("produtos/", views.ProdutoListView.as_view(), name="list"),
    path("produtos/novo/", views.ProdutoCreateView.as_view(), name="create"),
    path("produtos/<int:pk>/editar/", views.ProdutoUpdateView.as_view(), name="update"),
]
