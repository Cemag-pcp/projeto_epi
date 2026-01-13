from django.contrib.auth.mixins import PermissionRequiredMixin
from django.http import JsonResponse, HttpResponseRedirect
from django.template.loader import render_to_string
from django.urls import reverse
from django.views import View

from apps.core.views import BaseTenantCreateView, BaseTenantListView, BaseTenantUpdateView
from .forms import SetorForm
from .models import Setor
from apps.funcionarios.models import Funcionario


class SetorListView(BaseTenantListView):
    model = Setor
    template_name = "setores/list.html"
    form_class = SetorForm
    title = "Setores"
    headers = ["Nome", "Descricao", "Responsaveis", "Ativo"]
    row_fields = ["nome", "descricao", "responsaveis", "ativo"]
    filter_definitions = [
        {"name": "nome", "label": "Nome", "lookup": "icontains", "type": "text"},
        {
            "name": "responsaveis__nome",
            "label": "Responsavel",
            "lookup": "icontains",
            "type": "text",
        },
        {
            "name": "ativo",
            "label": "Ativo",
            "lookup": "exact_bool",
            "type": "select",
            "options": [("", "Todos"), ("1", "Ativo"), ("0", "Inativo")],
        },
    ]
    create_url_name = "setores:create"
    update_url_name = "setores:update"

    def get_queryset(self):
        return super().get_queryset().prefetch_related("responsaveis").distinct()


class SetorCreateView(BaseTenantCreateView):
    model = Setor
    form_class = SetorForm
    success_url_name = "setores:list"

    def form_valid(self, form):
        nome = (form.cleaned_data.get("nome") or "").strip()
        if nome and Setor.objects.filter(company=self.request.tenant, nome__iexact=nome).exists():
            form.add_error("nome", "Setor ja cadastrado.")
            return self.form_invalid(form)
        response = super().form_valid(form)
        if self.request.headers.get("X-Requested-With") == "XMLHttpRequest":
            row_html = render_to_string(
                "setores/_setor_row.html",
                {"setor": self.object},
                request=self.request,
            )
            edit_modal_html = render_to_string(
                "setores/_setor_edit_modal.html",
                {
                    "setor": self.object,
                    "form": SetorForm(instance=self.object),
                    "update_url": reverse("setores:update", args=[self.object.pk]),
                },
                request=self.request,
            )
            form_html = render_to_string(
                "components/_form.html",
                {"form": SetorForm(), "form_action": reverse("setores:create")},
                request=self.request,
            )
            return JsonResponse(
                {
                    "ok": True,
                    "action": "create",
                    "row_id": self.object.pk,
                    "row_html": row_html,
                    "edit_modal_html": edit_modal_html,
                    "form_html": form_html,
                }
            )
        return response

    def form_invalid(self, form):
        if self.request.headers.get("X-Requested-With") == "XMLHttpRequest":
            form_html = render_to_string(
                "components/_form.html",
                {"form": form, "form_action": reverse("setores:create")},
                request=self.request,
            )
            return JsonResponse({"ok": False, "form_html": form_html}, status=400)
        return super().form_invalid(form)


class SetorUpdateView(BaseTenantUpdateView):
    model = Setor
    form_class = SetorForm
    success_url_name = "setores:list"

    def form_valid(self, form):
        nome = (form.cleaned_data.get("nome") or "").strip()
        if (
            nome
            and Setor.objects.filter(company=self.request.tenant, nome__iexact=nome)
            .exclude(pk=form.instance.pk)
            .exists()
        ):
            form.add_error("nome", "Setor ja cadastrado.")
            return self.form_invalid(form)
        response = super().form_valid(form)
        if self.request.headers.get("X-Requested-With") == "XMLHttpRequest":
            row_html = render_to_string(
                "setores/_setor_row.html",
                {"setor": self.object},
                request=self.request,
            )
            return JsonResponse(
                {
                    "ok": True,
                    "action": "update",
                    "row_id": self.object.pk,
                    "row_html": row_html,
                }
            )
        return response

    def form_invalid(self, form):
        if self.request.headers.get("X-Requested-With") == "XMLHttpRequest":
            form_html = render_to_string(
                "components/_form.html",
                {
                    "form": form,
                    "form_action": reverse("setores:update", args=[self.get_object().pk]),
                },
                request=self.request,
            )
            return JsonResponse(
                {"ok": False, "form_html": form_html, "row_id": self.get_object().pk},
                status=400,
            )
        return super().form_invalid(form)


class SetorToggleActiveView(PermissionRequiredMixin, View):
    permission_required = "setores.change_setor"

    def post(self, request, pk):
        setor = Setor.objects.filter(pk=pk, company=request.tenant).first()
        if not setor:
            return JsonResponse({"ok": False}, status=404)
        funcionarios = list(
            Funcionario.objects.filter(company=request.tenant, setor=setor)
            .values("id", "nome")
            .distinct()
        )
        if funcionarios:
            return JsonResponse(
                {"ok": False, "blocked": True, "funcionarios": funcionarios, "row_id": setor.pk},
                status=400,
            )
        setor.ativo = not setor.ativo
        setor.updated_by = request.user
        setor.save(update_fields=["ativo", "updated_by"])
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            row_html = render_to_string(
                "setores/_setor_row.html",
                {"setor": setor},
                request=request,
            )
            return JsonResponse({"ok": True, "row_id": setor.pk, "row_html": row_html})
        return HttpResponseRedirect(reverse("setores:list"))


class SetorUsoView(PermissionRequiredMixin, View):
    permission_required = "setores.view_setor"

    def get(self, request, pk):
        setor = Setor.objects.filter(pk=pk, company=request.tenant).first()
        if not setor:
            return JsonResponse({"ok": False}, status=404)
        funcionarios = list(
            Funcionario.objects.filter(company=request.tenant, setor=setor)
            .values("id", "nome")
            .distinct()
        )
        return JsonResponse({"ok": True, "funcionarios": funcionarios})


class SetorDeleteView(PermissionRequiredMixin, View):
    permission_required = "setores.delete_setor"

    def post(self, request, pk):
        setor = Setor.objects.filter(pk=pk, company=request.tenant).first()
        if not setor:
            return JsonResponse({"ok": False}, status=404)
        funcionarios = list(
            Funcionario.objects.filter(company=request.tenant, setor=setor)
            .values("id", "nome")
            .distinct()
        )
        if funcionarios:
            return JsonResponse(
                {"ok": False, "blocked": True, "funcionarios": funcionarios, "row_id": setor.pk},
                status=400,
            )
        setor.delete()
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({"ok": True, "row_id": pk})
        return HttpResponseRedirect(reverse("setores:list"))
