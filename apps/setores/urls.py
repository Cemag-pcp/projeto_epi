from django.urls import path

from . import views

app_name = "setores"

urlpatterns = [
    path("setores/", views.SetorListView.as_view(), name="list"),
    path("setores/novo/", views.SetorCreateView.as_view(), name="create"),
    path("setores/<int:pk>/editar/", views.SetorUpdateView.as_view(), name="update"),
    path("setores/<int:pk>/toggle/", views.SetorToggleActiveView.as_view(), name="toggle_active"),
    path("setores/<int:pk>/excluir/", views.SetorDeleteView.as_view(), name="delete"),
    path("setores/<int:pk>/uso/", views.SetorUsoView.as_view(), name="usage"),
]
