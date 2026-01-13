from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("tenants", "0002_company_estoque_enabled"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("cargos", "0004_cargo_created_by_cargo_updated_by"),
        ("setores", "0004_setor_responsaveis"),
        ("tipos_funcionario", "0004_tipofuncionarioproduto"),
        ("produtos", "0023_tipoproduto_ativo"),
        ("funcionarios", "0022_funcionarioproduto_ativo"),
    ]

    operations = [
        migrations.CreateModel(
            name="Treinamento",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("nome", models.CharField(max_length=200)),
                ("validade_dias", models.PositiveIntegerField(default=0)),
                ("carga_horaria", models.DecimalField(decimal_places=2, default=0, max_digits=5)),
                (
                    "tipo",
                    models.CharField(
                        choices=[("epi", "EPI"), ("nr", "NR"), ("processo", "Processo"), ("outro", "Outro")],
                        default="epi",
                        max_length=20,
                    ),
                ),
                ("obrigatorio", models.BooleanField(default=True)),
                ("ativo", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now, editable=False)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "company",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="treinamento_set",
                        to="tenants.company",
                    ),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="treinamento_created",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "updated_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="treinamento_updated",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "requisitos_cargos",
                    models.ManyToManyField(blank=True, related_name="treinamentos", to="cargos.cargo"),
                ),
                (
                    "requisitos_epis",
                    models.ManyToManyField(blank=True, related_name="treinamentos_epi", to="produtos.produto"),
                ),
                (
                    "requisitos_setores",
                    models.ManyToManyField(blank=True, related_name="treinamentos", to="setores.setor"),
                ),
                (
                    "requisitos_tipos_funcionario",
                    models.ManyToManyField(
                        blank=True,
                        related_name="treinamentos",
                        to="tipos_funcionario.tipofuncionario",
                    ),
                ),
            ],
            options={"ordering": ["nome"]},
        ),
        migrations.CreateModel(
            name="Turma",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("data", models.DateField()),
                ("local", models.CharField(max_length=200)),
                ("capacidade", models.PositiveIntegerField(default=0)),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now, editable=False)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "company",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="turma_set",
                        to="tenants.company",
                    ),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="turma_created",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "updated_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="turma_updated",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "instrutor",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="turmas_instrutor",
                        to="funcionarios.funcionario",
                    ),
                ),
                (
                    "participantes",
                    models.ManyToManyField(blank=True, related_name="turmas_participante", to="funcionarios.funcionario"),
                ),
                (
                    "treinamento",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="turmas",
                        to="treinamentos.treinamento",
                    ),
                ),
            ],
            options={"ordering": ["-data", "id"]},
        ),
    ]
