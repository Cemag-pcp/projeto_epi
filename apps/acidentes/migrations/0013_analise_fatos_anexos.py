from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):
    dependencies = [
        ("funcionarios", "0025_alter_funcionario_validacao_recebimento"),
        ("acidentes", "0012_merge_0011_alter_e_seed"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="acidentetrabalho",
            name="analise_data_conclusao",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="acidentetrabalho",
            name="analise_preenchido_por",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="acidentes_analise_preenchidos",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="acidentetrabalho",
            name="analise_coordenador",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="acidentes_analise_coordenados",
                to="funcionarios.funcionario",
            ),
        ),
        migrations.AddField(
            model_name="acidentetrabalho",
            name="analise_envolvidos",
            field=models.ManyToManyField(
                blank=True,
                related_name="acidentes_analise_envolvidos",
                to="funcionarios.funcionario",
            ),
        ),
        migrations.AddField(
            model_name="acidentetrabalho",
            name="analise_participantes",
            field=models.ManyToManyField(
                blank=True,
                related_name="acidentes_analise_participantes",
                to="funcionarios.funcionario",
            ),
        ),
        migrations.CreateModel(
            name="AcidenteFato",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now, editable=False)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="acidentefato_created",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "updated_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="acidentefato_updated",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                ("hora_ocorrencia", models.TimeField()),
                ("detalhamento", models.TextField()),
                (
                    "acidente",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="fatos",
                        to="acidentes.acidentetrabalho",
                    ),
                ),
                (
                    "company",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="acidentefato_set",
                        to="tenants.company",
                    ),
                ),
            ],
            options={"ordering": ["hora_ocorrencia", "pk"]},
        ),
        migrations.CreateModel(
            name="AcidenteAnexo",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now, editable=False)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="acidenteanexo_created",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "updated_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="acidenteanexo_updated",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                ("arquivo", models.FileField(upload_to="acidentes/anexos/")),
                ("descricao", models.CharField(blank=True, max_length=200)),
                (
                    "acidente",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="anexos",
                        to="acidentes.acidentetrabalho",
                    ),
                ),
                (
                    "company",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="acidenteanexo_set",
                        to="tenants.company",
                    ),
                ),
            ],
            options={"ordering": ["pk"]},
        ),
    ]
