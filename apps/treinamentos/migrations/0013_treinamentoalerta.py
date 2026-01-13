from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
from django.utils import timezone


class Migration(migrations.Migration):

    dependencies = [
        ("tenants", "0002_company_estoque_enabled"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("treinamentos", "0012_documentotemplate"),
    ]

    operations = [
        migrations.CreateModel(
            name="TreinamentoAlerta",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(default=timezone.now, editable=False)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("dias_para_vencer", models.PositiveSmallIntegerField()),
                ("data_alerta", models.DateField(default=timezone.now)),
                ("enviado", models.BooleanField(default=False)),
                ("certificado", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="alertas", to="treinamentos.treinamentocertificado")),
                ("company", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="%(class)s_set", to="tenants.company")),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="%(class)s_created", to=settings.AUTH_USER_MODEL)),
                ("funcionario", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="treinamentos_alertas", to="funcionarios.funcionario")),
                ("treinamento", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="alertas", to="treinamentos.treinamento")),
                ("updated_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="%(class)s_updated", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ["-data_alerta"],
                "unique_together": {("certificado", "dias_para_vencer")},
            },
        ),
    ]
