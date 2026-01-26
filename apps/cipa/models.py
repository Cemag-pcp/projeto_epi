import uuid

from django.db import models
from django.db.models.functions import Lower
from django.core.validators import MaxValueValidator, MinValueValidator

from apps.core.models import TenantModel


class CipaEleicao(TenantModel):
    ESCOPO_CHOICES = [
        ("global", "Global"),
        ("planta", "Por planta"),
    ]

    STATUS_CHOICES = [
        ("rascunho", "Rascunho"),
        ("inscricoes", "Inscricoes"),
        ("votacao", "Votacao"),
        ("encerrada", "Encerrada"),
        ("cancelada", "Cancelada"),
    ]
    
    WIZARD_STEP_LABELS = {
        1: "Programação",
        2: "Início",
        3: "Comunicação",
        4: "Candidatura",
        5: "Divulgação",
    }

    nome = models.CharField(max_length=200)
    escopo = models.CharField(max_length=20, choices=ESCOPO_CHOICES, default="planta")
    planta = models.ForeignKey(
        "funcionarios.Planta",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="cipa_eleicoes",
    )
    mandato_inicio = models.DateField(null=True, blank=True)
    mandato_fim = models.DateField(null=True, blank=True)

    qt_colaboradores = models.PositiveIntegerField(null=True, blank=True)
    qt_efetivos = models.PositiveIntegerField(null=True, blank=True)
    qt_suplentes = models.PositiveIntegerField(null=True, blank=True)
    grau_risco = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(4)],
    )

    eleicao_extraordinaria = models.BooleanField(default=False)
    data_fim_ultimo_mandato = models.DateField(null=True, blank=True)
    data_inicio_processo_eleitoral = models.DateField(null=True, blank=True)
    data_comunicacao_sindicato = models.DateField(null=True, blank=True)
    data_abertura_candidaturas = models.DateField(null=True, blank=True)
    data_divulgacao_candidatos = models.DateField(null=True, blank=True)
    data_eleicao = models.DateField(null=True, blank=True)
    data_divulgacao = models.DateField(null=True, blank=True)

    candidatura_publica_token = models.UUIDField(default=uuid.uuid4, editable=False)
    candidatura_publica_ativa = models.BooleanField(default=False)
    votacao_publica_token = models.UUIDField(default=uuid.uuid4, editable=False)
    votacao_publica_ativa = models.BooleanField(default=False)
    wizard_step = models.PositiveSmallIntegerField(default=1)

    votacao_inicio = models.DateTimeField(null=True, blank=True)
    votacao_fim = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="rascunho")
    observacoes = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        constraints = [
            models.CheckConstraint(
                name="cipa_eleicao_scope_planta_consistency",
                check=(
                    models.Q(wizard_step=1, planta__isnull=True)
                    | models.Q(escopo="global", planta__isnull=True)
                    | models.Q(escopo="planta", planta__isnull=False)
                ),
            ),
            models.UniqueConstraint(
                Lower("nome"),
                "company",
                name="cipa_eleicao_unique_company_nome_ci",
            ),
        ]

    def __str__(self):
        return self.nome

    @property
    def wizard_step_label(self):
        return self.WIZARD_STEP_LABELS.get(int(self.wizard_step or 1), "-")


class CipaCandidato(TenantModel):
    STATUS_CHOICES = [
        ("pendente", "Pendente"),
        ("aprovado", "Aprovado"),
        ("indeferido", "Indeferido"),
    ]

    eleicao = models.ForeignKey(CipaEleicao, on_delete=models.CASCADE, related_name="candidatos")
    funcionario = models.ForeignKey(
        "funcionarios.Funcionario",
        on_delete=models.PROTECT,
        related_name="cipa_candidaturas",
    )
    numero = models.PositiveIntegerField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pendente")
    motivo_indeferimento = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["numero", "id"]
        unique_together = (
            ("company", "eleicao", "funcionario"),
        )

    def __str__(self):
        return f"{self.funcionario} - {self.eleicao}"


class CipaVoto(TenantModel):
    TIPO_CHOICES = [
        ("candidato", "Candidato"),
        ("branco", "Branco"),
        ("nulo", "Nulo"),
    ]

    eleicao = models.ForeignKey(CipaEleicao, on_delete=models.CASCADE, related_name="votos")
    eleitor = models.ForeignKey(
        "funcionarios.Funcionario",
        on_delete=models.PROTECT,
        related_name="cipa_votos",
    )
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default="candidato")
    candidato = models.ForeignKey(
        CipaCandidato,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="votos",
    )

    class Meta:
        ordering = ["-created_at", "-id"]
        unique_together = (
            ("company", "eleicao", "eleitor"),
        )

    def __str__(self):
        return f"Voto {self.eleicao} - {self.eleitor}"
