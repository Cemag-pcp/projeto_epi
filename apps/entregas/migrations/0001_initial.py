from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("depositos", "0003_deposito_created_by_deposito_updated_by"),
        ("funcionarios", "0019_planta"),
        ("produtos", "0022_produto_periodicidade_not_null"),
        ("tenants", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Entrega",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now, editable=False)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("quantidade", models.DecimalField(decimal_places=2, max_digits=12)),
                ("ca", models.CharField(blank=True, max_length=50)),
                ("observacao", models.TextField(blank=True)),
                ("entregue_em", models.DateTimeField(default=django.utils.timezone.now)),
                (
                    "company",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="%(class)s_set",
                        to="tenants.company",
                    ),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(class)s_created",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "updated_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(class)s_updated",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "deposito",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="entregas",
                        to="depositos.deposito",
                    ),
                ),
                (
                    "funcionario",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="entregas",
                        to="funcionarios.funcionario",
                    ),
                ),
                (
                    "produto",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="entregas",
                        to="produtos.produto",
                    ),
                ),
            ],
            options={
                "ordering": ["-entregue_em"],
            },
        ),
    ]
