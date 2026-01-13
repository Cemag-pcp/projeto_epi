from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):
    dependencies = [
        ("entregas", "0002_entrega_status"),
        ("tenants", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="EntregaItem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now, editable=False)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("quantidade", models.DecimalField(decimal_places=2, max_digits=12)),
                ("ca", models.CharField(blank=True, max_length=50)),
                ("observacao", models.TextField(blank=True)),
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
                        related_name="entregas_itens",
                        to="depositos.deposito",
                    ),
                ),
                (
                    "entrega",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="itens",
                        to="entregas.entrega",
                    ),
                ),
                (
                    "produto",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="entregas_itens",
                        to="produtos.produto",
                    ),
                ),
            ],
            options={
                "ordering": ["id"],
            },
        ),
    ]
