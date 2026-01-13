from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("entregas", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="entrega",
            name="status",
            field=models.CharField(
                choices=[("entregue", "Entregue"), ("cancelada", "Cancelada")],
                default="entregue",
                max_length=20,
            ),
        ),
    ]
