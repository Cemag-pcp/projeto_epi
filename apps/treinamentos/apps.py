from django.apps import AppConfig


class TreinamentosConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.treinamentos"
    verbose_name = "Treinamentos"

    def ready(self):
        from . import signals  # noqa: F401
