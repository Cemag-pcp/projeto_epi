from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import F, FloatField, ExpressionWrapper
from django.shortcuts import redirect, render
from django.utils import timezone

from apps.funcionarios.models import Planta
from apps.entregas.models import Entrega
from apps.estoque.models import Estoque
from apps.produtos.models import Produto
from apps.treinamentos.models import TreinamentoPendencia, TurmaAula


@login_required
def home(request):
    tenant = request.tenant
    today = timezone.localdate()
    yesterday = today - timedelta(days=1)

    entregas_hoje = Entrega.objects.filter(
        company=tenant, created_at__date=today
    ).count()
    entregas_ontem = Entrega.objects.filter(
        company=tenant, created_at__date=yesterday
    ).count()
    if entregas_ontem:
        delta = ((entregas_hoje - entregas_ontem) / entregas_ontem) * 100
        entregas_delta_label = f"{delta:+.0f}% vs. ontem"
    else:
        entregas_delta_label = "Sem comparacao"

    epis_vencendo = Produto.objects.filter(
        company=tenant,
        controle_epi=True,
        data_vencimento_ca__isnull=False,
        data_vencimento_ca__gte=today,
        data_vencimento_ca__lte=today + timedelta(days=30),
    ).count()

    treinamentos_pendentes = TreinamentoPendencia.objects.filter(
        company=tenant, status="pendente"
    ).count()

    estoque_critico_qs = Estoque.objects.filter(
        company=tenant,
        produto__estoque_minimo__gt=0,
        quantidade__lte=F("produto__estoque_minimo"),
    )
    estoque_critico = estoque_critico_qs.count()

    operacoes = (
        Entrega.objects.filter(company=tenant)
        .select_related("funcionario", "produto")
        .order_by("-created_at")[:4]
    )
    status_map = {
        "entregue": {"label": "Entregue", "class": "bg-success-subtle text-success"},
        "aguardando": {"label": "Aguardando entrega", "class": "bg-warning-subtle text-warning"},
        "cancelada": {"label": "Cancelada", "class": "bg-danger-subtle text-danger"},
    }
    operacoes_list = []
    for entrega in operacoes:
        status = status_map.get(entrega.status, {"label": entrega.status, "class": "bg-secondary-subtle text-secondary"})
        operacoes_list.append(
            {
                "funcionario": entrega.funcionario.nome,
                "produto": entrega.produto.nome,
                "quantidade": entrega.quantidade,
                "status_label": status["label"],
                "status_class": status["class"],
            }
        )

    treinamentos_expirados = TreinamentoPendencia.objects.filter(
        company=tenant, status="expirado"
    ).count()
    ca_expirado = Produto.objects.filter(
        company=tenant,
        controle_epi=True,
        data_vencimento_ca__isnull=False,
        data_vencimento_ca__lt=today,
    ).count()
    assinaturas_pendentes = Entrega.objects.filter(
        company=tenant, status="aguardando"
    ).count()
    entregas_pendentes = assinaturas_pendentes

    alerts = [
        {
            "title": "Treinamentos vencidos",
            "subtitle": f"{treinamentos_expirados} colaboradores com pendencias",
            "class": "bg-danger-subtle text-danger" if treinamentos_expirados else "bg-secondary-subtle text-secondary",
            "label": "Alto" if treinamentos_expirados else "Baixo",
        },
        {
            "title": "EPI com CA expirado",
            "subtitle": f"{ca_expirado} itens precisam substituicao",
            "class": "bg-warning-subtle text-warning" if ca_expirado else "bg-secondary-subtle text-secondary",
            "label": "Medio" if ca_expirado else "Baixo",
        },
        {
            "title": "Assinaturas pendentes",
            "subtitle": f"{assinaturas_pendentes} recibos aguardando confirmacao",
            "class": "bg-secondary-subtle text-secondary",
            "label": "Baixo",
        },
    ]

    upcoming_aulas = (
        TurmaAula.objects.filter(company=tenant, turma__finalizada=False, data__gte=today)
        .select_related("turma__treinamento")
        .order_by("data")[:3]
    )
    agenda_items = []
    for aula in upcoming_aulas:
        if aula.data == today:
            data_label = "Hoje"
        elif aula.data == today + timedelta(days=1):
            data_label = "Amanha"
        else:
            data_label = aula.data.strftime("%d/%m")
        inscritos = aula.turma.participantes.count()
        agenda_items.append(
            {
                "treinamento": aula.turma.treinamento.nome,
                "data_label": data_label,
                "local": aula.turma.local,
                "inscritos": inscritos,
            }
        )

    estoque_critico_items = (
        estoque_critico_qs.select_related("produto", "deposito__planta")
        .annotate(
            percent=ExpressionWrapper(
                F("quantidade") * 100.0 / F("produto__estoque_minimo"),
                output_field=FloatField(),
            )
        )
        .order_by("percent")[:3]
    )
    estoque_cards = []
    for item in estoque_critico_items:
        percent = int(max(0, min(100, item.percent or 0)))
        if percent <= 15:
            tone = "danger"
        elif percent <= 35:
            tone = "warning"
        else:
            tone = "secondary"
        estoque_cards.append(
            {
                "produto": item.produto.nome,
                "planta": item.deposito.planta.nome if item.deposito and item.deposito.planta else "-",
                "percent": percent,
                "tone": tone,
            }
        )

    context = {
        "entregas_hoje": entregas_hoje,
        "entregas_delta_label": entregas_delta_label,
        "epis_vencendo": epis_vencendo,
        "treinamentos_pendentes": treinamentos_pendentes,
        "estoque_critico": estoque_critico,
        "entregas_pendentes": entregas_pendentes,
        "operacoes": operacoes_list,
        "alerts": alerts,
        "agenda_items": agenda_items,
        "estoque_cards": estoque_cards,
    }
    return render(request, "layout/home.html", context)


@login_required
def components(request):
    paginator = Paginator(list(range(1, 51)), 10)
    page_obj = paginator.page(2)
    return render(request, "layout/components.html", {"pagination_page_obj": page_obj})


@login_required
def planta_select(request):
    if request.method != "POST":
        return redirect("ui-home")
    planta_id = request.POST.get("planta_id")
    if planta_id and request.tenant:
        exists = Planta.objects.filter(
            pk=planta_id,
            company=request.tenant,
            ativo=True,
        ).exists()
        if exists:
            request.session["planta_id"] = int(planta_id)
    next_url = request.POST.get("next") or request.META.get("HTTP_REFERER") or "/"
    return redirect(next_url)
