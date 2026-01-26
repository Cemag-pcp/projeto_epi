from django.urls import path

from .views import (
    CipaEleicaoListView,
    CipaEleicaoWizardView,
    cipa_candidatura_publica,
    cipa_votacao_publica,
    cipa_wizard_start,
)

app_name = "cipa"

urlpatterns = [
    path("cipa/", CipaEleicaoListView.as_view(), name="list"),
    path("cipa/novo/", cipa_wizard_start, name="wizard_start"),
    path("cipa/<int:pk>/wizard/<int:step>/", CipaEleicaoWizardView.as_view(), name="wizard"),
    path("cipa/candidatura/<uuid:token>/", cipa_candidatura_publica, name="candidatura_publica"),
    path("cipa/votacao/<uuid:token>/", cipa_votacao_publica, name="votacao_publica"),
]
