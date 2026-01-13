from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("produtos", "0019_localizacao_produto_ativo"),
    ]

    operations = [
        migrations.AlterField(
            model_name="produto",
            name="periodicidade",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                to="produtos.periodicidade",
            ),
        ),
    ]
