from datetime import date, datetime, time, timedelta

from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.db.models import Count, F, Sum
from django.db.models.functions import TruncDate, TruncMonth, TruncWeek
from django.http import HttpResponseRedirect, JsonResponse
from django.urls import reverse
from django.utils import timezone
from django.views import View
from django.views.generic import CreateView, ListView, UpdateView

from apps.core.mixins import TenantFormMixin, TenantQuerysetMixin
from apps.core.views import BaseTenantDetailView
from apps.entregas.models import Entrega
from apps.estoque.models import Estoque
from apps.funcionarios.models import Planta
from .forms import RelatorioForm
from .models import Relatorio


PERIOD_CHOICES = [
    ("today", "Hoje"),
    ("week", "Esta semana"),
    ("last7", "Ultimos 7 dias"),
    ("month", "Este mes"),
    ("last30", "Ultimos 30 dias"),
    ("year", "Este ano"),
    ("custom", "Personalizado"),
]


def _period_range(period_key):
    now = timezone.localtime()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    if period_key == "week":
        start = today_start - timedelta(days=today_start.weekday())
    elif period_key == "last7":
        start = today_start - timedelta(days=6)
    elif period_key == "month":
        start = today_start.replace(day=1)
    elif period_key == "last30":
        start = today_start - timedelta(days=29)
    elif period_key == "year":
        start = today_start.replace(month=1, day=1)
    else:
        start = today_start
    return start, now


def _custom_range(start_value, end_value):
    if not start_value or not end_value:
        return None
    try:
        start_date = date.fromisoformat(str(start_value))
        end_date = date.fromisoformat(str(end_value))
    except ValueError:
        return None
    if end_date < start_date:
        return None
    tz = timezone.get_current_timezone()
    start_dt = timezone.make_aware(datetime.combine(start_date, time.min), tz)
    end_dt = timezone.make_aware(datetime.combine(end_date, time.max), tz)
    return start_dt, end_dt


def _format_dt(value):
    if not value:
        return "-"
    return timezone.localtime(value).strftime("%d/%m/%Y %H:%M")


def _date_series(start, end):
    current = start.date()
    end_date = end.date()
    labels = []
    while current <= end_date:
        labels.append(current.strftime("%d/%m"))
        current += timedelta(days=1)
    return labels


def _build_series(queryset, start, end):
    labels = _date_series(start, end)
    counts = {entry["day"]: entry["total"] for entry in queryset}
    values = []
    current = start.date()
    end_date = end.date()
    while current <= end_date:
        values.append(int(counts.get(current, 0)))
        current += timedelta(days=1)
    return {"labels": labels, "values": values}


def _bucket_range(start, end, category):
    start_date = start.date()
    end_date = end.date()
    buckets = []
    labels = []
    if category == "semana":
        current = start_date - timedelta(days=start_date.weekday())
        while current <= end_date:
            buckets.append(current)
            labels.append(f"Sem {current.isocalendar().week}")
            current += timedelta(days=7)
        return buckets, labels
    if category == "mes":
        current = start_date.replace(day=1)
        while current <= end_date:
            buckets.append(current)
            labels.append(current.strftime("%m/%Y"))
            year = current.year + (1 if current.month == 12 else 0)
            month = 1 if current.month == 12 else current.month + 1
            current = current.replace(year=year, month=month)
        return buckets, labels
    current = start_date
    while current <= end_date:
        buckets.append(current)
        labels.append(current.strftime("%d/%m"))
        current += timedelta(days=1)
    return buckets, labels


def _bucket_expr(category, field_name):
    if category == "semana":
        return TruncWeek(field_name)
    if category == "mes":
        return TruncMonth(field_name)
    return TruncDate(field_name)


def _group_field(source, group_by):
    if source == "estoque":
        if group_by == "planta":
            return "deposito__planta__nome"
        return "produto__nome"
    if group_by == "produto":
        return "produto__nome"
    if group_by == "funcionario":
        return "funcionario__nome"
    if group_by == "planta":
        return "funcionario__planta__nome"
    if group_by == "setor":
        return "funcionario__setor__nome"
    return "produto__nome"


def _value_expr(source, value_type):
    if value_type == "quantidade":
        return Sum("quantidade")
    return Count("id")


class RelatorioListView(PermissionRequiredMixin, LoginRequiredMixin, TenantQuerysetMixin, ListView):
    model = Relatorio
    template_name = "relatorios/list.html"
    permission_required = "relatorios.view_relatorio"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["can_add"] = self.request.user.has_perm("relatorios.add_relatorio")
        context["can_delete"] = self.request.user.has_perm("relatorios.delete_relatorio")
        return context


