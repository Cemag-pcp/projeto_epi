from decimal import Decimal, InvalidOperation
from datetime import date
import calendar

from django.contrib.auth.mixins import PermissionRequiredMixin
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils import timezone
import re
from django.views import View
from django.db.models import Count
from django.template import Context, Template
from django.template import Context, Template
from django.template.loader import render_to_string

from apps.core.views import BaseTenantCreateView, BaseTenantListView, BaseTenantUpdateView
from apps.funcionarios.models import Funcionario
from .forms import DocumentoTemplateForm, TreinamentoForm, TurmaForm
from .models import (
    DocumentoTemplate,
    Treinamento,
    TreinamentoCertificado,
    TreinamentoPendencia,
    TreinamentoParticipacao,
    TreinamentoPresencaAula,
    Turma,
    TurmaAula,
)

def _ensure_participacoes(request, turma):
    participantes_ids = list(
        turma.participantes.filter(ativo=True).values_list("id", flat=True)
    )
    if not participantes_ids:
        return
    existentes = set(
        TreinamentoParticipacao.objects.filter(
            turma=turma,
            funcionario_id__in=participantes_ids,
        ).values_list("funcionario_id", flat=True)
    )
    faltantes = [func_id for func_id in participantes_ids if func_id not in existentes]
    if not faltantes:
        return
    presencas = (
        TreinamentoPresencaAula.objects.filter(
            turma_aula__turma=turma,
            funcionario_id__in=faltantes,
            presente=True,
        )
        .values("funcionario_id")
        .annotate(total=Count("id"))
    )
    presencas_map = {item["funcionario_id"]: item["total"] for item in presencas}
    novos = []
    for funcionario_id in faltantes:
        aulas_presentes = presencas_map.get(funcionario_id, 0)
        novos.append(
            TreinamentoParticipacao(
                company=request.tenant,
                turma=turma,
                funcionario_id=funcionario_id,
                presente=aulas_presentes > 0,
                aulas_presentes=aulas_presentes,
                created_by=request.user,
                updated_by=request.user,
            )
        )
    if novos:
        TreinamentoParticipacao.objects.bulk_create(novos, ignore_conflicts=True)


class TreinamentoAgendaView(PermissionRequiredMixin, View):
    permission_required = "treinamentos.view_turma"
    template_name = "treinamentos/agenda.html"

    def get(self, request):
        today = timezone.localdate()
        try:
            year = int(request.GET.get("ano", today.year))
            month = int(request.GET.get("mes", today.month))
        except (TypeError, ValueError):
            year = today.year
            month = today.month
        if month < 1 or month > 12:
            month = today.month
        month_start = date(year, month, 1)
        calendar_it = calendar.Calendar(firstweekday=6)
        weeks = calendar_it.monthdatescalendar(year, month)
        range_start = weeks[0][0]
        range_end = weeks[-1][-1]

        aulas = (
            TurmaAula.objects.filter(
                company=request.tenant,
                turma__finalizada=False,
                data__range=(range_start, range_end),
            )
            .select_related("turma__treinamento", "turma__instrutor")
            .order_by("data")
        )
        events_by_date = {}
        for aula in aulas:
            events_by_date.setdefault(aula.data, []).append(
                {
                    "turma_id": aula.turma_id,
                    "treinamento": aula.turma.treinamento.nome,
                    "local": aula.turma.local,
                    "instrutor": aula.turma.instrutor.nome if aula.turma.instrutor else "",
                }
            )

        turmas = (
            Turma.objects.filter(company=request.tenant, finalizada=False)
            .select_related("treinamento", "instrutor")
            .prefetch_related("aulas")
        )
        open_turmas = []
        for turma in turmas:
            aulas_list = list(turma.aulas.all())
            next_date = min((aula.data for aula in aulas_list), default=None)
            open_turmas.append(
                {
                    "id": turma.pk,
                    "treinamento": turma.treinamento.nome,
                    "local": turma.local,
                    "instrutor": turma.instrutor.nome if turma.instrutor else "",
                    "next_date": next_date,
                }
            )
        open_turmas.sort(
            key=lambda item: (item["next_date"] is None, item["next_date"] or date.max)
        )

        prev_year = year
        prev_month = month - 1
        if prev_month < 1:
            prev_month = 12
            prev_year = year - 1
        next_year = year
        next_month = month + 1
        if next_month > 12:
            next_month = 1
            next_year = year + 1

        month_names = [
            "Janeiro",
            "Fevereiro",
            "Marco",
            "Abril",
            "Maio",
            "Junho",
            "Julho",
            "Agosto",
            "Setembro",
            "Outubro",
            "Novembro",
            "Dezembro",
        ]
        context = {
            "title": "Agenda",
            "month_label": f"{month_names[month - 1]} {year}",
            "weeks": weeks,
            "events_by_date": events_by_date,
            "open_turmas": open_turmas,
            "today": today,
            "month": month,
            "year": year,
            "prev_month": prev_month,
            "prev_year": prev_year,
            "next_month": next_month,
            "next_year": next_year,
        }
        return render(request, self.template_name, context)

