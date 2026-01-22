from django.db import models
from django.utils import timezone

from apps.core.models import TenantModel


class Instrutor(TenantModel):
    nome = models.CharField(max_length=200)
    documento = models.CharField(max_length=50, blank=True)
    email = models.EmailField(blank=True)
    telefone = models.CharField(max_length=40, blank=True)
    ativo = models.BooleanField(default=True)

    class Meta:
        ordering = ["nome"]

    def __str__(self):
        return self.nome


class Treinamento(TenantModel):
    TIPO_CHOICES = [
        ("epi", "EPI"),
        ("nr", "NR"),
        ("processo", "Processo"),
        ("outro", "Outro"),
    ]

    nome = models.CharField(max_length=200)
    validade_dias = models.PositiveIntegerField(default=0)
    carga_horaria = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default="epi")
    obrigatorio = models.BooleanField(default=True)
    ativo = models.BooleanField(default=True)

    requisitos_cargos = models.ManyToManyField(
        "cargos.Cargo",
        blank=True,
        related_name="treinamentos",
    )
    requisitos_setores = models.ManyToManyField(
        "setores.Setor",
        blank=True,
        related_name="treinamentos",
    )
    requisitos_tipos_funcionario = models.ManyToManyField(
        "tipos_funcionario.TipoFuncionario",
        blank=True,
        related_name="treinamentos",
    )
    requisitos_epis = models.ManyToManyField(
        "produtos.Produto",
        blank=True,
        related_name="treinamentos_epi",
    )

    class Meta:
        ordering = ["nome"]

    def __str__(self):
        return self.nome

    def tipo_label(self):
        return self.get_tipo_display()

    def carga_horaria_label(self):
        return f"{self.carga_horaria}h"


class Turma(TenantModel):
    treinamento = models.ForeignKey(
        Treinamento,
        on_delete=models.PROTECT,
        related_name="turmas",
    )
    local = models.CharField(max_length=200)
    qtd_aulas = models.PositiveIntegerField(default=1)
    finalizada = models.BooleanField(default=False)
    instrutor = models.ForeignKey(
        Instrutor,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="turmas_instrutor",
    )
    capacidade = models.PositiveIntegerField(default=0)
    participantes = models.ManyToManyField(
        "funcionarios.Funcionario",
        blank=True,
        related_name="turmas_participante",
    )

    class Meta:
        ordering = ["-id"]

    def __str__(self):
        return f"{self.treinamento} - Turma {self.pk}"

    def capacidade_label(self):
        if not self.capacidade:
            return "Ilimitada"
        return self.capacidade

    def participantes_count(self):
        return self.participantes.count()


class TurmaAula(TenantModel):
    turma = models.ForeignKey(
        Turma,
        on_delete=models.CASCADE,
        related_name="aulas",
    )
    data = models.DateField()

    class Meta:
        ordering = ["data"]

    def __str__(self):
        return f"{self.turma} - {self.data}"


class TreinamentoPendencia(TenantModel):
    STATUS_CHOICES = [
        ("pendente", "Pendente"),
        ("agendado", "Agendado"),
        ("realizado", "Realizado"),
        ("aprovado", "Aprovado"),
        ("reprovado", "Reprovado"),
        ("expirado", "Expirado"),
    ]

    funcionario = models.ForeignKey(
        "funcionarios.Funcionario",
        on_delete=models.CASCADE,
        related_name="treinamentos_pendentes",
    )
    treinamento = models.ForeignKey(
        Treinamento,
        on_delete=models.CASCADE,
        related_name="pendencias",
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pendente")

    class Meta:
        ordering = ["-created_at"]
        unique_together = ("funcionario", "treinamento")

    def __str__(self):
        return f"{self.funcionario} - {self.treinamento} ({self.status})"


class TreinamentoParticipacao(TenantModel):
    RESULTADO_CHOICES = [
        ("aprovado", "Aprovado"),
        ("reprovado", "Reprovado"),
        ("ausente", "Ausente"),
    ]

    turma = models.ForeignKey(
        Turma,
        on_delete=models.CASCADE,
        related_name="participacoes",
    )
    funcionario = models.ForeignKey(
        "funcionarios.Funcionario",
        on_delete=models.CASCADE,
        related_name="treinamentos_participacoes",
    )
    presente = models.BooleanField(default=False)
    aulas_presentes = models.PositiveIntegerField(default=0)
    resultado = models.CharField(max_length=20, choices=RESULTADO_CHOICES, blank=True)
    nota = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
    avaliacao = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]
        unique_together = ("turma", "funcionario")

    def __str__(self):
        return f"{self.funcionario} - {self.turma}"


class TreinamentoPresencaAula(TenantModel):
    turma_aula = models.ForeignKey(
        TurmaAula,
        on_delete=models.CASCADE,
        related_name="presencas",
    )
    funcionario = models.ForeignKey(
        "funcionarios.Funcionario",
        on_delete=models.CASCADE,
        related_name="treinamentos_presencas",
    )
    presente = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]
        unique_together = ("turma_aula", "funcionario")

    def __str__(self):
        return f"{self.funcionario} - {self.turma_aula}"


class TreinamentoCertificado(TenantModel):
    funcionario = models.ForeignKey(
        "funcionarios.Funcionario",
        on_delete=models.CASCADE,
        related_name="treinamentos_certificados",
    )
    treinamento = models.ForeignKey(
        Treinamento,
        on_delete=models.CASCADE,
        related_name="certificados",
    )
    turma = models.ForeignKey(
        Turma,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="certificados",
    )
    data_emissao = models.DateField()
    validade_ate = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ["-data_emissao"]
        unique_together = ("funcionario", "treinamento")

    def __str__(self):
        return f"{self.funcionario} - {self.treinamento}"


class DocumentoTemplate(TenantModel):
    TIPO_CHOICES = [
        ("certificado", "Certificado"),
        ("recebimento_material", "Recebimento de material"),
        ("outro", "Outro"),
    ]
    titulo = models.CharField(max_length=200)
    tipo = models.CharField(max_length=30, choices=TIPO_CHOICES, default="certificado")
    corpo_html = models.TextField()
    logo = models.FileField(upload_to="documentos/", null=True, blank=True)
    ativo = models.BooleanField(default=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return f"{self.get_tipo_display()} - {self.titulo}"


class TreinamentoAlerta(TenantModel):
    certificado = models.ForeignKey(
        TreinamentoCertificado,
        on_delete=models.CASCADE,
        related_name="alertas",
    )
    funcionario = models.ForeignKey(
        "funcionarios.Funcionario",
        on_delete=models.CASCADE,
        related_name="treinamentos_alertas",
    )
    treinamento = models.ForeignKey(
        Treinamento,
        on_delete=models.CASCADE,
        related_name="alertas",
    )
    dias_para_vencer = models.PositiveSmallIntegerField()
    data_alerta = models.DateField(default=timezone.now)
    enviado = models.BooleanField(default=False)

    class Meta:
        ordering = ["-data_alerta"]
        unique_together = ("certificado", "dias_para_vencer")

    def __str__(self):
        return f"{self.funcionario} - {self.treinamento} ({self.dias_para_vencer}d)"
