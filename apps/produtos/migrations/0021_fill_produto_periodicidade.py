from django.db import migrations


def fill_produto_periodicidade(apps, schema_editor):
    Produto = apps.get_model("produtos", "Produto")
    Periodicidade = apps.get_model("produtos", "Periodicidade")
    for company_id in Produto.objects.filter(periodicidade__isnull=True).values_list(
        "company_id", flat=True
    ).distinct():
        if not company_id:
            continue
        periodicidade, _ = Periodicidade.objects.get_or_create(
            company_id=company_id,
            nome="Dias",
            defaults={"ativo": True, "fator_dias": 1},
        )
        Produto.objects.filter(company_id=company_id, periodicidade__isnull=True).update(
            periodicidade_id=periodicidade.id
        )


class Migration(migrations.Migration):
    dependencies = [
        ("produtos", "0020_produto_periodicidade_required"),
    ]

    operations = [
        migrations.RunPython(fill_produto_periodicidade, migrations.RunPython.noop),
    ]
