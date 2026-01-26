from django.conf import settings
from django.conf.urls.static import static
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
    path("", include(("apps.entregas.urls", "entregas"), namespace="entregas")),
    path("", include(("apps.treinamentos.urls", "treinamentos"), namespace="treinamentos")),
    path("", include(("apps.acessos.urls", "acessos"), namespace="acessos")),
    path("", include(("apps.accounts.urls", "accounts"), namespace="accounts")),
    path("", include(("apps.relatorios.urls", "relatorios"), namespace="relatorios")),
    path("", include(("apps.acidentes.urls", "acidentes"), namespace="acidentes")),
    path("", include(("apps.cipa.urls", "cipa"), namespace="cipa")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
