from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="ui-home"),
    path("componentes/", views.components, name="ui-components"),
    path("planta/selecionar/", views.planta_select, name="ui-planta-select"),
]
