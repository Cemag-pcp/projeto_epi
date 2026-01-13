from django.db import migrations, models
import django.db.models.deletion


def migrate_produto_periodicidade(apps, schema_editor):
    Produto = apps.get_model("produtos", "Produto")
    Periodicidade = apps.get_model("produtos", "Periodicidade")
    for produto in Produto.objects.exclude(periodicidade=""):
        nome = (produto.periodicidade or "").strip()
        if not nome:
            continue
        periodicidade, _ = Periodicidade.objects.get_or_create(
            company_id=produto.company_id,
            nome=nome,
            defaults={"ativo": True, "fator_dias": 1},
        )
        produto.periodicidade_fk = periodicidade
        if not produto.periodicidade_quantidade:
            produto.periodicidade_quantidade = 1
        produto.save(update_fields=["periodicidade_fk", "periodicidade_quantidade"])


class Migration(migrations.Migration):
    dependencies = [
        ("produtos", "0016_periodicidade_fator_dias"),
    ]

    operations = [
        migrations.AddField(
            model_name="produto",
            name="periodicidade_fk",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to="produtos.periodicidade",
            ),
        ),
        migrations.AddField(
            model_name="produto",
            name="periodicidade_quantidade",
            field=models.PositiveIntegerField(default=1, verbose_name="Quantidade"),
        ),
        migrations.RunPython(migrate_produto_periodicidade, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="produto",
            name="periodicidade",
        ),
        migrations.RenameField(
            model_name="produto",
            old_name="periodicidade_fk",
            new_name="periodicidade",
        ),
    ]
