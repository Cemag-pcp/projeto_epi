import uuid

from django import forms
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Q
from django.http import Http404
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views import View

from apps.core.views import BaseTenantListView

from .forms import (
    CipaCandidaturaPublicaForm,
    CipaEleicaoCandidaturaForm,
    CipaEleicaoDivulgacaoForm,
    CipaEleicaoInicioForm,
    CipaEleicaoProgramacaoForm,
    CipaEleicaoSindicatoForm,
    CipaVotacaoPublicaForm,
    compute_default_dates,
)
from .models import CipaCandidato, CipaEleicao, CipaVoto


WIZARD_STEPS = {
    1: {"title": "Programação", "form": CipaEleicaoProgramacaoForm},
    2: {"title": "Início", "form": CipaEleicaoInicioForm},
    3: {"title": "Comunicação para o Sindicato", "form": CipaEleicaoSindicatoForm},
    4: {"title": "Candidatura", "form": CipaEleicaoCandidaturaForm},
    5: {"title": "Divulgação", "form": CipaEleicaoDivulgacaoForm},
}


class CipaEleicaoListView(BaseTenantListView):
    model = CipaEleicao
    template_name = "cipa/list.html"
    paginate_by = 20
    title = "CIPA"
    subtitle = "Eleições da CIPA."

    def get_queryset(self):
        qs = super().get_queryset().select_related("planta")
        planta_id = self.request.session.get("planta_id")
        if planta_id:
            qs = qs.filter(Q(planta_id=planta_id) | Q(escopo="global"))
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        if self.request.user.has_perm("cipa.add_cipaeleicao"):
            ctx["create_url"] = reverse("cipa:wizard_start")
        return ctx


def _get_eleicao_or_404(request, pk: int) -> CipaEleicao:
    try:
        return CipaEleicao.objects.select_related("planta").get(pk=pk, company=request.tenant)
    except CipaEleicao.DoesNotExist:
        raise Http404


def _compute_result(company, eleicao: CipaEleicao):
    candidatos_qs = (
        CipaCandidato.objects.filter(company=company, eleicao=eleicao, status="aprovado")
        .select_related("funcionario")
        .order_by("numero", "id")
    )
    counts = {
        row["candidato_id"]: row["c"]
        for row in (
            CipaVoto.objects.filter(company=company, eleicao=eleicao, tipo="candidato", candidato__isnull=False)
            .values("candidato_id")
            .annotate(c=Count("id"))
        )
    }

    rows = [{"candidato": cand, "votos": int(counts.get(cand.id, 0))} for cand in candidatos_qs]
    rows.sort(key=lambda r: (-r["votos"], r["candidato"].numero or 999999, r["candidato"].id))

    totals = {
        row["tipo"]: row["c"]
        for row in (
            CipaVoto.objects.filter(company=company, eleicao=eleicao)
            .values("tipo")
            .annotate(c=Count("id"))
        )
    }
    return {
        "rows": rows,
        "total": int(sum(totals.values()) if totals else 0),
        "branco": int(totals.get("branco", 0)),
        "nulo": int(totals.get("nulo", 0)),
        "candidato": int(totals.get("candidato", 0)),
    }


def cipa_wizard_start(request):
    if not request.user.is_authenticated:
        return redirect("login")
    if not request.user.has_perm("cipa.add_cipaeleicao"):
        raise Http404

    planta_id = request.session.get("planta_id")
    eleicao = CipaEleicao.objects.create(
        company=request.tenant,
        created_by=request.user,
        updated_by=request.user,
        nome="",
        escopo="planta" if planta_id else "global",
        planta_id=planta_id if planta_id else None,
        status="rascunho",
        wizard_step=1,
    )
    return redirect("cipa:wizard", pk=eleicao.pk, step=1)


