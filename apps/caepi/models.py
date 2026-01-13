from django.db import models


class CaEPI(models.Model):
    registro_ca = models.CharField(max_length=50, db_index=True)
    data_validade = models.DateField(null=True, blank=True, db_index=True)
    situacao = models.TextField(blank=True)
    nr_processo = models.TextField(blank=True)
    cnpj = models.CharField(max_length=20, blank=True)
    razao_social = models.CharField(max_length=255, blank=True)
    natureza = models.TextField(blank=True)
    nome_equipamento = models.CharField(max_length=255, blank=True)
    descricao_equipamento = models.TextField(blank=True)
    marca_ca = models.TextField(blank=True)
    referencia = models.TextField(blank=True)
    cor = models.TextField(blank=True)
    aprovado_para_laudo = models.TextField(blank=True)
    restricao_laudo = models.TextField(blank=True)
    observacao_analise_laudo = models.TextField(blank=True)
    cnpj_laboratorio = models.CharField(max_length=20, blank=True)
    razao_social_laboratorio = models.CharField(max_length=255, blank=True)
    nr_laudo = models.TextField(blank=True)
    norma = models.TextField(blank=True)
    ultima_atualizacao = models.DateTimeField()

    class Meta:
        ordering = ["-data_validade", "registro_ca"]

    def __str__(self):
        return f"{self.registro_ca} - {self.nome_equipamento}"
