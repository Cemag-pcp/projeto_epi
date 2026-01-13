from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("funcionarios", "0016_ghe_campos"),
    ]

    operations = [
        migrations.AddField(
            model_name="turno",
            name="ativo",
            field=models.BooleanField(default=True),
        ),
    ]