class TreinamentoListView(BaseTenantListView):
    model = Treinamento
    form_class = TreinamentoForm
    template_name = "treinamentos/treinamentos_list.html"
    title = "Treinamentos"
    subtitle = "Cadastre e gerencie treinamentos obrigatorios e validos."
    headers = ["Nome", "Tipo", "Validade (dias)", "Carga horaria", "Obrigatorio", "Ativo"]
    row_fields = ["nome", "tipo_label", "validade_dias", "carga_horaria_label", "obrigatorio", "ativo"]
    filter_definitions = [
        {"name": "nome", "label": "Nome", "lookup": "icontains", "type": "text"},
        {
            "name": "tipo",
            "label": "Tipo",
            "lookup": "exact",
            "type": "select",
            "options": [("", "Todos")] + list(Treinamento.TIPO_CHOICES),
        },
        {
            "name": "obrigatorio",
            "label": "Obrigatorio",
            "lookup": "exact_bool",
            "type": "select",
            "options": [("", "Todos"), ("1", "Sim"), ("0", "Nao")],
        },
        {
            "name": "ativo",
            "label": "Ativo",
            "lookup": "exact_bool",
            "type": "select",
            "options": [("", "Todos"), ("1", "Ativo"), ("0", "Inativo")],
        },
    ]
    create_url_name = "treinamentos:create"
    update_url_name = "treinamentos:update"


class TreinamentoCreateView(BaseTenantCreateView):
    model = Treinamento
    form_class = TreinamentoForm
    success_url_name = "treinamentos:list"


class TreinamentoUpdateView(BaseTenantUpdateView):
    model = Treinamento
    form_class = TreinamentoForm
    success_url_name = "treinamentos:list"


class TreinamentoToggleActiveView(PermissionRequiredMixin, View):
    permission_required = "treinamentos.change_treinamento"

    def post(self, request, pk):
        treinamento = Treinamento.objects.filter(pk=pk, company=request.tenant).first()
        if not treinamento:
            return JsonResponse({"ok": False}, status=404)
        treinamento.ativo = not treinamento.ativo
        treinamento.updated_by = request.user
        treinamento.save(update_fields=["ativo", "updated_by"])
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            row_html = render_to_string(
                "treinamentos/_treinamento_row.html",
                {"treinamento": treinamento},
                request=request,
            )
            return JsonResponse({"ok": True, "row_id": treinamento.pk, "row_html": row_html})
        return HttpResponseRedirect(reverse("treinamentos:list"))


class DocumentoTemplateListView(BaseTenantListView):
    model = DocumentoTemplate
    form_class = DocumentoTemplateForm
    template_name = "treinamentos/documentos_list.html"
    title = "Configuracao de documentos"
    subtitle = "Gerencie layouts de certificados e outros documentos."
    headers = ["Titulo", "Tipo", "Ativo", "Atualizado em"]
    row_fields = ["titulo", "tipo", "ativo", "updated_at"]
    create_url_name = "treinamentos:documentos_create"
    update_url_name = "treinamentos:documentos_update"


class DocumentoTemplateCreateView(BaseTenantCreateView):
    model = DocumentoTemplate
    form_class = DocumentoTemplateForm
    success_url_name = "treinamentos:documentos_list"

    def form_valid(self, form):
        tipo = form.cleaned_data.get("tipo")
        ativo = form.cleaned_data.get("ativo")
        if ativo and DocumentoTemplate.objects.filter(
            company=self.request.tenant,
            tipo=tipo,
            ativo=True,
        ).exists():
            form.add_error("tipo", "Ja existe um documento ativo para este tipo.")
            return self.form_invalid(form)
        return super().form_valid(form)


