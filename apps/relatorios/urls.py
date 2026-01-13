from django.urls import path

from . import views

app_name = "relatorios"

urlpatterns = [
    path("relatorios/", views.RelatorioListView.as_view(), name="list"),
    path("relatorios/novo/", views.RelatorioCreateView.as_view(), name="create"),
    path("relatorios/<int:pk>/editar/", views.RelatorioUpdateView.as_view(), name="update"),
    path("relatorios/<int:pk>/excluir/", views.RelatorioDeleteView.as_view(), name="delete"),
    path("relatorios/<int:pk>/", views.RelatorioDetailView.as_view(), name="detail"),
]
