from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):
    dependencies = [
        ("treinamentos", "0008_turma_finalizada"),
        ("funcionarios", "0022_funcionarioproduto_ativo"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="TreinamentoCertificado",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("data_emissao", models.DateField()),
                ("validade_ate", models.DateField(blank=True, null=True)),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now, editable=False)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "company",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="treinamentocertificado_set",
                        to="tenants.company",
                    ),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="treinamentocertificado_created",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "updated_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="treinamentocertificado_updated",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "funcionario",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="treinamentos_certificados",
                        to="funcionarios.funcionario",
                    ),
                ),
                (
                    "treinamento",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="certificados",
                        to="treinamentos.treinamento",
                    ),
                ),
                (
                    "turma",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="certificados",
                        to="treinamentos.turma",
                    ),
                ),
            ],
            options={"ordering": ["-data_emissao"], "unique_together": {("funcionario", "treinamento")}},
        ),
    ]