class RelatorioCreateView(PermissionRequiredMixin, LoginRequiredMixin, TenantFormMixin, CreateView):
    model = Relatorio
    form_class = RelatorioForm
    template_name = "relatorios/editor.html"
    permission_required = "relatorios.add_relatorio"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["relatorio"] = None
        context["widgets"] = []
        context["plantas"] = list(
            Planta.objects.filter(company=self.request.tenant, ativo=True)
            .order_by("nome")
            .values("id", "nome")
        )
        return context

    def get_success_url(self):
        return reverse("relatorios:update", args=[self.object.pk])


class RelatorioUpdateView(PermissionRequiredMixin, LoginRequiredMixin, TenantFormMixin, UpdateView):
    model = Relatorio
    form_class = RelatorioForm
    template_name = "relatorios/editor.html"
    permission_required = "relatorios.change_relatorio"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["relatorio"] = self.object
        context["widgets"] = self.object.widgets or []
        context["plantas"] = list(
            Planta.objects.filter(company=self.request.tenant, ativo=True)
            .order_by("nome")
            .values("id", "nome")
        )
        return context

    def get_queryset(self):
        return super().get_queryset().filter(company=self.request.tenant)

    def get_success_url(self):
        return reverse("relatorios:update", args=[self.object.pk])


class RelatorioDetailView(BaseTenantDetailView):
    model = Relatorio
    template_name = "relatorios/detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        valid_periods = {choice[0] for choice in PERIOD_CHOICES}
        period_label_map = dict(PERIOD_CHOICES)
        plantas_map = {
            str(planta["id"]): planta["nome"]
            for planta in Planta.objects.filter(company=self.request.tenant, ativo=True)
            .values("id", "nome")
        }
        requested_ranges = set()
        requested_plants = set()
        for widget in self.object.widgets or []:
            period = widget.get("period") or "today"
            if period not in valid_periods:
                period = "today"
            if period == "custom":
                custom_range = _custom_range(widget.get("start_date"), widget.get("end_date"))
                if custom_range:
                    requested_ranges.add(("custom", custom_range[0], custom_range[1]))
                else:
                    start, end = _period_range("today")
                    requested_ranges.add(("today", start, end))
            else:
                start, end = _period_range(period)
                requested_ranges.add((period, start, end))
            plant = str(widget.get("plant") or "").strip()
            if plant and plant in plantas_map:
                requested_plants.add(plant)

        requested_plants.add("")
        period_cache = {}
        if not requested_ranges:
            start, end = _period_range("today")
            requested_ranges.add(("today", start, end))
        for period_key, start, end in requested_ranges:
            for plant_key in requested_plants:
                entregas_base = Entrega.objects.filter(
                    company=self.request.tenant,
                    created_at__gte=start,
                    created_at__lte=end,
                )
                if plant_key:
                    entregas_base = entregas_base.filter(funcionario__planta_id=plant_key)

                estoque_base = Estoque.objects.filter(
                    company=self.request.tenant,
                    produto__estoque_minimo__gt=0,
                    quantidade__lte=F("produto__estoque_minimo"),
                )
                if plant_key:
                    estoque_base = estoque_base.filter(deposito__planta_id=plant_key)
                estoque_critico_count = estoque_base.count()
                estoque_qs = (
                    estoque_base.select_related("produto")
                    .annotate(deficit=F("produto__estoque_minimo") - F("quantidade"))
                    .order_by("-deficit", "produto__nome")[:7]
                )
                if estoque_qs:
                    estoque_labels = [estoque.produto.nome[:12] for estoque in estoque_qs]
                    estoque_values = [float(estoque.quantidade) for estoque in estoque_qs]
                else:
                    estoque_labels = []
                    estoque_values = []

                metric_values = {
                    "entregas_realizadas": entregas_base.filter(status="entregue").count(),
                    "entregas_pendentes": entregas_base.filter(status="aguardando").count(),
                    "entregas_canceladas": entregas_base.filter(status="cancelada").count(),
                    "estoque_critico": estoque_critico_count,
                }

                entregas_por_dia = (
                    entregas_base.filter(status="entregue")
                    .annotate(day=TruncDate("created_at"))
                    .values("day")
                    .annotate(total=Count("id"))
                    .order_by("day")
                )
                pendencias_por_dia = (
                    entregas_base.filter(status="aguardando")
                    .annotate(day=TruncDate("created_at"))
                    .values("day")
                    .annotate(total=Count("id"))
                    .order_by("day")
                )
                canceladas_por_dia = (
                    entregas_base.filter(status="cancelada")
                    .annotate(day=TruncDate("created_at"))
                    .values("day")
                    .annotate(total=Count("id"))
                    .order_by("day")
                )

                series_map = {
                    "entregas_por_dia": _build_series(entregas_por_dia, start, end),
                    "entregas_pendentes_por_dia": _build_series(pendencias_por_dia, start, end),
                    "entregas_canceladas_por_dia": _build_series(canceladas_por_dia, start, end),
                    "estoque_critico": {"labels": estoque_labels, "values": estoque_values},
                }
                period_cache[(period_key, plant_key, start, end)] = {
                    "metric_values": metric_values,
                    "series_map": series_map,
                }

        widgets = []
        for widget in self.object.widgets or []:
            data = dict(widget)
            metric = data.get("metric")
            period = data.get("period") or "today"
            if period not in valid_periods:
                period = "today"
            plant = str(data.get("plant") or "").strip()
            if plant not in plantas_map:
                plant = ""
            start = None
            end = None
            period_key = period
            if period == "custom":
                custom_range = _custom_range(data.get("start_date"), data.get("end_date"))
                if custom_range:
                    start, end = custom_range
                    period_key = "custom"
                else:
                    period_key = "today"
            if start is None or end is None:
                start, end = _period_range(period_key)
            cache = period_cache.get((period_key, plant, start, end), {})
            data["value"] = cache.get("metric_values", {}).get(metric)
            data["series_payload"] = cache.get("series_map", {}).get(metric, {"labels": [], "values": []})
            data["period_label"] = period_label_map.get(period, "")
            data["plant_label"] = plantas_map.get(plant, "Todas")

            if data.get("type") == "grafico":
                source = data.get("source") or "entregas"
                group_by = data.get("group_by") or "produto"
                category = data.get("category") or "semana"
                value_type = data.get("value_type") or "quantidade"
                chart_type = data.get("chart_type") or "line"
                limit = data.get("limit") or 10
                show_legend = bool(data.get("show_legend"))
                try:
                    limit = int(limit)
                except (TypeError, ValueError):
                    limit = 10
                if limit <= 0:
                    limit = 10

                if source == "estoque":
                    base_qs = Estoque.objects.filter(
                        company=self.request.tenant,
                        atualizado_em__gte=start,
                        atualizado_em__lte=end,
                    )
                    date_field = "atualizado_em"
                    if plant:
                        base_qs = base_qs.filter(deposito__planta_id=plant)
                else:
                    base_qs = Entrega.objects.filter(
                        company=self.request.tenant,
                        created_at__gte=start,
                        created_at__lte=end,
                    )
                    date_field = "created_at"
                    if plant:
                        base_qs = base_qs.filter(funcionario__planta_id=plant)

                group_field = _group_field(source, group_by)
                value_expr = _value_expr(source, value_type)

                if chart_type == "pie":
                    totals = (
                        base_qs.exclude(**{f"{group_field}__isnull": True})
                        .values(group_field)
                        .annotate(total=value_expr)
                        .order_by("-total")[:limit]
                    )
                    labels = [item[group_field] for item in totals]
                    values = [float(item["total"] or 0) for item in totals]
                    data["series_payload"] = {"labels": labels, "series": values}
                else:
                    if group_field and category == "mes":
                        totals = (
                            base_qs.exclude(**{f"{group_field}__isnull": True})
                            .values(group_field)
                            .annotate(total=value_expr)
                            .order_by("-total")[:limit]
                        )
                        labels = [item[group_field] for item in totals]
                        values = [float(item["total"] or 0) for item in totals]
                        data["series_payload"] = {
                            "labels": labels,
                            "series": [{"name": "Total", "data": values}],
                        }
                    else:
                        buckets, labels = _bucket_range(start, end, category)
                        bucket_expr = _bucket_expr(category, date_field)
                        series = []
                        if group_field:
                            top_groups = list(
                                base_qs.exclude(**{f"{group_field}__isnull": True})
                                .values(group_field)
                                .annotate(total=value_expr)
                                .order_by("-total")[:limit]
                            )
                            group_keys = [item[group_field] for item in top_groups]
                            if group_keys:
                                bucketed = (
                                    base_qs.filter(**{f"{group_field}__in": group_keys})
                                    .annotate(bucket=bucket_expr)
                                    .values(group_field, "bucket")
                                    .annotate(total=value_expr)
                                )
                                grouped_map = {key: {} for key in group_keys}
                                for entry in bucketed:
                                    bucket_val = entry["bucket"]
                                    if bucket_val is None:
                                        continue
                                    bucket_key = bucket_val.date() if hasattr(bucket_val, "date") else bucket_val
                                    grouped_map[entry[group_field]][bucket_key] = float(entry["total"] or 0)
                                for key in group_keys:
                                    data_points = [
                                        grouped_map.get(key, {}).get(bucket, 0) for bucket in buckets
                                    ]
                                    series.append({"name": key, "data": data_points})
                        else:
                            bucketed = (
                                base_qs.annotate(bucket=bucket_expr)
                                .values("bucket")
                                .annotate(total=value_expr)
                            )
                            totals_map = {}
                            for entry in bucketed:
                                bucket_val = entry["bucket"]
                                if bucket_val is None:
                                    continue
                                bucket_key = bucket_val.date() if hasattr(bucket_val, "date") else bucket_val
                                totals_map[bucket_key] = float(entry["total"] or 0)
                            series.append(
                                {"name": "Total", "data": [totals_map.get(bucket, 0) for bucket in buckets]}
                            )

                        data["series_payload"] = {"labels": labels, "series": series}

                data["chart_type"] = chart_type
                data["show_legend"] = show_legend
            elif data.get("type") == "tabela":
                metric = data.get("metric")
                limit = data.get("limit") or 10
                try:
                    limit = int(limit)
                except (TypeError, ValueError):
                    limit = 10
                if limit <= 0:
                    limit = 10

                table_headers = []
                table_rows = []
                base_qs = Entrega.objects.filter(company=self.request.tenant)
                if plant:
                    base_qs = base_qs.filter(funcionario__planta_id=plant)
                if period:
                    base_qs = base_qs.filter(created_at__gte=start, created_at__lte=end)

                if metric == "entregas_pendentes":
                    table_headers = ["Funcionario", "Produto", "Quantidade", "Solicitada em", "Planta"]
                    rows = (
                        base_qs.filter(status="aguardando")
                        .select_related("funcionario", "produto", "funcionario__planta")
                        .order_by("-created_at")[:limit]
                    )
                    for entrega in rows:
                        table_rows.append(
                            [
                                str(entrega.funcionario),
                                str(entrega.produto),
                                float(entrega.quantidade),
                                _format_dt(entrega.created_at),
                                str(entrega.funcionario.planta) if entrega.funcionario.planta_id else "-",
                            ]
                        )
                elif metric == "ultimas_entregas":
                    table_headers = ["Funcionario", "Produto", "Quantidade", "Entregue em", "Planta"]
                    rows = (
                        base_qs.filter(status="entregue")
                        .select_related("funcionario", "produto", "funcionario__planta")
                        .order_by("-entregue_em", "-created_at")[:limit]
                    )
                    for entrega in rows:
                        table_rows.append(
                            [
                                str(entrega.funcionario),
                                str(entrega.produto),
                                float(entrega.quantidade),
                                _format_dt(entrega.entregue_em or entrega.created_at),
                                str(entrega.funcionario.planta) if entrega.funcionario.planta_id else "-",
                            ]
                        )
                elif metric == "ranking_itens":
                    table_headers = ["Produto", "Total"]
                    value_type = data.get("value_type") or "quantidade"
                    value_expr = _value_expr("entregas", value_type)
                    rows = (
                        base_qs.filter(status="entregue")
                        .exclude(produto__nome__isnull=True)
                        .values("produto__nome")
                        .annotate(total=value_expr)
                        .order_by("-total")[:limit]
                    )
                    for item in rows:
                        table_rows.append([item["produto__nome"], float(item["total"] or 0)])

                data["table_headers"] = table_headers
                data["table_rows"] = table_rows

            widgets.append(data)

        context["widgets"] = widgets
        context["period_choices"] = PERIOD_CHOICES
        return context


class RelatorioDeleteView(PermissionRequiredMixin, View):
    permission_required = "relatorios.delete_relatorio"

    def post(self, request, pk):
        relatorio = Relatorio.objects.filter(pk=pk, company=request.tenant).first()
        if not relatorio:
            return JsonResponse({"ok": False}, status=404)
        relatorio.delete()
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({"ok": True, "row_id": pk})
        return HttpResponseRedirect(reverse("relatorios:list"))
