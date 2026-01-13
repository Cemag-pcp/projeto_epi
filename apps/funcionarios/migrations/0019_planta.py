from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


def create_default_planta(apps, schema_editor):
    Planta = apps.get_model("funcionarios", "Planta")
    Company = apps.get_model("tenants", "Company")
    if Planta.objects.exists():
        return
    schema_name = schema_editor.connection.schema_name
    company = Company.objects.filter(schema_name=schema_name).first()
    if not company:
        return
    Planta.objects.create(nome="Principal", ativo=True, company_id=company.id)


class Migration(migrations.Migration):
    dependencies = [
        ("funcionarios", "0018_motivo_afastamento"),
        ("tenants", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Planta",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now, editable=False)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("nome", models.CharField(max_length=120)),
                ("ativo", models.BooleanField(default=True)),
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
            ],
            options={
                "ordering": ["nome"],
            },
        ),
        migrations.AddField(
            model_name="funcionario",
            name="planta",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to="funcionarios.planta",
            ),
        ),
        migrations.RunPython(create_default_planta, migrations.RunPython.noop),
    ]
