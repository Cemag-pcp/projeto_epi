from django.contrib.auth import views as auth_views
from django.urls import include, path


urlpatterns = [
    path("login/", auth_views.LoginView.as_view(template_name="registration/login.html"), name="login"),
    path("", include("apps.ui.urls")),
    path("", include("django.contrib.auth.urls")),
    path("", include(("apps.funcionarios.urls", "funcionarios"), namespace="funcionarios")),
    path("", include(("apps.cargos.urls", "cargos"), namespace="cargos")),
    path("", include(("apps.setores.urls", "setores"), namespace="setores")),
    path("", include(("apps.tipos_funcionario.urls", "tipos_funcionario"), namespace="tipos_funcionario")),
    path("", include(("apps.fornecedores.urls", "fornecedores"), namespace="fornecedores")),
    path("", include(("apps.produtos.urls", "produtos"), namespace="produtos")),
    path("", include(("apps.depositos.urls", "depositos"), namespace="depositos")),
    path("", include(("apps.estoque.urls", "estoque"), namespace="estoque")),
]
