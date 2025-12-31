from django.urls import path

from . import views

app_name = "cargos"

urlpatterns = [
    path("cargos/", views.CargoListView.as_view(), name="list"),
    path("cargos/novo/", views.CargoCreateView.as_view(), name="create"),
    path("cargos/<int:pk>/editar/", views.CargoUpdateView.as_view(), name="update"),
]