class DocumentoTemplateUpdateView(BaseTenantUpdateView):
    model = DocumentoTemplate
    form_class = DocumentoTemplateForm
    success_url_name = "treinamentos:documentos_list"

    def form_valid(self, form):
        tipo = form.cleaned_data.get("tipo")
        ativo = form.cleaned_data.get("ativo")
        if ativo and DocumentoTemplate.objects.filter(
            company=self.request.tenant,
            tipo=tipo,
            ativo=True,
        ).exclude(pk=self.get_object().pk).exists():
            form.add_error("tipo", "Ja existe um documento ativo para este tipo.")
            return self.form_invalid(form)
        return super().form_valid(form)


class DocumentoTemplateDeleteView(PermissionRequiredMixin, View):
    permission_required = "treinamentos.delete_documentotemplate"

    def post(self, request, pk):
        documento = DocumentoTemplate.objects.filter(pk=pk, company=request.tenant).first()
        if not documento:
            return HttpResponseRedirect(reverse("treinamentos:documentos_list"))
        documento.delete()
        return HttpResponseRedirect(reverse("treinamentos:documentos_list"))


class TurmaListView(BaseTenantListView):
    model = Turma
    form_class = TurmaForm
    template_name = "treinamentos/turmas_list.html"
    title = "Turmas"
    subtitle = "Agende turmas e gerencie participantes."
    headers = ["Treinamento", "Local", "Instrutor", "Capacidade", "Participantes"]
    row_fields = [
        "treinamento",
        "local",
        "instrutor",
        "capacidade_label",
        "participantes_count",
    ]
    filter_definitions = [
        {"name": "treinamento__nome", "label": "Treinamento", "lookup": "icontains", "type": "text"},
        {"name": "instrutor__nome", "label": "Instrutor", "lookup": "icontains", "type": "text"},
    ]
    create_url_name = "treinamentos:turmas_create"
    update_url_name = "treinamentos:turmas_update"


class TurmaCreateView(BaseTenantCreateView):
    model = Turma
    form_class = TurmaForm
    success_url_name = "treinamentos:turmas_list"


class TurmaUpdateView(BaseTenantUpdateView):
    model = Turma
    form_class = TurmaForm
    success_url_name = "treinamentos:turmas_list"

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        if self.object.finalizada:
            return HttpResponseRedirect(self.get_success_url())
        return super().post(request, *args, **kwargs)


class TurmaFinalizarView(PermissionRequiredMixin, View):
    permission_required = "treinamentos.change_turma"

    def post(self, request, pk):
        turma = get_object_or_404(Turma, pk=pk, company=request.tenant)
        if not turma.finalizada:
            _ensure_participacoes(request, turma)
            turma.finalizada = True
            turma.updated_by = request.user
            turma.save(update_fields=["finalizada", "updated_by", "updated_at"])
            data_emissao = timezone.localdate()
            validade_ate = None
            validade_dias = turma.treinamento.validade_dias or 0
            if validade_dias > 0:
                validade_ate = data_emissao + timezone.timedelta(days=validade_dias)
            participacoes = TreinamentoParticipacao.objects.filter(turma=turma).select_related("funcionario")
            for item in participacoes:
                pendencia = TreinamentoPendencia.objects.filter(
                    funcionario=item.funcionario,
                    treinamento=turma.treinamento,
                    company=request.tenant,
                ).first()
                if pendencia:
                    if item.resultado == "aprovado":
                        pendencia.status = "aprovado"
                    elif item.resultado == "reprovado":
                        pendencia.status = "reprovado"
                    elif item.presente:
                        pendencia.status = "realizado"
                    else:
                        pendencia.status = "pendente"
                    pendencia.updated_by = request.user
                    pendencia.save(update_fields=["status", "updated_by", "updated_at"])
                if item.resultado == "aprovado":
                    TreinamentoCertificado.objects.update_or_create(
                        funcionario=item.funcionario,
                        treinamento=turma.treinamento,
                        defaults={
                            "company": request.tenant,
                            "turma": turma,
                            "data_emissao": data_emissao,
                            "validade_ate": validade_ate,
                            "updated_by": request.user,
                        },
                    )
        return HttpResponseRedirect(reverse("treinamentos:turmas_list"))

