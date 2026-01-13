from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("entregas", "0004_entrega_motivo_cancelamento"),
    ]

    operations = [
        migrations.AlterField(
            model_name="entrega",
            name="entregue_em",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
