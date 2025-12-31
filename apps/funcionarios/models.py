from django.db import models

from apps.core.models import TenantModel


class Funcionario(TenantModel):
    foto = models.ImageField(upload_to="funcionarios/fotos/", null=True, blank=True)
    registro = models.CharField(max_length=50, null=True, blank=True)
    nome = models.CharField(max_length=200)
    turno = models.CharField(max_length=80, blank=True)
    email = models.EmailField(blank=True)
    telefone = models.CharField(max_length=40, blank=True)
    cargo = models.ForeignKey("cargos.Cargo", on_delete=models.SET_NULL, null=True, blank=True)
    setor = models.ForeignKey("setores.Setor", on_delete=models.SET_NULL, null=True, blank=True)
    centro_custo = models.CharField(max_length=120, blank=True)
    ghe = models.CharField(max_length=120, blank=True)
    lider = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True, related_name="liderados"
    )
    gestor = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True, related_name="gerenciados"
    )
    tipo = models.ForeignKey("tipos_funcionario.TipoFuncionario", on_delete=models.SET_NULL, null=True, blank=True)
    data_admissao = models.DateField(null=True, blank=True)
    ativo = models.BooleanField(default=True)

    def __str__(self):
        return self.nome