class CipaEleicaoWizardView(LoginRequiredMixin, View):
    def get(self, request, pk: int, step: int):
        if not (request.user.has_perm("cipa.change_cipaeleicao") or request.user.has_perm("cipa.add_cipaeleicao")):
            raise Http404
        eleicao = _get_eleicao_or_404(request, pk)
        step = int(step or 1)
        if step not in WIZARD_STEPS:
            return redirect("cipa:wizard", pk=pk, step=eleicao.wizard_step or 1)

        form = self._build_form(request, eleicao, step)
        return render(
            request,
            "cipa/wizard.html",
            self._context(eleicao=eleicao, step=step, form=form),
        )

    def post(self, request, pk: int, step: int):
        if not (request.user.has_perm("cipa.change_cipaeleicao") or request.user.has_perm("cipa.add_cipaeleicao")):
            raise Http404
        eleicao = _get_eleicao_or_404(request, pk)
        step = int(step or 1)
        if step not in WIZARD_STEPS:
            return redirect("cipa:wizard", pk=pk, step=eleicao.wizard_step or 1)

        if step == 4 and "regenerate_token" in request.POST:
            eleicao.candidatura_publica_token = uuid.uuid4()
            eleicao.updated_by = request.user
            eleicao.save(update_fields=["candidatura_publica_token", "updated_by", "updated_at"])
            messages.success(request, "Link de candidatura atualizado.")
            return redirect("cipa:wizard", pk=pk, step=step)

        if step == 5 and "open_voting" in request.POST:
            eleicao.votacao_publica_ativa = True
            eleicao.status = "votacao"
            eleicao.updated_by = request.user
            eleicao.save(update_fields=["votacao_publica_ativa", "status", "updated_by", "updated_at"])
            messages.success(request, "Votação aberta.")
            return redirect("cipa:wizard", pk=pk, step=step)

        if step == 5 and "close_voting" in request.POST:
            eleicao.votacao_publica_ativa = False
            eleicao.status = "encerrada"
            eleicao.updated_by = request.user
            eleicao.save(update_fields=["votacao_publica_ativa", "status", "updated_by", "updated_at"])
            messages.success(request, "Votação encerrada. Resultado computado abaixo.")
            return redirect("cipa:wizard", pk=pk, step=step)

        if step == 5 and "regenerate_voting_token" in request.POST:
            eleicao.votacao_publica_token = uuid.uuid4()
            eleicao.updated_by = request.user
            eleicao.save(update_fields=["votacao_publica_token", "updated_by", "updated_at"])
            messages.success(request, "Link de votação atualizado.")
            return redirect("cipa:wizard", pk=pk, step=step)

        form = self._build_form(request, eleicao, step, data=request.POST)
        if not form.is_valid():
            return render(request, "cipa/wizard.html", self._context(eleicao=eleicao, step=step, form=form))

        action_close = "save_close" in request.POST
        action_next = "save_next" in request.POST

        if action_next:
            if hasattr(form, "validate_for_next") and not form.validate_for_next():
                return render(request, "cipa/wizard.html", self._context(eleicao=eleicao, step=step, form=form))

        instance = form.save(commit=False)
        instance.company = request.tenant
        if instance.created_by_id is None:
            instance.created_by = request.user
        instance.updated_by = request.user

        if step == 2 and request.POST.get("apply_defaults") == "1":
            defaults = compute_default_dates(instance.data_fim_ultimo_mandato)
            for key, value in defaults.items():
                if getattr(instance, key) in (None, ""):
                    setattr(instance, key, value)

        instance.wizard_step = max(int(instance.wizard_step or 1), step + (1 if action_next else 0), step)
        instance.save()
        form.save_m2m() if hasattr(form, "save_m2m") else None

        if action_close:
            messages.success(request, "Configuração salva.")
            return redirect("cipa:list")

        if action_next:
            if step >= max(WIZARD_STEPS.keys()):
                messages.success(request, "Configuração concluída.")
                return redirect("cipa:list")
            next_step = step + 1
            messages.success(request, "Etapa salva.")
            return redirect("cipa:wizard", pk=pk, step=next_step)

        messages.success(request, "Configuração salva.")
        return redirect("cipa:wizard", pk=pk, step=step)

    def _build_form(self, request, eleicao: CipaEleicao, step: int, data=None):
        form_cls = WIZARD_STEPS[step]["form"]
        form = form_cls(data=data, instance=eleicao)
        if hasattr(form, "request"):
            form.request = request
        else:
            setattr(form, "request", request)
        return form

    def _context(self, *, eleicao: CipaEleicao, step: int, form):
        steps = []
        for num, meta in WIZARD_STEPS.items():
            steps.append(
                {
                    "number": num,
                    "title": meta["title"],
                    "url": reverse("cipa:wizard", kwargs={"pk": eleicao.pk, "step": num}),
                    "active": num == step,
                    "completed": num < int(eleicao.wizard_step or 1),
                }
            )
        return {
            "title": "Criar eleição da CIPA",
            "eleicao": eleicao,
            "step": step,
            "step_title": WIZARD_STEPS[step]["title"],
            "steps": steps,
            "form": form,
            "result": _compute_result(self.request.tenant, eleicao) if eleicao.status == "encerrada" else None,
        }


