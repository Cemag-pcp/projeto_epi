from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("entregas", "0003_entregaitem"),
    ]

    operations = [
        migrations.AddField(
            model_name="entrega",
            name="motivo_cancelamento",
            field=models.TextField(blank=True),
        ),
    ]