class TurmaPresencaView(PermissionRequiredMixin, View):
    permission_required = "treinamentos.change_turma"

    def get(self, request, pk):
        turma = get_object_or_404(Turma, pk=pk, company=request.tenant)
        _ensure_participacoes(request, turma)
        aulas = TurmaAula.objects.filter(turma=turma).order_by("data")
        participacoes_qs = (
            TreinamentoParticipacao.objects.filter(turma=turma)
            .select_related("funcionario")
            .order_by("funcionario__nome")
        )
        presencas = TreinamentoPresencaAula.objects.filter(turma_aula__turma=turma).values(
            "funcionario_id",
            "turma_aula_id",
            "presente",
        )
        presenca_map = {
            (item["funcionario_id"], item["turma_aula_id"]): bool(item["presente"])
            for item in presencas
        }
        participacoes = []
        for item in participacoes_qs:
            presencas_aulas = []
            for aula in aulas:
                presencas_aulas.append(
                    {"aula": aula, "presente": presenca_map.get((item.funcionario_id, aula.id), False)}
                )
            participacoes.append({"participacao": item, "presencas": presencas_aulas})
        context = {
            "turma": turma,
            "participacoes": participacoes,
            "aulas": aulas,
        }
        return render(request, "treinamentos/turma_presenca.html", context)

    def post(self, request, pk):
        turma = get_object_or_404(Turma, pk=pk, company=request.tenant)
        if turma.finalizada:
            return HttpResponseRedirect(reverse("treinamentos:turmas_presenca", args=[turma.pk]))
        aulas = list(TurmaAula.objects.filter(turma=turma).order_by("data"))
        participantes_ids = request.POST.getlist("participante_id")
        for raw_id in participantes_ids:
            try:
                funcionario_id = int(raw_id)
            except (TypeError, ValueError):
                continue
            aulas_presentes = 0
            for aula in aulas:
                checked = request.POST.get(f"presenca_{funcionario_id}_{aula.id}") == "1"
                if checked:
                    aulas_presentes += 1
                TreinamentoPresencaAula.objects.update_or_create(
                    turma_aula=aula,
                    funcionario_id=funcionario_id,
                    defaults={
                        "company": request.tenant,
                        "presente": checked,
                        "updated_by": request.user,
                    },
                )
            presente = aulas_presentes > 0
            TreinamentoParticipacao.objects.update_or_create(
                turma=turma,
                funcionario_id=funcionario_id,
                defaults={
                    "company": request.tenant,
                    "presente": presente,
                    "aulas_presentes": aulas_presentes,
                    "updated_by": request.user,
                },
            )
        return HttpResponseRedirect(reverse("treinamentos:turmas_presenca", args=[turma.pk]))


