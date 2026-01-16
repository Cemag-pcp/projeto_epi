from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("acessos", "0002_consumoparceiro_terceiro"),
    ]

    operations = [
        migrations.AddField(
            model_name="consumoparceiro",
            name="assinatura",
            field=models.ImageField(
                blank=True,
                null=True,
                upload_to="acessos/consumos/assinaturas/",
            ),
        ),
    ]

