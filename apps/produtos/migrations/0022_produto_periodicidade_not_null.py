from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("produtos", "0021_fill_produto_periodicidade"),
    ]

    operations = [
        migrations.AlterField(
            model_name="produto",
            name="periodicidade",
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to="produtos.periodicidade"),
        ),
    ]
