from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.core.models import TenantModel


class AgenteCausador(TenantModel):
    nome = models.CharField(max_length=200)
    descricao = models.CharField(max_length=255, blank=True)
    ativo = models.BooleanField(default=True)

    class Meta:
        ordering = ["nome"]
        unique_together = ("company", "nome")

    def __str__(self):
        return self.nome


class ParteAtingida(TenantModel):
    nome = models.CharField(max_length=200)
    descricao = models.TextField(blank=True)
    ativo = models.BooleanField(default=True)

    class Meta:
        ordering = ["nome"]
        unique_together = ("company", "nome")

    def __str__(self):
        return self.nome


class NaturezaLesao(TenantModel):
    nome = models.CharField(max_length=200)
    ativo = models.BooleanField(default=True)

    class Meta:
        ordering = ["nome"]
        unique_together = ("company", "nome")

    def __str__(self):
        return self.nome


class EmitenteAtestado(TenantModel):
    nome = models.CharField(max_length=200)
    ativo = models.BooleanField(default=True)

    class Meta:
        ordering = ["nome"]
        unique_together = ("company", "nome")

    def __str__(self):
        return self.nome


class AcidenteTrabalho(TenantModel):
    NAO_APLICAVEL_CHOICES = [
        ("nao_aplicavel", "Nao aplicavel"),
    ]

    LATERALIDADE_CHOICES = [
        ("nao_aplicavel", "Nao aplicavel"),
        ("esquerda", "Esquerda"),
        ("direita", "Direita"),
        ("ambas", "Ambas"),
    ]

    SEVERIDADE_CHOICES = [
        ("nao_aplicavel", "Nao aplicavel"),
        ("leve", "Leve"),
        ("moderada", "Moderada"),
        ("critica", "Critica"),
    ]

    TIPO_REGISTRO_CHOICES = [
        ("acidente", "Acidente"),
        ("quase_acidente", "Quase acidente"),
    ]

    TIPO_ACIDENTE_CHOICES = [
        ("tipico", "Tipico"),
        ("doenca", "Doenca"),
        ("trajeto", "Trajeto"),
        ("outros", "Outros tipos"),
    ]

    TRAJETO_EVENTO_CHOICES = [
        ("atropelamento", "Atropelamento"),
        ("colisao", "Colisao"),
        ("outros", "Outros"),
    ]

    SITUACAO_GERADORA_CHOICES = [
        ("", "Selecione"),
        ("Impacto de pessoa contra objeto parado", "Impacto de pessoa contra objeto parado"),
        ("Impacto de pessoa contra objeto em movimento", "Impacto de pessoa contra objeto em movimento"),
        ("Impacto sofrido por pessoa de objeto que cai", "Impacto sofrido por pessoa de objeto que cai"),
        ("Impacto sofrido por pessoa de objeto projetado", "Impacto sofrido por pessoa de objeto projetado"),
        ("Impacto sofrido por pessoa, NIC", "Impacto sofrido por pessoa, NIC"),
        (
            "Queda de pessoa com diferença de nível de andaime, passagem, plataforma, etc.",
            "Queda de pessoa com diferença de nível de andaime, passagem, plataforma, etc.",
        ),
        (
            "Queda de pessoa com diferença de nível de escada móvel ou fixada",
            "Queda de pessoa com diferença de nível de escada móvel ou fixada",
        ),
        (
            "Queda de pessoa com diferença de nível de material empilhado",
            "Queda de pessoa com diferença de nível de material empilhado",
        ),
        (
            "Queda de pessoa com diferença de nível de veículo",
            "Queda de pessoa com diferença de nível de veículo",
        ),
        (
            "Queda de pessoa com diferença de nível em escada permanente",
            "Queda de pessoa com diferença de nível em escada permanente",
        ),
        (
            "Queda de pessoa com diferença de nível em poço, escavação, abertura no piso, etc.",
            "Queda de pessoa com diferença de nível em poço, escavação, abertura no piso, etc.",
        ),
        ("Queda de pessoa com diferença de nível, NIC", "Queda de pessoa com diferença de nível, NIC"),
        (
            "Queda de pessoa em mesmo nível em passagem ou superfície de sustentação",
            "Queda de pessoa em mesmo nível em passagem ou superfície de sustentação",
        ),
        (
            "Queda de pessoa em mesmo nível sobre ou contra alguma coisa",
            "Queda de pessoa em mesmo nível sobre ou contra alguma coisa",
        ),
        ("Queda de pessoa em mesmo nível, NIC", "Queda de pessoa em mesmo nível, NIC"),
        (
            "Aprisionamento em, sob ou entre objetos em movimento convergente",
            "Aprisionamento em, sob ou entre objetos em movimento convergente",
        ),
        (
            "Aprisionamento em, sob ou entre objeto parado e outro em movimento",
            "Aprisionamento em, sob ou entre objeto parado e outro em movimento",
        ),
        (
            "Aprisionamento em, sob ou entre dois ou mais objetos em movimento",
            "Aprisionamento em, sob ou entre dois ou mais objetos em movimento",
        ),
        (
            "Aprisionamento em, sob ou entre desabamento ou desmoronamento",
            "Aprisionamento em, sob ou entre desabamento ou desmoronamento",
        ),
        ("Aprisionamento em, sob ou entre, NIC", "Aprisionamento em, sob ou entre, NIC"),
        (
            "Atrito ou abrasão por encostar, pisar, ajoelhar ou sentar em objeto",
            "Atrito ou abrasão por encostar, pisar, ajoelhar ou sentar em objeto",
        ),
        ("Atrito ou abrasão por manusear objeto", "Atrito ou abrasão por manusear objeto"),
        ("Atrito ou abrasão por objeto em vibração", "Atrito ou abrasão por objeto em vibração"),
        ("Atrito ou abrasão por corpo estranho no olho", "Atrito ou abrasão por corpo estranho no olho"),
        ("Atrito ou abrasão por compressão repetitiva", "Atrito ou abrasão por compressão repetitiva"),
        ("Atrito ou abrasão, NIC", "Atrito ou abrasão, NIC"),
        ("Reação do corpo a movimento involuntário", "Reação do corpo a movimento involuntário"),
        ("Reação do corpo a movimento voluntário", "Reação do corpo a movimento voluntário"),
        ("Esforço excessivo ao erguer objeto", "Esforço excessivo ao erguer objeto"),
        ("Esforço excessivo ao empurrar ou puxar objeto", "Esforço excessivo ao empurrar ou puxar objeto"),
        (
            "Esforço excessivo ao manejar, sacudir ou arremessar objeto",
            "Esforço excessivo ao manejar, sacudir ou arremessar objeto",
        ),
        ("Esforço excessivo, NIC", "Esforço excessivo, NIC"),
        ("Elétrica, exposição à energia", "Elétrica, exposição à energia"),
        ("Temperatura muito alta, contato com objeto ou substância a", "Temperatura muito alta, contato com objeto ou substância a"),
        ("Temperatura muito baixa, contato com objeto ou substância a", "Temperatura muito baixa, contato com objeto ou substância a"),
        ("Temperatura ambiente elevada, exposição à", "Temperatura ambiente elevada, exposição à"),
        ("Temperatura ambiente baixa, exposição à", "Temperatura ambiente baixa, exposição à"),
        ("Inalação de substância cáustica, tóxica ou nociva", "Inalação de substância cáustica, tóxica ou nociva"),
        ("Ingestão de substância cáustica", "Ingestão de substância cáustica"),
        ("Absorção de substância cáustica", "Absorção de substância cáustica"),
        ("Inalação, ingestão ou absorção, NIC", "Inalação, ingestão ou absorção, NIC"),
        ("Imersão", "Imersão"),
        ("Radiação não ionizante, exposição à", "Radiação não ionizante, exposição à"),
        ("Radiação ionizante, exposição à", "Radiação ionizante, exposição à"),
        ("Ruído, exposição ao", "Ruído, exposição ao"),
        ("Vibração, exposição à", "Vibração, exposição à"),
        ("Pressão ambiente, exposição à", "Pressão ambiente, exposição à"),
        ("Exposição à pressão ambiente elevada", "Exposição à pressão ambiente elevada"),
        ("Exposição à pressão ambiente baixa", "Exposição à pressão ambiente baixa"),
        ("Poluição da água, ação da (exposição à poluição da água)", "Poluição da água, ação da (exposição à poluição da água)"),
        ("Poluição do ar, ação da (exposição à poluição do ar)", "Poluição do ar, ação da (exposição à poluição do ar)"),
        ("Poluição do solo, ação da (exposição à poluição do solo)", "Poluição do solo, ação da (exposição à poluição do solo)"),
        ("Poluição, NIC, exposição à (exposição à poluição, NIC)", "Poluição, NIC, exposição à (exposição à poluição, NIC)"),
        (
            "Ataque de ser vivo por mordedura, picada, chifrada, coice, etc.",
            "Ataque de ser vivo por mordedura, picada, chifrada, coice, etc.",
        ),
        ("Ataque de ser vivo com peçonha", "Ataque de ser vivo com peçonha"),
        ("Ataque de ser vivo com transmissão de doença", "Ataque de ser vivo com transmissão de doença"),
        ("Ataque de ser vivo, NIC", "Ataque de ser vivo, NIC"),
        ("Tipo, NIC", "Tipo, NIC"),
        ("Tipo inexistente", "Tipo inexistente"),
    ]

    TIPO_LOCAL_CHOICES = [
        ("", "Selecione"),
        ("estabelecimento_brasil", "Estab. do empregador Brasil"),
        ("estabelecimento_exterior", "Estab. do empregador Exterior"),
        ("estabelecimento_terceiros", "Estab. de terceiros"),
        ("via_publica", "Via pública"),
        ("area_rural", "Área rural"),
        ("embarcacao", "Embarcação"),
        ("outros", "Outros"),
    ]

    ESTADO_CHOICES = [
        ("", "Selecione"),
        ("AC", "Acre"),
        ("AL", "Alagoas"),
        ("AP", "Amapa"),
        ("AM", "Amazonas"),
        ("BA", "Bahia"),
        ("CE", "Ceara"),
        ("DF", "Distrito Federal"),
        ("ES", "Espirito Santo"),
        ("GO", "Goias"),
        ("MA", "Maranhao"),
        ("MT", "Mato Grosso"),
        ("MS", "Mato Grosso do Sul"),
        ("MG", "Minas Gerais"),
        ("PA", "Para"),
        ("PB", "Paraiba"),
        ("PR", "Parana"),
        ("PE", "Pernambuco"),
        ("PI", "Piaui"),
        ("RJ", "Rio de Janeiro"),
        ("RN", "Rio Grande do Norte"),
        ("RS", "Rio Grande do Sul"),
        ("RO", "Rondonia"),
        ("RR", "Roraima"),
        ("SC", "Santa Catarina"),
        ("SP", "Sao Paulo"),
        ("SE", "Sergipe"),
        ("TO", "Tocantins"),
    ]

    TIPO_LOGRADOURO_CHOICES = [
        ("", "Selecione"),
        ("rua", "Rua"),
        ("avenida", "Avenida"),
        ("estrada", "Estrada"),
        ("praca", "Praca"),
        ("area", "Area"),
        ("acesso", "Acesso"),
        ("alameda", "Alameda"),
        ("bairro", "Bairro"),
        ("beco", "Beco"),
        ("boulevard", "Boulevard"),
        ("caminho", "Caminho"),
        ("chacara", "Chacara"),
        ("conjunto", "Conjunto"),
        ("condominio", "Condominio"),
        ("distrito", "Distrito"),
        ("fazenda", "Fazenda"),
        ("jardim", "Jardim"),
        ("loteamento", "Loteamento"),
        ("parque", "Parque"),
        ("rodovia", "Rodovia"),
        ("rua_particular", "Rua Particular"),
        ("servidao", "Servidao"),
        ("sitio", "Sitio"),
        ("travessa", "Travessa"),
        ("via", "Via"),
        ("vila", "Vila"),
        ("outros", "Outros"),
    ]

    funcionario = models.ForeignKey(
        "funcionarios.Funcionario",
        on_delete=models.PROTECT,
        related_name="acidentes_trabalho",
    )
    tipo_registro = models.CharField(
        max_length=20,
        choices=TIPO_REGISTRO_CHOICES,
        default="acidente",
    )
    tipo_acidente = models.CharField(
        max_length=20,
        choices=TIPO_ACIDENTE_CHOICES,
        default="tipico",
    )
    trajeto_evento = models.CharField(
        max_length=20,
        choices=TRAJETO_EVENTO_CHOICES,
        blank=True,
    )
    situacao_geradora = models.CharField(
        max_length=255,
        choices=SITUACAO_GERADORA_CHOICES,
        default="",
    )
    agente_causador = models.ForeignKey(
        "acidentes.AgenteCausador",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="acidentes",
    )
    parte_atingida = models.ForeignKey(
        "acidentes.ParteAtingida",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="acidentes",
    )
    lateralidade = models.CharField(
        max_length=20,
        choices=LATERALIDADE_CHOICES,
        default="nao_aplicavel",
    )
    severidade_real = models.CharField(
        max_length=20,
        choices=SEVERIDADE_CHOICES,
        default="nao_aplicavel",
    )
    severidade_potencial = models.CharField(
        max_length=20,
        choices=SEVERIDADE_CHOICES,
        default="nao_aplicavel",
    )
    ultimo_dia_trabalhado = models.DateField(null=True, blank=True)
    horas_trabalhadas = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    houve_afastamento = models.BooleanField(default=False)
    houve_obito = models.BooleanField(default=False)
    data_obito = models.DateField(null=True, blank=True)
    houve_comunicacao_policia = models.BooleanField(default=False)
    data_ocorrencia = models.DateTimeField(default=timezone.now)
    descricao_ocorrido = models.TextField(blank=True)
    observacao = models.TextField(blank=True)

    tipo_local = models.CharField(max_length=40, choices=TIPO_LOCAL_CHOICES)
    ambiente = models.CharField(max_length=120)
    descricao_local = models.CharField(max_length=80)

    cep = models.CharField("CEP", max_length=9, blank=True)
    estado = models.CharField("Estado", max_length=2, choices=ESTADO_CHOICES)
    cidade = models.CharField("Cidade", max_length=120)

    tipo_logradouro = models.CharField("Tipo do Logradouro", max_length=40, choices=TIPO_LOGRADOURO_CHOICES)
    endereco = models.CharField("Endereco", max_length=100, blank=True)
    numero = models.CharField("Numero", max_length=10, blank=True)
    complemento = models.CharField("Complemento", max_length=100, blank=True)
    bairro = models.CharField("Bairro", max_length=90, blank=True)

    existe_atestado = models.BooleanField(default=False)
    data_atendimento = models.DateField(null=True, blank=True)
    houve_internacao = models.BooleanField(default=False)
    duracao_tratamento_dias = models.PositiveIntegerField(null=True, blank=True)
    indicado_afastamento = models.BooleanField(default=False)
    natureza_lesao = models.ForeignKey(
        "acidentes.NaturezaLesao",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="acidentes",
    )
    diagnostico_provavel = models.TextField(blank=True)
    codigo_cid10 = models.CharField(max_length=12, blank=True)
    observacao_atestado = models.TextField(blank=True)
    emitente = models.ForeignKey(
        "acidentes.EmitenteAtestado",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="acidentes",
    )
    codigo_cnes = models.CharField(max_length=20, blank=True)

    analise_data_conclusao = models.DateField(null=True, blank=True)
    analise_preenchido_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="acidentes_analise_preenchidos",
    )
    analise_coordenador = models.ForeignKey(
        "funcionarios.Funcionario",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="acidentes_analise_coordenados",
    )
    analise_envolvidos = models.ManyToManyField(
        "funcionarios.Funcionario",
        blank=True,
        related_name="acidentes_analise_envolvidos",
    )
    analise_participantes = models.ManyToManyField(
        "funcionarios.Funcionario",
        blank=True,
        related_name="acidentes_analise_participantes",
    )

    class Meta:
        ordering = ["-data_ocorrencia"]

    def __str__(self):
        return f"Acidente #{self.pk} - {self.funcionario}"

    def cidade_uf(self):
        cidade = self.cidade or "-"
        uf = self.estado or "-"
        return f"{cidade}/{uf}"

    @property
    def create_date(self):
        return self.created_at

    @property
    def update_date(self):
        return self.updated_at


class AcidenteFato(TenantModel):
    acidente = models.ForeignKey(
        AcidenteTrabalho,
        on_delete=models.CASCADE,
        related_name="fatos",
    )
    hora_ocorrencia = models.TimeField()
    detalhamento = models.TextField()

    class Meta:
        ordering = ["hora_ocorrencia", "pk"]

    def __str__(self):
        return f"Fato {self.hora_ocorrencia} - {self.acidente_id}"


class AcidenteAnexo(TenantModel):
    acidente = models.ForeignKey(
        AcidenteTrabalho,
        on_delete=models.CASCADE,
        related_name="anexos",
    )
    arquivo = models.FileField(upload_to="acidentes/anexos/")
    descricao = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ["pk"]

    def __str__(self):
        return f"Anexo {self.pk} - {self.acidente_id}"
