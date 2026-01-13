from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("funcionarios", "0014_funcionario_afastado_funcionario_categoria_cnh_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="centrocusto",
            name="ativo",
            field=models.BooleanField(default=True),
        ),
    ]
