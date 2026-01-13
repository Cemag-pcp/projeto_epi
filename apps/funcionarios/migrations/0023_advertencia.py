from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
from django.utils import timezone


class Migration(migrations.Migration):

    dependencies = [
        ("tenants", "0002_company_estoque_enabled"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("funcionarios", "0022_funcionarioproduto_ativo"),
    ]

    operations = [
        migrations.CreateModel(
            name="Advertencia",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(default=timezone.now, editable=False)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("data", models.DateField(default=timezone.localdate)),
                ("tipo", models.CharField(choices=[("uso_incorreto", "Uso incorreto"), ("uso_indevido", "Uso indevido"), ("ausencia", "Ausencia de uso")], default="uso_incorreto", max_length=30)),
                ("descricao", models.TextField(blank=True)),
                ("company", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="%(class)s_set", to="tenants.company")),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="%(class)s_created", to=settings.AUTH_USER_MODEL)),
                ("funcionario", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="advertencias", to="funcionarios.funcionario")),
                ("updated_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="%(class)s_updated", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ["-data"],
            },
        ),
    ]
