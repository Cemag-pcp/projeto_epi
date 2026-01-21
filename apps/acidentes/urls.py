from django.urls import path

from . import views

app_name = "acidentes"

urlpatterns = [
    path("acidentes/", views.AcidenteTrabalhoListView.as_view(), name="list"),
    path("acidentes/novo/", views.AcidenteTrabalhoCreateView.as_view(), name="create"),
    path("acidentes/<int:pk>/editar/", views.AcidenteTrabalhoUpdateView.as_view(), name="update"),
    path("acidentes/api/ambientes/", views.AmbientesApiView.as_view(), name="api_ambientes"),
    path("acidentes/api/cidades/", views.CidadesApiView.as_view(), name="api_cidades"),
    path("acidentes/api/cep/", views.CepLookupApiView.as_view(), name="api_cep"),
]

