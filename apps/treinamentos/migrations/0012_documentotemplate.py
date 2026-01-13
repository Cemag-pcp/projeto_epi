from django.conf import settings
from django.db import migrations, models
from django.utils import timezone
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("tenants", "0002_company_estoque_enabled"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("treinamentos", "0011_alter_turma_options_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="DocumentoTemplate",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(default=timezone.now, editable=False)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("titulo", models.CharField(max_length=200)),
                ("tipo", models.CharField(choices=[("certificado", "Certificado"), ("recebimento_material", "Recebimento de material"), ("outro", "Outro")], default="certificado", max_length=30)),
                ("corpo_html", models.TextField()),
                ("logo", models.FileField(blank=True, null=True, upload_to="documentos/")),
                ("ativo", models.BooleanField(default=True)),
                ("company", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="%(class)s_set", to="tenants.company")),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="%(class)s_created", to=settings.AUTH_USER_MODEL)),
                ("updated_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="%(class)s_updated", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ["-updated_at"],
            },
        ),
    ]
