from django.urls import path

from . import views

app_name = "setores"

urlpatterns = [
    path("setores/", views.SetorListView.as_view(), name="list"),
    path("setores/novo/", views.SetorCreateView.as_view(), name="create"),
    path("setores/<int:pk>/editar/", views.SetorUpdateView.as_view(), name="update"),
]
