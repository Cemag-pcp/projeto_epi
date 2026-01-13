from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("tenants", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="company",
            name="estoque_enabled",
            field=models.BooleanField(default=True),
        ),
    ]
