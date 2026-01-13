from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("funcionarios", "0021_funcionario_validacao_recebimento"),
    ]

    operations = [
        migrations.AddField(
            model_name="funcionarioproduto",
            name="ativo",
            field=models.BooleanField(default=True),
        ),
    ]
