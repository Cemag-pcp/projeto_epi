from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("produtos", "0022_produto_periodicidade_not_null"),
    ]

    operations = [
        migrations.AddField(
            model_name="tipoproduto",
            name="ativo",
            field=models.BooleanField(default=True),
        ),
    ]
