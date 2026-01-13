from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("produtos", "0015_periodicidade"),
    ]

    operations = [
        migrations.AddField(
            model_name="periodicidade",
            name="fator_dias",
            field=models.PositiveIntegerField(default=1),
        ),
    ]
