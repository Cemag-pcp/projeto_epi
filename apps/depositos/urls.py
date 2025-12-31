from django.urls import path

from . import views

app_name = "depositos"

urlpatterns = [
    path("depositos/", views.DepositoListView.as_view(), name="list"),
    path("depositos/novo/", views.DepositoCreateView.as_view(), name="create"),
    path("depositos/<int:pk>/editar/", views.DepositoUpdateView.as_view(), name="update"),
]
