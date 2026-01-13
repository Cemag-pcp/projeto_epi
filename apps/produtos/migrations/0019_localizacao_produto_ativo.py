from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("produtos", "0018_localizacao_produto"),
    ]

    operations = [
        migrations.AddField(
            model_name="localizacaoproduto",
            name="ativo",
            field=models.BooleanField(default=True),
        ),
    ]
