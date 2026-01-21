from django import forms
from django.contrib.auth import get_user_model
from django.forms import inlineformset_factory

from apps.core.forms import BootstrapModelForm
from apps.funcionarios.models import Funcionario

from .models import (
    AcidenteTrabalho,
    AcidenteAnexo,
    AcidenteFato,
    AgenteCausador,
    EmitenteAtestado,
    NaturezaLesao,
    ParteAtingida,
)


class AcidenteTrabalhoForm(BootstrapModelForm):
    tipo_registro = forms.ChoiceField(
        label="Registro",
        choices=AcidenteTrabalho.TIPO_REGISTRO_CHOICES,
        widget=forms.RadioSelect(attrs={"class": "form-check-input"}),
        initial="acidente",
    )
    tipo_acidente = forms.ChoiceField(
        label="Tipo do acidente",
        choices=AcidenteTrabalho.TIPO_ACIDENTE_CHOICES,
        widget=forms.RadioSelect(attrs={"class": "form-check-input"}),
        initial="tipico",
    )
    trajeto_evento = forms.ChoiceField(
        label="Tipo de trajeto",
        choices=AcidenteTrabalho.TRAJETO_EVENTO_CHOICES,
        widget=forms.RadioSelect(attrs={"class": "form-check-input"}),
        required=False,
    )
    houve_afastamento = forms.TypedChoiceField(
        label="Afastamento",
        choices=[("1", "Houve afastamento"), ("0", "Nao houve afastamento")],
        widget=forms.RadioSelect(attrs={"class": "form-check-input"}),
        coerce=lambda value: str(value) == "1",
        initial="0",
    )
    ambiente = forms.ChoiceField(choices=[("", "Selecione")])
    cidade = forms.ChoiceField(choices=[("", "Selecione")])

    class Meta:
        model = AcidenteTrabalho
        fields = [
            "tipo_registro",
            "tipo_acidente",
            "trajeto_evento",
            "situacao_geradora",
            "agente_causador",
            "parte_atingida",
            "lateralidade",
            "severidade_real",
            "severidade_potencial",
            "funcionario",
            "ultimo_dia_trabalhado",
            "horas_trabalhadas",
            "houve_afastamento",
            "houve_obito",
            "data_obito",
            "houve_comunicacao_policia",
            "data_ocorrencia",
            "descricao_ocorrido",
            "observacao",
            "tipo_local",
            "ambiente",
            "descricao_local",
            "cep",
            "estado",
            "cidade",
            "tipo_logradouro",
            "endereco",
            "numero",
            "complemento",
            "bairro",
            "existe_atestado",
            "data_atendimento",
            "houve_internacao",
            "duracao_tratamento_dias",
            "indicado_afastamento",
            "natureza_lesao",
            "diagnostico_provavel",
            "codigo_cid10",
            "observacao_atestado",
            "emitente",
            "codigo_cnes",
            "analise_data_conclusao",
            "analise_preenchido_por",
            "analise_coordenador",
            "analise_envolvidos",
            "analise_participantes",
        ]
        widgets = {
            "data_ocorrencia": forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"),
            "ultimo_dia_trabalhado": forms.DateInput(attrs={"type": "date"}),
            "data_obito": forms.DateInput(attrs={"type": "date"}),
            "descricao_local": forms.Textarea(attrs={"rows": 2, "maxlength": "80"}),
            "data_atendimento": forms.DateInput(attrs={"type": "date"}),
            "analise_data_conclusao": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, tenant=None, planta_id=None, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        User = get_user_model()
        funcionarios = Funcionario.objects.all()
        agentes = AgenteCausador.objects.none()
        partes = ParteAtingida.objects.none()
        naturezas = NaturezaLesao.objects.none()
        emitentes = EmitenteAtestado.objects.none()
        if tenant is not None:
            funcionarios = funcionarios.filter(company=tenant, ativo=True)
            agentes = AgenteCausador.objects.filter(company=tenant, ativo=True)
            partes = ParteAtingida.objects.filter(company=tenant, ativo=True)
            naturezas = NaturezaLesao.objects.filter(company=tenant, ativo=True)
            emitentes = EmitenteAtestado.objects.filter(company=tenant, ativo=True)
        if planta_id:
            funcionarios = funcionarios.filter(planta_id=planta_id)
        self.fields["funcionario"].queryset = funcionarios.order_by("nome")
        if "agente_causador" in self.fields:
            self.fields["agente_causador"].queryset = agentes.order_by("nome")
            self.fields["agente_causador"].empty_label = "Selecione"
        if "parte_atingida" in self.fields:
            self.fields["parte_atingida"].queryset = partes.order_by("nome")
            self.fields["parte_atingida"].empty_label = "Selecione"
        if "natureza_lesao" in self.fields:
            self.fields["natureza_lesao"].queryset = naturezas.order_by("nome")
            self.fields["natureza_lesao"].empty_label = "Selecione"
        if "emitente" in self.fields:
            self.fields["emitente"].queryset = emitentes.order_by("nome")
            self.fields["emitente"].empty_label = "Selecione"
        if "analise_coordenador" in self.fields:
            self.fields["analise_coordenador"].queryset = funcionarios.order_by("nome")
            self.fields["analise_coordenador"].empty_label = "Selecione"
        if "analise_envolvidos" in self.fields:
            self.fields["analise_envolvidos"].queryset = funcionarios.order_by("nome")
        if "analise_participantes" in self.fields:
            self.fields["analise_participantes"].queryset = funcionarios.order_by("nome")
        if "analise_preenchido_por" in self.fields:
            current_user = getattr(self.instance, "analise_preenchido_por", None)
            if current_user:
                self.fields["analise_preenchido_por"].queryset = User.objects.filter(pk=current_user.pk)
            elif user is not None:
                self.fields["analise_preenchido_por"].queryset = User.objects.filter(pk=user.pk)
                self.fields["analise_preenchido_por"].initial = user
            else:
                self.fields["analise_preenchido_por"].queryset = User.objects.none()
            self.fields["analise_preenchido_por"].disabled = True
            self.fields["analise_preenchido_por"].required = False

        self.fields["tipo_local"].widget.attrs["data-acidente-tipo-local"] = "1"
        self.fields["estado"].widget.attrs["data-acidente-estado"] = "1"
        self.fields["ambiente"].widget.attrs["data-acidente-ambiente"] = "1"
        self.fields["cidade"].widget.attrs["data-acidente-cidade"] = "1"
        self.fields["tipo_acidente"].widget.attrs["data-acidente-tipo-acidente"] = "1"
        self.fields["trajeto_evento"].widget.attrs["data-acidente-trajeto-evento"] = "1"
        self.fields["houve_obito"].widget.attrs["data-acidente-houve-obito"] = "1"
        self.fields["data_obito"].widget.attrs["data-acidente-data-obito"] = "1"
        self.fields["existe_atestado"].widget.attrs["data-acidente-existe-atestado"] = "1"
        self.fields["data_atendimento"].widget.attrs["data-acidente-data-atendimento"] = "1"
        self.fields["houve_internacao"].widget.attrs["data-acidente-houve-internacao"] = "1"
        self.fields["duracao_tratamento_dias"].widget.attrs["data-acidente-duracao-tratamento"] = "1"
        self.fields["indicado_afastamento"].widget.attrs["data-acidente-indicado-afastamento"] = "1"
        self.fields["natureza_lesao"].widget.attrs["data-acidente-natureza-lesao"] = "1"
        self.fields["diagnostico_provavel"].widget.attrs["data-acidente-diagnostico-provavel"] = "1"
        self.fields["codigo_cid10"].widget.attrs["data-acidente-cid10"] = "1"
        self.fields["observacao_atestado"].widget.attrs["data-acidente-observacao-atestado"] = "1"
        self.fields["emitente"].widget.attrs["data-acidente-emitente"] = "1"
        self.fields["codigo_cnes"].widget.attrs["data-acidente-cnes"] = "1"

        self.fields["duracao_tratamento_dias"].widget.attrs.update({"min": "0", "step": "1"})

        self.fields["horas_trabalhadas"].widget.attrs.update({"min": "0", "step": "0.25"})

        for field_name in (
            "situacao_geradora",
            "agente_causador",
            "parte_atingida",
            "funcionario",
            "estado",
            "cidade",
            "tipo_logradouro",
            "analise_coordenador",
            "analise_envolvidos",
            "analise_participantes",
        ):
            field = self.fields.get(field_name)
            if field:
                field.widget.attrs["data-choices"] = "1"

        for field_name in ("tipo_registro", "tipo_acidente", "trajeto_evento", "houve_afastamento"):
            field = self.fields.get(field_name)
            if not field:
                continue
            widget = field.widget
            current = (widget.attrs.get("class") or "").split()
            widget.attrs["class"] = " ".join([cls for cls in current if cls != "form-control"])

        self.fields["cep"].required = False
        self.fields["endereco"].required = False
        self.fields["numero"].required = False
        self.fields["bairro"].required = False
        self.fields["cep"].widget.attrs.update(
            {
                "placeholder": "00000-000",
                "inputmode": "numeric",
                "autocomplete": "postal-code",
                "data-acidente-cep": "1",
            }
        )
        if "data_ocorrencia" in self.fields:
            self.fields["data_ocorrencia"].input_formats = ["%Y-%m-%dT%H:%M"]

        if self.instance and getattr(self.instance, "ambiente", ""):
            current = self.instance.ambiente
            if current and current not in {value for value, _ in self.fields["ambiente"].choices}:
                self.fields["ambiente"].choices = [("", "Selecione"), (current, current)]

        if self.instance and getattr(self.instance, "cidade", ""):
            current = self.instance.cidade
            if current and current not in {value for value, _ in self.fields["cidade"].choices}:
                self.fields["cidade"].choices = [("", "Selecione"), (current, current)]
        if self.is_bound:
            cidade_value = self.data.get(self.add_prefix("cidade"))
            if cidade_value and cidade_value not in {value for value, _ in self.fields["cidade"].choices}:
                self.fields["cidade"].choices = [("", "Selecione"), (cidade_value, cidade_value)]
            ambiente_value = self.data.get(self.add_prefix("ambiente"))
            if ambiente_value and ambiente_value not in {value for value, _ in self.fields["ambiente"].choices}:
                self.fields["ambiente"].choices = [("", "Selecione"), (ambiente_value, ambiente_value)]

    def clean(self):
        cleaned = super().clean()
        tipo_acidente = cleaned.get("tipo_acidente")
        trajeto_evento = cleaned.get("trajeto_evento")
        if tipo_acidente == "trajeto" and not trajeto_evento:
            self.add_error("trajeto_evento", "Selecione o tipo de trajeto.")
        if tipo_acidente != "trajeto":
            cleaned["trajeto_evento"] = ""

        houve_obito = cleaned.get("houve_obito")
        data_obito = cleaned.get("data_obito")
        if houve_obito and not data_obito:
            self.add_error("data_obito", "Informe a data de obito.")
        if not houve_obito:
            cleaned["data_obito"] = None

        horas_trabalhadas = cleaned.get("horas_trabalhadas")
        if horas_trabalhadas is not None and horas_trabalhadas < 0:
            self.add_error("horas_trabalhadas", "Horas trabalhadas deve ser maior ou igual a zero.")

        existe_atestado = cleaned.get("existe_atestado")
        if existe_atestado:
            if not cleaned.get("data_atendimento"):
                self.add_error("data_atendimento", "Informe a data do atendimento.")
            if cleaned.get("duracao_tratamento_dias") in (None, ""):
                self.add_error("duracao_tratamento_dias", "Informe a duracao do tratamento (dias).")
            if not (cleaned.get("codigo_cid10") or "").strip():
                self.add_error("codigo_cid10", "Informe o codigo CID-10.")
        else:
            cleaned["data_atendimento"] = None
            cleaned["houve_internacao"] = False
            cleaned["duracao_tratamento_dias"] = None
            cleaned["indicado_afastamento"] = False
            cleaned["natureza_lesao"] = None
            cleaned["diagnostico_provavel"] = ""
            cleaned["codigo_cid10"] = ""
            cleaned["observacao_atestado"] = ""
            cleaned["emitente"] = None
            cleaned["codigo_cnes"] = ""
        return cleaned


class AcidenteFatoForm(BootstrapModelForm):
    class Meta:
        model = AcidenteFato
        fields = ["hora_ocorrencia", "detalhamento"]
        widgets = {"hora_ocorrencia": forms.TimeInput(attrs={"type": "time"})}


class AcidenteAnexoForm(BootstrapModelForm):
    class Meta:
        model = AcidenteAnexo
        fields = ["arquivo", "descricao"]


AcidenteFatoFormSet = inlineformset_factory(
    AcidenteTrabalho,
    AcidenteFato,
    form=AcidenteFatoForm,
    extra=1,
    can_delete=True,
)

AcidenteAnexoFormSet = inlineformset_factory(
    AcidenteTrabalho,
    AcidenteAnexo,
    form=AcidenteAnexoForm,
    extra=1,
    can_delete=True,
)
