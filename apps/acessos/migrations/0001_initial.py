from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
from django.utils import timezone


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("tenants", "0002_company_estoque_enabled"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("funcionarios", "0024_advertencia_descricao_required"),
        ("produtos", "0023_tipoproduto_ativo"),
    ]

    operations = [
        migrations.CreateModel(
            name="EmpresaParceira",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(default=timezone.now, editable=False)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("nome", models.CharField(max_length=200)),
                ("documento", models.CharField(blank=True, max_length=40)),
                ("contato", models.CharField(blank=True, max_length=120)),
                ("ativo", models.BooleanField(default=True)),
                ("company", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="%(class)s_set", to="tenants.company")),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="%(class)s_created", to=settings.AUTH_USER_MODEL)),
                ("updated_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="%(class)s_updated", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ["nome"],
            },
        ),
        migrations.CreateModel(
            name="Terceiro",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(default=timezone.now, editable=False)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("nome", models.CharField(max_length=200)),
                ("documento", models.CharField(blank=True, max_length=40)),
                ("telefone", models.CharField(blank=True, max_length=40)),
                ("ativo", models.BooleanField(default=True)),
                ("company", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="%(class)s_set", to="tenants.company")),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="%(class)s_created", to=settings.AUTH_USER_MODEL)),
                ("empresa_parceira", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="terceiros", to="acessos.empresaparceira")),
                ("updated_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="%(class)s_updated", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ["nome"],
            },
        ),
        migrations.CreateModel(
            name="ConsumoParceiro",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(default=timezone.now, editable=False)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("quantidade", models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ("data", models.DateField(default=timezone.localdate)),
                ("observacao", models.TextField(blank=True)),
                ("company", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="%(class)s_set", to="tenants.company")),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="%(class)s_created", to=settings.AUTH_USER_MODEL)),
                ("empresa_parceira", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="consumos", to="acessos.empresaparceira")),
                ("produto", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="consumos_parceiros", to="produtos.produto")),
                ("updated_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="%(class)s_updated", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ["-data"],
            },
        ),
        migrations.CreateModel(
            name="AcessoEPI",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(default=timezone.now, editable=False)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("tipo_pessoa", models.CharField(choices=[("funcionario", "Funcionario"), ("terceiro", "Terceiro")], default="funcionario", max_length=20)),
                ("data_hora", models.DateTimeField(default=timezone.now)),
                ("status_epi", models.CharField(choices=[("em_dia", "Em dia"), ("pendente", "Pendente"), ("nao_informado", "Nao informado")], default="nao_informado", max_length=20)),
                ("status_treinamento", models.CharField(choices=[("em_dia", "Em dia"), ("pendente", "Pendente"), ("nao_aplicavel", "Nao aplicavel")], default="nao_aplicavel", max_length=20)),
                ("permitido", models.BooleanField(default=True)),
                ("observacao", models.TextField(blank=True)),
                ("company", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="%(class)s_set", to="tenants.company")),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="%(class)s_created", to=settings.AUTH_USER_MODEL)),
                ("funcionario", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="acessos_epi", to="funcionarios.funcionario")),
                ("planta", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to="funcionarios.planta")),
                ("terceiro", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="acessos_epi", to="acessos.terceiro")),
                ("updated_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="%(class)s_updated", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ["-data_hora"],
            },
        ),
    ]
