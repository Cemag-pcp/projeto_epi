import os

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from apps.core.models import TenantModel

MAX_ATTACHMENT_SIZE = 3 * 1024 * 1024  # 3MB


def validate_attachment_size(value):
    if value.size > MAX_ATTACHMENT_SIZE:
        raise ValidationError("Arquivo excede o limite de 3MB.")


class GHE(TenantModel):
    codigo = models.CharField(max_length=50, default="")
    descricao = models.CharField(max_length=200, default="")
    responsavel = models.ForeignKey(
        "Funcionario", on_delete=models.SET_NULL, null=True, blank=True, related_name="ghes_responsaveis"
    )
    ativo = models.BooleanField(default=True)

    class Meta:
        ordering = ["codigo", "descricao"]

    def __str__(self):
        if self.codigo and self.descricao:
            return f"{self.codigo} - {self.descricao}"
        return self.descricao or self.codigo


class CentroCusto(TenantModel):
    nome = models.CharField(max_length=120)
    ativo = models.BooleanField(default=True)

    class Meta:
        ordering = ["nome"]

    def __str__(self):
        return self.nome


class Turno(TenantModel):
    nome = models.CharField(max_length=80)
    ativo = models.BooleanField(default=True)

    class Meta:
        ordering = ["nome"]

    def __str__(self):
        return self.nome


class Funcionario(TenantModel):
    VALIDACAO_RECEBIMENTO_CHOICES = [
        ("nenhum", "Nenhum"),
        ("senha", "Senha"),
    ]
    foto = models.ImageField(upload_to="funcionarios/fotos/", null=True, blank=True)
    identificador = models.CharField(max_length=80, blank=True)
    registro = models.CharField(max_length=50, null=True, blank=True)
    nome = models.CharField(max_length=200)
    rg = models.CharField(max_length=20, blank=True)
    cpf = models.CharField(max_length=14, blank=True)
    pis = models.CharField(max_length=20, blank=True)
    data_nascimento = models.DateField(null=True, blank=True)
    turno = models.ForeignKey("Turno", on_delete=models.SET_NULL, null=True, blank=True)
    email = models.EmailField(blank=True)
    telefone = models.CharField(max_length=40, blank=True)
    cargo = models.ForeignKey("cargos.Cargo", on_delete=models.SET_NULL, null=True, blank=True)
    setor = models.ForeignKey("setores.Setor", on_delete=models.SET_NULL, null=True, blank=True)
    planta = models.ForeignKey("Planta", on_delete=models.SET_NULL, null=True, blank=True)
    centro_custo = models.ForeignKey("CentroCusto", on_delete=models.SET_NULL, null=True, blank=True)
    ghe = models.ForeignKey("GHE", on_delete=models.SET_NULL, null=True, blank=True)
    lider = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True, related_name="liderados"
    )
    gestor = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True, related_name="gerenciados"
    )
    tipo = models.ForeignKey("tipos_funcionario.TipoFuncionario", on_delete=models.SET_NULL, null=True, blank=True)
    data_admissao = models.DateField(null=True, blank=True)
    data_demissao = models.DateField(null=True, blank=True)
    categoria_cnh = models.CharField(max_length=5, blank=True)
    validacao_recebimento = models.CharField(
        max_length=10,
        choices=VALIDACAO_RECEBIMENTO_CHOICES,
        default="nenhum",
    )
    senha_recebimento = models.CharField(max_length=128, blank=True)
    ativo = models.BooleanField(default=True)
    temporario = models.BooleanField(default=False)
    afastado = models.BooleanField(default=False)
    inicio_ferias = models.DateField(null=True, blank=True)
    fim_ferias = models.DateField(null=True, blank=True)
    riscos = models.ManyToManyField("Risco", blank=True, related_name="funcionarios")

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


class Advertencia(TenantModel):
    TIPO_CHOICES = [
        ("uso_incorreto", "Uso incorreto"),
        ("uso_indevido", "Uso indevido"),
        ("ausencia", "Ausencia de uso"),
    ]

    funcionario = models.ForeignKey(Funcionario, on_delete=models.CASCADE, related_name="advertencias")
    data = models.DateField(default=timezone.localdate)
    tipo = models.CharField(max_length=30, choices=TIPO_CHOICES, default="uso_incorreto")
    descricao = models.TextField()

    class Meta:
        ordering = ["-data"]

    def __str__(self):
        return f"{self.funcionario} - {self.get_tipo_display()} ({self.data})"

    def tipo_label(self):
        return self.get_tipo_display()


class MotivoAfastamento(TenantModel):
    nome = models.CharField(max_length=200)
    ativo = models.BooleanField(default=True)

    class Meta:
        ordering = ["nome"]

    def __str__(self):
        return self.nome


class Planta(TenantModel):
    nome = models.CharField(max_length=120)
    ativo = models.BooleanField(default=True)

    class Meta:
        ordering = ["nome"]

    def __str__(self):
        return self.nome


class Risco(TenantModel):
    NIVEL_CHOICES = [
        ("baixo", "Baixo"),
        ("medio", "Medio"),
        ("alto", "Alto"),
    ]

    nome = models.CharField(max_length=200)
    descricao = models.TextField(blank=True)
    nivel = models.CharField(max_length=20, choices=NIVEL_CHOICES, default="baixo")
    ativo = models.BooleanField(default=True)

    class Meta:
        ordering = ["nome"]

    def __str__(self):
        return self.nome


class FuncionarioAnexo(TenantModel):
    funcionario = models.ForeignKey(Funcionario, on_delete=models.CASCADE, related_name="anexos")
    arquivo = models.FileField(upload_to="funcionarios/anexos/")
    descricao = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.funcionario} - {self.arquivo.name}"


class FuncionarioHistorico(TenantModel):
    funcionario = models.ForeignKey(Funcionario, on_delete=models.CASCADE, related_name="historico")
    descricao = models.TextField()

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.funcionario} - {self.descricao[:50]}"


class FuncionarioProduto(TenantModel):
    funcionario = models.ForeignKey(
        Funcionario,
        on_delete=models.CASCADE,
        related_name="produtos_disponiveis",
    )
    produto_fornecedor = models.ForeignKey(
        "produtos.ProdutoFornecedor",
        on_delete=models.CASCADE,
        related_name="funcionarios_disponiveis",
    )
    ativo = models.BooleanField(default=True)

    class Meta:
        unique_together = ("funcionario", "produto_fornecedor")

    def __str__(self):
        return f"{self.funcionario} - {self.produto_fornecedor}"
