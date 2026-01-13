from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("depositos", "0004_deposito_planta"),
    ]

    operations = [
        migrations.AddField(
            model_name="deposito",
            name="bloquear_movimento_negativo",
            field=models.BooleanField(default=False),
        ),
    ]
