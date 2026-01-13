from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("funcionarios", "0023_advertencia"),
    ]

    operations = [
        migrations.AlterField(
            model_name="advertencia",
            name="descricao",
            field=models.TextField(),
        ),
    ]
