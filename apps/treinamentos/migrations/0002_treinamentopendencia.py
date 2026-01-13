from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):
    dependencies = [
        ("treinamentos", "0001_initial"),
        ("funcionarios", "0022_funcionarioproduto_ativo"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="TreinamentoPendencia",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pendente", "Pendente"),
                            ("agendado", "Agendado"),
                            ("realizado", "Realizado"),
                            ("aprovado", "Aprovado"),
                            ("reprovado", "Reprovado"),
                            ("expirado", "Expirado"),
                        ],
                        default="pendente",
                        max_length=20,
                    ),
                ),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now, editable=False)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "company",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="treinamentopendencia_set",
                        to="tenants.company",
                    ),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="treinamentopendencia_created",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "updated_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="treinamentopendencia_updated",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "funcionario",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="treinamentos_pendentes",
                        to="funcionarios.funcionario",
                    ),
                ),
                (
                    "treinamento",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="pendencias",
                        to="treinamentos.treinamento",
                    ),
                ),
            ],
            options={"ordering": ["-created_at"], "unique_together": {("funcionario", "treinamento")}},
        ),
    ]
