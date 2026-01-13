from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("treinamentos", "0003_treinamentoparticipacao"),
    ]

    operations = [
        migrations.AddField(
            model_name="turma",
            name="qtd_aulas",
            field=models.PositiveIntegerField(default=1),
        ),
        migrations.AddField(
            model_name="treinamentoparticipacao",
            name="aulas_presentes",
            field=models.PositiveIntegerField(default=0),
        ),
    ]
