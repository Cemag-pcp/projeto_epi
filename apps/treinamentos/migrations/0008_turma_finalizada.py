from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("treinamentos", "0007_treinamentopresencaaula"),
    ]

    operations = [
        migrations.AddField(
            model_name="turma",
            name="finalizada",
            field=models.BooleanField(default=False),
        ),
    ]
