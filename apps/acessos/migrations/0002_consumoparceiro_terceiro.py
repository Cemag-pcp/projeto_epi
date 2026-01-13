from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("acessos", "0001_initial"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="consumoparceiro",
            name="empresa_parceira",
        ),
        migrations.AddField(
            model_name="consumoparceiro",
            name="terceiro",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="consumos",
                to="acessos.terceiro",
            ),
        ),
    ]
