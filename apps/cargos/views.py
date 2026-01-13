from django.contrib.auth.mixins import PermissionRequiredMixin
from django.http import JsonResponse, HttpResponseRedirect
from django.template.loader import render_to_string
from django.urls import reverse
from django.views import View

from apps.core.views import BaseTenantCreateView, BaseTenantListView, BaseTenantUpdateView
from apps.funcionarios.models import Funcionario
from .forms import CargoForm
from .models import Cargo


class CargoListView(BaseTenantListView):
    model = Cargo
    template_name = "cargos/list.html"
    form_class = CargoForm
    title = "Cargos"
    headers = ["Nome", "Setor", "Ativo"]
    row_fields = ["nome", "setor", "ativo"]
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
    create_url_name = "cargos:create"
    update_url_name = "cargos:update"


class CargoCreateView(BaseTenantCreateView):
    model = Cargo
    form_class = CargoForm
    success_url_name = "cargos:list"

    def form_valid(self, form):
        response = super().form_valid(form)
        if self.request.headers.get("X-Requested-With") == "XMLHttpRequest":
            row_html = render_to_string(
                "cargos/_cargo_row.html",
                {"cargo": self.object},
                request=self.request,
            )
            edit_modal_html = render_to_string(
                "cargos/_cargo_edit_modal.html",
                {
                    "cargo": self.object,
                    "form": CargoForm(instance=self.object),
                    "update_url": reverse("cargos:update", args=[self.object.pk]),
                },
                request=self.request,
            )
            form_html = render_to_string(
                "components/_form.html",
                {"form": CargoForm(), "form_action": reverse("cargos:create")},
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
                {"form": form, "form_action": reverse("cargos:create")},
                request=self.request,
            )
            return JsonResponse({"ok": False, "form_html": form_html}, status=400)
        return super().form_invalid(form)


class CargoUpdateView(BaseTenantUpdateView):
    model = Cargo
    form_class = CargoForm
    success_url_name = "cargos:list"

    def form_valid(self, form):
        response = super().form_valid(form)
        if self.request.headers.get("X-Requested-With") == "XMLHttpRequest":
            row_html = render_to_string(
                "cargos/_cargo_row.html",
                {"cargo": self.object},
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
                    "form_action": reverse("cargos:update", args=[self.get_object().pk]),
                },
                request=self.request,
            )
            return JsonResponse(
                {"ok": False, "form_html": form_html, "row_id": self.get_object().pk},
                status=400,
            )
        return super().form_invalid(form)


class CargoToggleActiveView(PermissionRequiredMixin, View):
    permission_required = "cargos.change_cargo"

    def post(self, request, pk):
        cargo = Cargo.objects.filter(pk=pk, company=request.tenant).first()
        if not cargo:
            return JsonResponse({"ok": False}, status=404)
        funcionarios = list(
            Funcionario.objects.filter(company=request.tenant, cargo=cargo)
            .values("id", "nome")
            .distinct()
        )
        if funcionarios:
            return JsonResponse(
                {"ok": False, "blocked": True, "funcionarios": funcionarios, "row_id": cargo.pk},
                status=400,
            )
        cargo.ativo = not cargo.ativo
        cargo.updated_by = request.user
        cargo.save(update_fields=["ativo", "updated_by"])
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            row_html = render_to_string(
                "cargos/_cargo_row.html",
                {"cargo": cargo},
                request=request,
            )
            return JsonResponse({"ok": True, "row_id": cargo.pk, "row_html": row_html})
        return HttpResponseRedirect(reverse("cargos:list"))


class CargoUsoView(PermissionRequiredMixin, View):
    permission_required = "cargos.view_cargo"

    def get(self, request, pk):
        cargo = Cargo.objects.filter(pk=pk, company=request.tenant).first()
        if not cargo:
            return JsonResponse({"ok": False}, status=404)
        funcionarios = list(
            Funcionario.objects.filter(company=request.tenant, cargo=cargo)
            .values("id", "nome")
            .distinct()
        )
        return JsonResponse({"ok": True, "funcionarios": funcionarios})


class CargoDeleteView(PermissionRequiredMixin, View):
    permission_required = "cargos.delete_cargo"

    def post(self, request, pk):
        cargo = Cargo.objects.filter(pk=pk, company=request.tenant).first()
        if not cargo:
            return JsonResponse({"ok": False}, status=404)
        funcionarios = list(
            Funcionario.objects.filter(company=request.tenant, cargo=cargo)
            .values("id", "nome")
            .distinct()
        )
        if funcionarios:
            return JsonResponse(
                {"ok": False, "blocked": True, "funcionarios": funcionarios, "row_id": cargo.pk},
                status=400,
            )
        cargo.delete()
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({"ok": True, "row_id": pk})
        return HttpResponseRedirect(reverse("cargos:list"))
