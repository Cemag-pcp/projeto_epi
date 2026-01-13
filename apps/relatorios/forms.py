import json
from datetime import date

from django import forms

from apps.core.forms import BootstrapModelForm
from .models import Relatorio

WIDGET_TYPES = {
    "kpi",
    "tabela",
    "pendencias",
    "grafico",
}

KPI_METRICS = {
    "entregas_realizadas",
    "entregas_pendentes",
    "entregas_canceladas",
    "estoque_critico",
}

TABELA_METRICS = {
    "entregas_pendentes",
    "ultimas_entregas",
    "ranking_itens",
}

GRAFICO_METRICS = {
    "entregas_por_dia",
    "entregas_pendentes_por_dia",
    "entregas_canceladas_por_dia",
    "estoque_critico",
}

GRAFICO_SIZES = {
    "half",
    "full",
}

GRAFICO_TYPES = {
    "line",
    "bar",
    "pie",
}

PERIOD_KEYS = {
    "today",
    "week",
    "last7",
    "month",
    "last30",
    "year",
    "custom",
}

SOURCE_OPTIONS = {
    "entregas",
    "estoque",
}

GROUP_BY_OPTIONS = {
    "produto",
    "funcionario",
    "planta",
    "setor",
}

CATEGORY_OPTIONS = {
    "dia",
    "semana",
    "mes",
}

VALUE_TYPE_OPTIONS = {
    "quantidade",
    "itens",
}

def _clean_plant(value):
    if value is None:
        return ""
    value = str(value).strip()
    if value.isdigit():
        return value
    return ""


def _clean_date(value):
    if not value:
        return ""
    try:
        parsed = date.fromisoformat(str(value))
    except ValueError:
        return ""
    return parsed.isoformat()


class RelatorioForm(BootstrapModelForm):
    widgets_json = forms.CharField(required=False, widget=forms.HiddenInput())

    class Meta:
        model = Relatorio
        fields = ["nome", "descricao"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        descricao = self.fields.get("descricao")
        if descricao:
            descricao.widget.attrs["rows"] = 2
        widgets = []
        if self.instance and getattr(self.instance, "widgets", None):
            widgets = self.instance.widgets or []
        self.fields["widgets_json"].initial = json.dumps(widgets)

    def clean_widgets_json(self):
        raw = self.cleaned_data.get("widgets_json") or "[]"
        try:
            widgets = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise forms.ValidationError("Widgets invalidos.") from exc
        if not isinstance(widgets, list):
            raise forms.ValidationError("Widgets invalidos.")
        cleaned = []
        for widget in widgets:
            if not isinstance(widget, dict):
                continue
            widget_type = widget.get("type")
            if widget_type not in WIDGET_TYPES:
                continue
            metric = str(widget.get("metric") or "").strip()
            if widget_type == "kpi" and metric not in KPI_METRICS:
                metric = ""
            size = str(widget.get("size") or "").strip()
            period = str(widget.get("period") or "").strip()
            plant = _clean_plant(widget.get("plant"))
            source = str(widget.get("source") or "").strip()
            group_by = str(widget.get("group_by") or "").strip()
            category = str(widget.get("category") or "").strip()
            value_type = str(widget.get("value_type") or "").strip()
            chart_type = str(widget.get("chart_type") or "").strip()
            limit = widget.get("limit")
            show_legend = bool(widget.get("show_legend"))
            if widget_type == "grafico":
                if metric not in GRAFICO_METRICS:
                    metric = ""
                if size not in GRAFICO_SIZES:
                    size = "half"
                if period not in PERIOD_KEYS:
                    period = "today"
                if source not in SOURCE_OPTIONS:
                    source = "entregas"
                if group_by not in GROUP_BY_OPTIONS:
                    group_by = "produto"
                if category not in CATEGORY_OPTIONS:
                    category = "semana"
                if value_type not in VALUE_TYPE_OPTIONS:
                    value_type = "quantidade"
                if chart_type not in GRAFICO_TYPES:
                    chart_type = "line"
                try:
                    limit = int(limit)
                except (TypeError, ValueError):
                    limit = 10
                if limit <= 0:
                    limit = 10
            elif widget_type == "kpi":
                if period not in PERIOD_KEYS:
                    period = "today"
                size = ""
            elif widget_type == "tabela":
                if metric not in TABELA_METRICS:
                    metric = ""
                if period not in PERIOD_KEYS:
                    period = "today"
                if value_type not in VALUE_TYPE_OPTIONS:
                    value_type = "quantidade"
                source = ""
                group_by = ""
                category = ""
                chart_type = ""
                try:
                    limit = int(limit)
                except (TypeError, ValueError):
                    limit = 10
                if limit <= 0:
                    limit = 10
                size = ""
            else:
                size = ""
                period = ""
                plant = ""
                source = ""
                group_by = ""
                category = ""
                value_type = ""
                chart_type = ""
                limit = ""
                show_legend = False
            start_date = ""
            end_date = ""
            if widget_type in {"grafico", "kpi"} and period == "custom":
                start_date = _clean_date(widget.get("start_date"))
                end_date = _clean_date(widget.get("end_date"))
            cleaned.append(
                {
                    "id": str(widget.get("id") or ""),
                    "type": widget_type,
                    "title": str(widget.get("title") or "").strip(),
                    "metric": metric,
                    "size": size,
                    "period": period,
                    "plant": plant,
                    "source": source,
                    "group_by": group_by,
                    "category": category,
                    "value_type": value_type,
                    "chart_type": chart_type,
                    "limit": limit,
                    "show_legend": show_legend,
                    "start_date": start_date,
                    "end_date": end_date,
                }
            )
        return cleaned

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.widgets = self.cleaned_data.get("widgets_json", [])
        if commit:
            instance.save()
        return instance
