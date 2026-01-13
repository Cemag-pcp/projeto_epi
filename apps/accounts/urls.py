from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("usuarios/", views.UserProfileListView.as_view(), name="list"),
    path("usuarios/novo/", views.UserProfileCreateView.as_view(), name="create"),
    path("usuarios/<int:pk>/editar/", views.UserProfileUpdateView.as_view(), name="update"),
    path("usuarios/<int:pk>/toggle/", views.UserProfileToggleActiveView.as_view(), name="toggle_active"),
    path("usuarios/<int:pk>/excluir/", views.UserProfileDeleteView.as_view(), name="delete"),
    path("grupos/", views.GroupListView.as_view(), name="groups_list"),
    path("grupos/novo/", views.GroupCreateView.as_view(), name="groups_create"),
    path("grupos/<int:pk>/editar/", views.GroupUpdateView.as_view(), name="groups_update"),
    path("grupos/<int:pk>/excluir/", views.GroupDeleteView.as_view(), name="groups_delete"),
]
