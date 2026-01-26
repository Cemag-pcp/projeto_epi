from datetime import date, timedelta

from django import forms
from django.db.models import Max

from apps.funcionarios.models import Funcionario

from .models import CipaCandidato, CipaEleicao


def compute_default_dates(data_fim_ultimo_mandato: date) -> dict:
    """
    Datas padrão (ajustáveis) a partir do fim do último mandato.
    Observação: esses offsets podem variar conforme norma/empresa.
    """
    if not data_fim_ultimo_mandato:
        return {}

    mandato_inicio = data_fim_ultimo_mandato + timedelta(days=1)
    mandato_fim = mandato_inicio + timedelta(days=364)
    data_eleicao = data_fim_ultimo_mandato - timedelta(days=30)
    return {
        "mandato_inicio": mandato_inicio,
        "mandato_fim": mandato_fim,
        "data_eleicao": data_eleicao,
        "data_divulgacao_candidatos": data_eleicao - timedelta(days=7),
        "data_abertura_candidaturas": data_eleicao - timedelta(days=15),
        "data_comunicacao_sindicato": data_fim_ultimo_mandato - timedelta(days=60),
        "data_inicio_processo_eleitoral": data_fim_ultimo_mandato - timedelta(days=90),
    }


class WizardBaseForm(forms.ModelForm):
    required_for_next: list[str] = []

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.required = False

    def validate_for_next(self) -> bool:
        ok = True
        for name in self.required_for_next:
            value = self.cleaned_data.get(name)
            if value in (None, "", [], ()):
                self.add_error(name, "Campo obrigatório para avançar.")
                ok = False
        return ok


class CipaEleicaoProgramacaoForm(WizardBaseForm):
    required_for_next = ["nome", "qt_colaboradores", "qt_efetivos", "qt_suplentes", "grau_risco"]

    class Meta:
        model = CipaEleicao
        fields = [
            "nome",
            "escopo",
            "planta",
            "qt_colaboradores",
            "qt_efetivos",
            "qt_suplentes",
            "grau_risco",
        ]
        widgets = {
            "nome": forms.TextInput(attrs={"class": "form-control"}),
            "escopo": forms.Select(attrs={"class": "form-select"}),
            "planta": forms.Select(attrs={"class": "form-select"}),
            "qt_colaboradores": forms.NumberInput(attrs={"class": "form-control", "min": 0}),
            "qt_efetivos": forms.NumberInput(attrs={"class": "form-control", "min": 0}),
            "qt_suplentes": forms.NumberInput(attrs={"class": "form-control", "min": 0}),
            "grau_risco": forms.NumberInput(attrs={"class": "form-control", "min": 1, "max": 4}),
        }

    def validate_for_next(self) -> bool:
        ok = super().validate_for_next()
        escopo = self.cleaned_data.get("escopo")
        planta = self.cleaned_data.get("planta")
        if escopo == "global":
            self.cleaned_data["planta"] = None
        if escopo == "planta" and planta is None:
            self.add_error("planta", "Campo obrigatório para avançar.")
            ok = False
        return ok

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("escopo") == "global":
            cleaned["planta"] = None
        return cleaned


class CipaEleicaoInicioForm(WizardBaseForm):
    required_for_next = ["data_fim_ultimo_mandato"]

    class Meta:
        model = CipaEleicao
        fields = [
            "eleicao_extraordinaria",
            "data_fim_ultimo_mandato",
            "mandato_inicio",
            "mandato_fim",
            "data_eleicao",
            "data_divulgacao_candidatos",
            "data_abertura_candidaturas",
            "data_comunicacao_sindicato",
            "data_inicio_processo_eleitoral",
        ]
        widgets = {
            "eleicao_extraordinaria": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "data_fim_ultimo_mandato": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "mandato_inicio": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "mandato_fim": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "data_eleicao": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "data_divulgacao_candidatos": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "data_abertura_candidaturas": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "data_comunicacao_sindicato": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "data_inicio_processo_eleitoral": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
        }


