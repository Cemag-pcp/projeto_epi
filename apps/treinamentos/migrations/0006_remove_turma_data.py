from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("treinamentos", "0005_turmaaula"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="turma",
            name="data",
        ),
    ]
