from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):
    dependencies = [
        ("treinamentos", "0006_remove_turma_data"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="TreinamentoPresencaAula",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("presente", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now, editable=False)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "company",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="treinamentopresencaaula_set",
                        to="tenants.company",
                    ),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="treinamentopresencaaula_created",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "updated_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="treinamentopresencaaula_updated",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "funcionario",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="treinamentos_presencas",
                        to="funcionarios.funcionario",
                    ),
                ),
                (
                    "turma_aula",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="presencas",
                        to="treinamentos.turmaaula",
                    ),
                ),
            ],
            options={"ordering": ["-created_at"], "unique_together": {("turma_aula", "funcionario")}},
        ),
    ]
