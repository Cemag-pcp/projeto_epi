from django.http import JsonResponse
from django.shortcuts import render
from django.template.loader import render_to_string
from django.urls import reverse, reverse_lazy

from apps.core.views import (
    BaseTenantCreateView,
    BaseTenantDetailView,
    BaseTenantListView,
    BaseTenantUpdateView,
)
from .forms import AfastamentoForm, FuncionarioForm
from .models import Afastamento, Funcionario


class FuncionarioListView(BaseTenantListView):
    model = Funcionario
    template_name = "funcionarios/list.html"
    form_class = FuncionarioForm
    title = "Funcionarios"
    headers = ["Nome", "Cargo", "Setor", "Tipo", "Ativo"]
    row_fields = ["nome", "cargo", "setor", "tipo", "ativo"]
    filter_definitions = [
        {"name": "nome", "label": "Nome", "lookup": "icontains", "type": "text"},
        {
            "name": "ativo",
            "label": "Ativo",
            "lookup": "exact_bool",
            "type": "select",
            "options": [("", "Todos"), ("1", "Ativo"), ("0", "Inativo")],
        },
    ]
    create_url_name = "funcionarios:create"
    update_url_name = "funcionarios:update"


class FuncionarioCreateView(BaseTenantCreateView):
    model = Funcionario
    form_class = FuncionarioForm
    success_url_name = "funcionarios:list"


class FuncionarioUpdateView(BaseTenantUpdateView):
    model = Funcionario
    form_class = FuncionarioForm
    success_url_name = "funcionarios:list"


class FuncionarioDetailView(BaseTenantDetailView):
    model = Funcionario
    template_name = "funcionarios/detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["afastamento_form"] = AfastamentoForm(initial={"funcionario": self.object})
        context["afastamentos_create_url"] = reverse_lazy("funcionarios:afastamentos_create")
        context["afastamento_edit_rows"] = [
            {
                "object": afastamento,
                "form": AfastamentoForm(instance=afastamento),
                "update_url": reverse_lazy("funcionarios:afastamentos_update", args=[afastamento.pk]),
            }
            for afastamento in self.object.afastamentos.all()
        ]
        return context


class AfastamentoListView(BaseTenantListView):
    model = Afastamento
    template_name = "funcionarios/afastamentos_list.html"
    form_class = AfastamentoForm
    title = "Afastamentos"
    headers = [
        "Data Inicio",
        "Data Fim",
        "Qtde. Dias Afastado",
        "Motivo de Afastamento",
        "Nome do Arquivo",
    ]
    row_fields = ["data_inicio", "data_fim", "dias_afastado", "motivo", "nome_arquivo"]
    create_url_name = "funcionarios:afastamentos_create"
    update_url_name = "funcionarios:afastamentos_update"


class AfastamentoCreateView(BaseTenantCreateView):
    model = Afastamento
    form_class = AfastamentoForm

    def get_initial(self):
        initial = super().get_initial()
        funcionario_id = self.request.GET.get("funcionario")
        if funcionario_id:
            initial["funcionario"] = funcionario_id
        return initial

    def get_success_url(self):
        return reverse("funcionarios:detail", args=[self.object.funcionario_id])

    def form_valid(self, form):
        response = super().form_valid(form)
        if self.request.headers.get("X-Requested-With") == "XMLHttpRequest":
            row_html = render_to_string(
                "funcionarios/_afastamento_row.html",
                {"afastamento": self.object},
                request=self.request,
            )
            form_html = render_to_string(
                "components/_form.html",
                {
                    "form": AfastamentoForm(initial={"funcionario": self.object.funcionario}),
                    "form_action": reverse_lazy("funcionarios:afastamentos_create"),
                },
                request=self.request,
            )
            return JsonResponse(
                {"ok": True, "action": "create", "row_html": row_html, "form_html": form_html}
            )
        return response

    def form_invalid(self, form):
        if self.request.headers.get("X-Requested-With") == "XMLHttpRequest":
            form_html = render_to_string(
                "components/_form.html",
                {"form": form, "form_action": reverse_lazy("funcionarios:afastamentos_create")},
                request=self.request,
            )
            return JsonResponse({"ok": False, "form_html": form_html})
        return super().form_invalid(form)


class AfastamentoUpdateView(BaseTenantUpdateView):
    model = Afastamento
    form_class = AfastamentoForm

    def get_success_url(self):
        return reverse("funcionarios:detail", args=[self.object.funcionario_id])

    def form_valid(self, form):
        response = super().form_valid(form)
        if self.request.headers.get("X-Requested-With") == "XMLHttpRequest":
            row_html = render_to_string(
                "funcionarios/_afastamento_row.html",
                {"afastamento": self.object},
                request=self.request,
            )
            return JsonResponse(
                {
                    "ok": True,
                    "action": "update",
                    "row_html": row_html,
                    "row_id": self.object.pk,
                }
            )
        return response

    def form_invalid(self, form):
        if self.request.headers.get("X-Requested-With") == "XMLHttpRequest":
            form_html = render_to_string(
                "components/_form.html",
                {
                    "form": form,
                    "form_action": reverse_lazy("funcionarios:afastamentos_update", args=[self.get_object().pk]),
                },
                request=self.request,
            )
            return JsonResponse({"ok": False, "form_html": form_html, "row_id": self.get_object().pk})
        self.object = self.get_object()
        funcionario = self.object.funcionario
        context = {
            "object": funcionario,
            "afastamento_form": AfastamentoForm(initial={"funcionario": funcionario}),
            "afastamentos_create_url": reverse_lazy("funcionarios:afastamentos_create"),
            "afastamento_edit_rows": [
                {
                    "object": afastamento,
                    "form": form if afastamento.pk == self.object.pk else AfastamentoForm(instance=afastamento),
                    "update_url": reverse_lazy("funcionarios:afastamentos_update", args=[afastamento.pk]),
                }
                for afastamento in funcionario.afastamentos.all()
            ],
            "afastamento_edit_errors_id": self.object.pk,
        }
        return render(self.request, "funcionarios/detail.html", context)