def cipa_candidatura_publica(request, token):
    if not getattr(request, "tenant", None):
        raise Http404
    try:
        eleicao = CipaEleicao.objects.get(company=request.tenant, candidatura_publica_token=token)
    except CipaEleicao.DoesNotExist:
        raise Http404

    if not eleicao.candidatura_publica_ativa:
        return render(request, "cipa/candidatura_publica.html", {"eleicao": eleicao, "inactive": True})

    if request.method == "POST":
        form = CipaCandidaturaPublicaForm(request.POST, eleicao=eleicao, company=request.tenant)
        if form.is_valid():
            try:
                form.save(company=request.tenant, user=request.user if request.user.is_authenticated else None)
            except forms.ValidationError as exc:
                form.add_error(None, "; ".join(exc.messages))
            else:
                messages.success(request, "Candidatura registrada.")
                return redirect(request.path)
    else:
        form = CipaCandidaturaPublicaForm(eleicao=eleicao, company=request.tenant)

    return render(request, "cipa/candidatura_publica.html", {"eleicao": eleicao, "form": form})


def cipa_votacao_publica(request, token):
    if not getattr(request, "tenant", None):
        raise Http404
    try:
        eleicao = CipaEleicao.objects.get(company=request.tenant, votacao_publica_token=token)
    except CipaEleicao.DoesNotExist:
        raise Http404

    if eleicao.status == "encerrada":
        result = _compute_result(request.tenant, eleicao)
        return render(request, "cipa/votacao_publica.html", {"eleicao": eleicao, "closed": True, "result": result})

    if not eleicao.votacao_publica_ativa or eleicao.status != "votacao":
        return render(request, "cipa/votacao_publica.html", {"eleicao": eleicao, "inactive": True})

    if request.method == "POST":
        form = CipaVotacaoPublicaForm(request.POST, eleicao=eleicao, company=request.tenant)
        if form.is_valid():
            eleitor = form.cleaned_data["eleitor"]
            tipo = form.cleaned_data["tipo"]
            candidato = form.cleaned_data.get("candidato") if tipo == "candidato" else None

            voto, created = CipaVoto.objects.update_or_create(
                company=request.tenant,
                eleicao=eleicao,
                eleitor=eleitor,
                defaults={"tipo": tipo, "candidato": candidato, "updated_by": request.user if request.user.is_authenticated else None},
            )
            if created:
                voto.created_by = request.user if request.user.is_authenticated else None
                voto.save(update_fields=["created_by"])

            messages.success(request, "Voto registrado.")
            return redirect(request.path)
    else:
        form = CipaVotacaoPublicaForm(eleicao=eleicao, company=request.tenant)

    return render(request, "cipa/votacao_publica.html", {"eleicao": eleicao, "form": form})