class CipaEleicaoSindicatoForm(WizardBaseForm):
    class Meta:
        model = CipaEleicao
        fields = [
            "data_comunicacao_sindicato",
            "observacoes",
        ]
        widgets = {
            "data_comunicacao_sindicato": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "observacoes": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
        }


class CipaEleicaoCandidaturaForm(WizardBaseForm):
    class Meta:
        model = CipaEleicao
        fields = [
            "data_abertura_candidaturas",
            "candidatura_publica_ativa",
        ]
        widgets = {
            "data_abertura_candidaturas": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "candidatura_publica_ativa": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


class CipaEleicaoDivulgacaoForm(WizardBaseForm):
    class Meta:
        model = CipaEleicao
        fields = [
            "data_divulgacao_candidatos",
            "data_divulgacao",
            "observacoes",
        ]
        widgets = {
            "data_divulgacao_candidatos": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "data_divulgacao": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "observacoes": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
        }


class CipaCandidaturaPublicaForm(forms.Form):
    funcionario = forms.ModelChoiceField(
        queryset=Funcionario.objects.none(),
        widget=forms.Select(attrs={"class": "form-select"}),
        label="Funcionário",
    )

    def __init__(self, *args, **kwargs):
        self.eleicao: CipaEleicao = kwargs.pop("eleicao")
        company = kwargs.pop("company")
        super().__init__(*args, **kwargs)
        qs = Funcionario.objects.filter(company=company, ativo=True).select_related("planta").order_by("nome")
        if self.eleicao.escopo == "planta" and self.eleicao.planta_id:
            qs = qs.filter(planta_id=self.eleicao.planta_id)
        self.fields["funcionario"].queryset = qs

    def save(self, *, company, user):
        funcionario = self.cleaned_data["funcionario"]
        if CipaCandidato.objects.filter(company=company, eleicao=self.eleicao, funcionario=funcionario).exists():
            raise forms.ValidationError("Este funcionário já está inscrito como candidato nesta eleição.")

        max_num = (
            CipaCandidato.objects.filter(company=company, eleicao=self.eleicao)
            .aggregate(m=Max("numero"))
            .get("m")
        )
        numero = (max_num or 0) + 1
        return CipaCandidato.objects.create(
            company=company,
            created_by=user,
            updated_by=user,
            eleicao=self.eleicao,
            funcionario=funcionario,
            numero=numero,
            status="pendente",
        )


class CipaVotacaoPublicaForm(forms.Form):
    eleitor = forms.ModelChoiceField(
        queryset=Funcionario.objects.none(),
        widget=forms.Select(attrs={"class": "form-select"}),
        label="Eleitor",
    )
    tipo = forms.ChoiceField(
        choices=[("candidato", "Candidato"), ("branco", "Branco"), ("nulo", "Nulo")],
        widget=forms.Select(attrs={"class": "form-select"}),
        label="Tipo de voto",
        initial="candidato",
    )
    candidato = forms.ModelChoiceField(
        queryset=CipaCandidato.objects.none(),
        required=False,
        widget=forms.Select(attrs={"class": "form-select"}),
        label="Candidato",
    )

    def __init__(self, *args, **kwargs):
        self.eleicao: CipaEleicao = kwargs.pop("eleicao")
        company = kwargs.pop("company")
        super().__init__(*args, **kwargs)
        eleitores = Funcionario.objects.filter(company=company, ativo=True).select_related("planta").order_by("nome")
        if self.eleicao.escopo == "planta" and self.eleicao.planta_id:
            eleitores = eleitores.filter(planta_id=self.eleicao.planta_id)
        self.fields["eleitor"].queryset = eleitores

        candidatos = (
            CipaCandidato.objects.filter(company=company, eleicao=self.eleicao, status="aprovado")
            .select_related("funcionario")
            .order_by("numero", "id")
        )
        self.fields["candidato"].queryset = candidatos

    def clean(self):
        cleaned = super().clean()
        tipo = cleaned.get("tipo")
        candidato = cleaned.get("candidato")
        if tipo == "candidato" and not candidato:
            self.add_error("candidato", "Selecione um candidato.")
        if tipo in ("branco", "nulo"):
            cleaned["candidato"] = None
        return cleaned
