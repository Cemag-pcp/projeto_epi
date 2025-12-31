import os

from django.core.exceptions import ValidationError
from django.db import models

from apps.core.models import TenantModel

MAX_ATTACHMENT_SIZE = 3 * 1024 * 1024  # 3MB


def validate_attachment_size(value):
    if value.size > MAX_ATTACHMENT_SIZE:
        raise ValidationError("Arquivo excede o limite de 3MB.")


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


class Afastamento(TenantModel):
    funcionario = models.ForeignKey(Funcionario, on_delete=models.CASCADE, related_name="afastamentos")
    data_inicio = models.DateField()
    data_fim = models.DateField()
    motivo = models.CharField(max_length=255)
    arquivo = models.FileField(
        upload_to="funcionarios/afastamentos/",
        validators=[validate_attachment_size],
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["-data_inicio"]

    def dias_afastado(self):
        if not self.data_inicio or not self.data_fim:
            return ""
        dias = (self.data_fim - self.data_inicio).days + 1
        return max(dias, 0)

    def nome_arquivo(self):
        if not self.arquivo:
            return "-"
        return os.path.basename(self.arquivo.name)

    def __str__(self):
        return f"{self.funcionario} ({self.data_inicio} - {self.data_fim})"