class TurmaAvaliacaoView(PermissionRequiredMixin, View):
    permission_required = "treinamentos.change_turma"

    def get(self, request, pk):
        turma = get_object_or_404(Turma, pk=pk, company=request.tenant)
        _ensure_participacoes(request, turma)
        participacoes = (
            TreinamentoParticipacao.objects.filter(turma=turma)
            .select_related("funcionario")
            .order_by("funcionario__nome")
        )
        aulas = TurmaAula.objects.filter(turma=turma).order_by("data")
        context = {
            "turma": turma,
            "participacoes": participacoes,
            "aulas": aulas,
        }
        return render(request, "treinamentos/turma_avaliacao.html", context)

    def post(self, request, pk):
        turma = get_object_or_404(Turma, pk=pk, company=request.tenant)
        if turma.finalizada:
            return HttpResponseRedirect(reverse("treinamentos:turmas_avaliacao", args=[turma.pk]))
        participantes_ids = request.POST.getlist("participante_id")
        for raw_id in participantes_ids:
            try:
                funcionario_id = int(raw_id)
            except (TypeError, ValueError):
                continue
            resultado = request.POST.get(f"resultado_{funcionario_id}") or ""
            nota_raw = request.POST.get(f"nota_{funcionario_id}")
            avaliacao = request.POST.get(f"avaliacao_{funcionario_id}") or ""

            participacao = TreinamentoParticipacao.objects.filter(
                turma=turma,
                funcionario_id=funcionario_id,
            ).first()
            aulas_presentes = participacao.aulas_presentes if participacao else 0
            presente = aulas_presentes > 0

            nota = None
            if nota_raw:
                try:
                    nota = Decimal(nota_raw)
                except (InvalidOperation, ValueError):
                    nota = None
            if not presente:
                resultado = "ausente"
                nota = None
            else:
                if not resultado:
                    continue

            TreinamentoParticipacao.objects.update_or_create(
                turma=turma,
                funcionario_id=funcionario_id,
                defaults={
                    "company": request.tenant,
                    "presente": presente,
                    "resultado": resultado,
                    "nota": nota,
                    "avaliacao": avaliacao,
                    "updated_by": request.user,
                },
            )

            pendencia = TreinamentoPendencia.objects.filter(
                funcionario_id=funcionario_id,
                treinamento=turma.treinamento,
                company=request.tenant,
            ).first()
            if pendencia:
                if presente:
                    if resultado == "aprovado":
                        pendencia.status = "aprovado"
                    elif resultado == "reprovado":
                        pendencia.status = "reprovado"
                    else:
                        pendencia.status = "realizado"
                else:
                    pendencia.status = "pendente"
                pendencia.updated_by = request.user
                pendencia.save(update_fields=["status", "updated_by", "updated_at"])
            if presente and resultado == "aprovado":
                data_emissao = timezone.localdate()
                validade_ate = None
                validade_dias = turma.treinamento.validade_dias or 0
                if validade_dias > 0:
                    validade_ate = data_emissao + timezone.timedelta(days=validade_dias)
                TreinamentoCertificado.objects.update_or_create(
                    funcionario_id=funcionario_id,
                    treinamento=turma.treinamento,
                    defaults={
                        "company": request.tenant,
                        "turma": turma,
                        "data_emissao": data_emissao,
                        "validade_ate": validade_ate,
                        "updated_by": request.user,
                    },
                )

        return HttpResponseRedirect(reverse("treinamentos:turmas_avaliacao", args=[turma.pk]))


class CertificadoPrintView(PermissionRequiredMixin, View):
    permission_required = "treinamentos.view_treinamentocertificado"

    def get(self, request, pk):
        certificado = get_object_or_404(
            TreinamentoCertificado,
            pk=pk,
            company=request.tenant,
        )
        turma = certificado.turma
        instrutor = ""
        datas_aulas = ""
        if turma:
            if turma.instrutor:
                instrutor = turma.instrutor.nome
            datas = list(TurmaAula.objects.filter(turma=turma).values_list("data", flat=True).order_by("data"))
            datas_aulas = ", ".join([d.strftime("%d/%m/%Y") for d in datas])
        documento = (
            DocumentoTemplate.objects.filter(
                company=request.tenant,
                tipo="certificado",
                ativo=True,
            )
            .order_by("-updated_at")
            .first()
        ) or (
            DocumentoTemplate.objects.filter(
                company=request.tenant,
                tipo="certificado",
            )
            .order_by("-updated_at")
            .first()
        )
        logo_url = documento.logo.url if documento and documento.logo else ""
        context = {
            "certificado": certificado,
            "funcionario": certificado.funcionario,
            "treinamento": certificado.treinamento,
            "turma": turma,
            "empresa": request.tenant,
            "data_emissao": certificado.data_emissao,
            "validade_ate": certificado.validade_ate,
            "instrutor": instrutor,
            "datas_aulas": datas_aulas,
            "logo_url": logo_url,
        }
        corpo_html = ""
        if documento and documento.corpo_html:
            corpo_html = documento.corpo_html
            corpo_html = re.sub(r'\scontenteditable="(?:true|false)"', "", corpo_html)
            corpo_html = re.sub(r'\sdata-editable="1"', "", corpo_html)
            corpo_html = re.sub(r'\sdata-lock="1"', "", corpo_html)
            try:
                corpo_html = Template(corpo_html).render(Context(context))
            except Exception:
                corpo_html = ""
            try:
                corpo_html = Template(corpo_html).render(Context(context))
            except Exception:
                corpo_html = ""
        context["corpo_html"] = corpo_html
        context["documento"] = documento
        return render(request, "treinamentos/certificado_print.html", context)
