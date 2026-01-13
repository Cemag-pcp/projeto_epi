from django.urls import path

from . import views

app_name = "cargos"

urlpatterns = [
    path("cargos/", views.CargoListView.as_view(), name="list"),
    path("cargos/novo/", views.CargoCreateView.as_view(), name="create"),
    path("cargos/<int:pk>/editar/", views.CargoUpdateView.as_view(), name="update"),
    path("cargos/<int:pk>/toggle/", views.CargoToggleActiveView.as_view(), name="toggle"),
    path("cargos/<int:pk>/excluir/", views.CargoDeleteView.as_view(), name="delete"),
    path("cargos/<int:pk>/uso/", views.CargoUsoView.as_view(), name="usage"),
]
