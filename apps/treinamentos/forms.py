from datetime import date

from django import forms

from apps.core.forms import BootstrapModelForm
from apps.funcionarios.models import Funcionario
from apps.produtos.models import Produto
from apps.setores.models import Setor
from apps.tipos_funcionario.models import TipoFuncionario
from .models import DocumentoTemplate, Treinamento, Turma, TurmaAula


class TreinamentoForm(BootstrapModelForm):
    class Meta:
        model = Treinamento
        fields = [
            "nome",
            "tipo",
            "validade_dias",
            "carga_horaria",
            "obrigatorio",
            "ativo",
            "requisitos_cargos",
            "requisitos_setores",
            "requisitos_tipos_funcionario",
            "requisitos_epis",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        requisitos_epis = self.fields.get("requisitos_epis")
        if requisitos_epis:
            requisitos_epis.queryset = Produto.objects.filter(controle_epi=True, ativo=True)


class TurmaForm(BootstrapModelForm):
    participantes_setores = forms.ModelMultipleChoiceField(
        queryset=Setor.objects.none(),
        required=False,
        label="Setores participantes",
    )
    participantes_tipos_funcionario = forms.ModelMultipleChoiceField(
        queryset=TipoFuncionario.objects.none(),
        required=False,
        label="Tipos de funcionario participantes",
    )
    aulas_datas = forms.CharField(
        required=False,
        label="Datas das aulas",
        widget=forms.Textarea(attrs={"rows": 3, "placeholder": "Uma data por linha (YYYY-MM-DD)"}),
    )

    class Meta:
        model = Turma
        fields = [
            "treinamento",
            "qtd_aulas",
            "local",
            "instrutor",
            "capacidade",
            "participantes",
            "aulas_datas",
            "finalizada",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        company = getattr(self.instance, "company", None)
        qtd_aulas = self.fields.get("qtd_aulas")
        if qtd_aulas:
            qtd_aulas.widget.attrs.setdefault("min", "1")
        aulas_datas = self.fields.get("aulas_datas")
        if aulas_datas:
            aulas_datas.widget.attrs.setdefault("data-aulas-datas", "1")
        if company:
            self.fields["participantes_setores"].queryset = Setor.objects.filter(company=company, ativo=True)
            self.fields["participantes_tipos_funcionario"].queryset = TipoFuncionario.objects.filter(
                company=company, ativo=True
            )
        else:
            self.fields["participantes_setores"].queryset = Setor.objects.filter(ativo=True)
            self.fields["participantes_tipos_funcionario"].queryset = TipoFuncionario.objects.filter(ativo=True)
        if self.instance and self.instance.pk:
            datas = list(self.instance.aulas.values_list("data", flat=True).order_by("data"))
            if datas:
                self.fields["aulas_datas"].initial = "\n".join([d.isoformat() for d in datas])
        if self.instance and self.instance.pk and self.instance.finalizada:
            for name, field in self.fields.items():
                if name == "finalizada":
                    field.disabled = True
                    continue
                field.disabled = True

    def clean_aulas_datas(self):
        raw = (self.cleaned_data.get("aulas_datas") or "").strip()
        if not raw:
            return []
        datas = []
        for line in raw.splitlines():
            value = line.strip()
            if not value:
                continue
            try:
                datas.append(date.fromisoformat(value))
            except ValueError as exc:
                raise forms.ValidationError("Datas invalidas. Use o formato YYYY-MM-DD.") from exc
        return datas

    def clean(self):
        cleaned = super().clean()
        datas = cleaned.get("aulas_datas") or []
        qtd_aulas = cleaned.get("qtd_aulas")
        if datas and qtd_aulas and len(datas) != qtd_aulas:
            self.add_error("aulas_datas", "Quantidade de datas deve ser igual ao numero de aulas.")
        return cleaned

    def save(self, commit=True):
        instance = super().save(commit=commit)
        setores = self.cleaned_data.get("participantes_setores")
        tipos = self.cleaned_data.get("participantes_tipos_funcionario")
        if commit and (setores or tipos):
            funcionarios = Funcionario.objects.filter(company=instance.company, ativo=True)
            if setores:
                funcionarios = funcionarios.filter(setor__in=setores)
            if tipos:
                funcionarios = funcionarios.filter(tipo__in=tipos)
            if funcionarios.exists():
                instance.participantes.add(*funcionarios)
        if commit:
            datas = self.cleaned_data.get("aulas_datas") or []
            TurmaAula.objects.filter(turma=instance).delete()
            for data in datas:
                TurmaAula.objects.create(company=instance.company, turma=instance, data=data)
        return instance


class DocumentoTemplateForm(BootstrapModelForm):
    class Meta:
        model = DocumentoTemplate
        fields = ["titulo", "tipo", "ativo", "logo", "corpo_html"]
        widgets = {
            "corpo_html": forms.Textarea(
                attrs={
                    "rows": 12,
                }
            )
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance or not self.instance.pk:
            self.fields["corpo_html"].initial = (
                '<div class="title" data-lock="1"><span data-editable="1">Certificado de Treinamento</span></div>\n'
                '<div class="subtitle" data-lock="1"><span data-editable="1">{{ empresa.name }}</span></div>\n'
                '<div class="content content-center" data-lock="1">\n'
                '  <span data-editable="1">Certificamos que </span>'
                '<span class="highlight" data-editable="1">{{ funcionario.nome }}</span>'
                '<span data-editable="1"> participou e foi aprovado no treinamento </span>'
                '<span class="highlight" data-editable="1">{{ treinamento.nome }}</span>'
                '<span data-editable="1">.</span>\n'
                '</div>\n'
                '<div class="content content-center" style="margin-top: 16px;" data-lock="1">\n'
                '  <span data-editable="1">Instrutor: </span>'
                '<span class="highlight" data-editable="1">{{ instrutor }}</span><br>\n'
                '  <span data-editable="1">Datas: </span>'
                '<span class="highlight" data-editable="1">{{ datas_aulas }}</span><br>\n'
                '  <span data-editable="1">Emissao: </span>'
                '<span class="highlight" data-editable="1">{{ data_emissao }}</span>\n'
                '</div>\n'
            )
        corpo_html = self.fields.get("corpo_html")
        if corpo_html:
            corpo_html.help_text = (
                "Edite apenas o texto. As classes padrao serao preservadas automaticamente."
            )
