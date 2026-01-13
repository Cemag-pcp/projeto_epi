from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):
    dependencies = [
        ("treinamentos", "0002_treinamentopendencia"),
        ("funcionarios", "0022_funcionarioproduto_ativo"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="TreinamentoParticipacao",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("presente", models.BooleanField(default=False)),
                (
                    "resultado",
                    models.CharField(
                        blank=True,
                        choices=[("aprovado", "Aprovado"), ("reprovado", "Reprovado"), ("ausente", "Ausente")],
                        max_length=20,
                    ),
                ),
                ("nota", models.DecimalField(blank=True, decimal_places=1, max_digits=4, null=True)),
                ("avaliacao", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now, editable=False)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "company",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="treinamentoparticipacao_set",
                        to="tenants.company",
                    ),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="treinamentoparticipacao_created",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "updated_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="treinamentoparticipacao_updated",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "funcionario",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="treinamentos_participacoes",
                        to="funcionarios.funcionario",
                    ),
                ),
                (
                    "turma",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="participacoes",
                        to="treinamentos.turma",
                    ),
                ),
            ],
            options={"ordering": ["-created_at"], "unique_together": {("turma", "funcionario")}},
        ),
    ]
