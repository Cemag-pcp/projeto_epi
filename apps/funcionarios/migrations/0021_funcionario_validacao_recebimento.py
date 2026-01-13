from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("funcionarios", "0020_funcionarioproduto"),
    ]

    operations = [
        migrations.AddField(
            model_name="funcionario",
            name="validacao_recebimento",
            field=models.CharField(
                choices=[("nenhum", "Nenhum"), ("senha", "Senha")],
                default="nenhum",
                max_length=10,
            ),
        ),
        migrations.AddField(
            model_name="funcionario",
            name="senha_recebimento",
            field=models.CharField(blank=True, max_length=128),
        ),
    ]
