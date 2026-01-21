from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("acessos", "0003_consumoparceiro_assinatura"),
        ("depositos", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="consumoparceiro",
            name="deposito",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="consumos_parceiros",
                to="depositos.deposito",
            ),
        ),
    ]
