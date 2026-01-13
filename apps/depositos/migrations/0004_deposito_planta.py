from django.db import migrations, models


def set_default_planta(apps, schema_editor):
    Deposito = apps.get_model("depositos", "Deposito")
    Planta = apps.get_model("funcionarios", "Planta")
    for deposito in Deposito.objects.filter(planta__isnull=True):
        planta = (
            Planta.objects.filter(company_id=deposito.company_id).order_by("id").first()
        )
        if planta is None:
            planta = Planta.objects.create(
                company_id=deposito.company_id,
                nome="Planta Padrao",
                ativo=True,
            )
        deposito.planta_id = planta.id
        deposito.save(update_fields=["planta"])


class Migration(migrations.Migration):
    dependencies = [
        ("funcionarios", "0021_funcionario_validacao_recebimento"),
        ("depositos", "0003_deposito_created_by_deposito_updated_by"),
    ]

    operations = [
        migrations.AddField(
            model_name="deposito",
            name="planta",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.deletion.PROTECT,
                to="funcionarios.planta",
            ),
        ),
        migrations.RunPython(set_default_planta, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="deposito",
            name="planta",
            field=models.ForeignKey(
                on_delete=models.deletion.PROTECT,
                to="funcionarios.planta",
            ),
        ),
    ]
