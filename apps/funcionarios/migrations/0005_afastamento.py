from django.db import migrations, models
import django.db.models.deletion

import apps.funcionarios.models


class Migration(migrations.Migration):

    dependencies = [
        ("tenants", "0001_initial"),
        ("funcionarios", "0004_funcionario_centro_custo_funcionario_foto_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="Afastamento",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("data_inicio", models.DateField()),
                ("data_fim", models.DateField()),
                ("motivo", models.CharField(max_length=255)),
                (
                    "arquivo",
                    models.FileField(
                        blank=True,
                        null=True,
                        upload_to="funcionarios/afastamentos/",
                        validators=[apps.funcionarios.models.validate_attachment_size],
                    ),
                ),
                (
                    "company",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="afastamento_set",
                        to="tenants.company",
                    ),
                ),
                (
                    "funcionario",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="afastamentos",
                        to="funcionarios.funcionario",
                    ),
                ),
            ],
            options={
                "ordering": ["-data_inicio"],
            },
        ),
    ]
