from django.contrib.auth.mixins import PermissionRequiredMixin
from django.http import JsonResponse, HttpResponseRedirect
from django.template.loader import render_to_string
from django.urls import reverse
from django.views import View

from apps.core.views import BaseTenantCreateView, BaseTenantListView, BaseTenantUpdateView
from .forms import FornecedorForm
from .models import Fornecedor
from apps.produtos.models import ProdutoFornecedor


class FornecedorListView(BaseTenantListView):
    model = Fornecedor
    template_name = "fornecedores/list.html"
    form_class = FornecedorForm
    title = "Fornecedores"
    headers = ["Nome", "Documento", "Email", "Ativo"]
    row_fields = ["nome", "documento", "email", "ativo"]
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
    create_url_name = "fornecedores:create"
    update_url_name = "fornecedores:update"


class FornecedorCreateView(BaseTenantCreateView):
    model = Fornecedor
    form_class = FornecedorForm
    success_url_name = "fornecedores:list"

    def form_valid(self, form):
        nome = (form.cleaned_data.get("nome") or "").strip()
        documento = (form.cleaned_data.get("documento") or "").strip()
        email = (form.cleaned_data.get("email") or "").strip()
        duplicado = (
            Fornecedor.objects.filter(company=self.request.tenant, nome__iexact=nome)
            .exclude(pk=form.instance.pk)
            .exists()
        )
        if duplicado:
            form.add_error("nome", "Fornecedor ja cadastrado.")
            return self.form_invalid(form)
        if documento:
            if (
                Fornecedor.objects.filter(company=self.request.tenant, documento__iexact=documento)
                .exclude(pk=form.instance.pk)
                .exists()
            ):
                form.add_error("documento", "Documento ja cadastrado.")
                return self.form_invalid(form)
        if email:
            if (
                Fornecedor.objects.filter(company=self.request.tenant, email__iexact=email)
                .exclude(pk=form.instance.pk)
                .exists()
            ):
                form.add_error("email", "Email ja cadastrado.")
                return self.form_invalid(form)
        response = super().form_valid(form)
        if self.request.headers.get("X-Requested-With") == "XMLHttpRequest":
            row_html = render_to_string(
                "fornecedores/_fornecedor_row.html",
                {"fornecedor": self.object},
                request=self.request,
            )
            edit_modal_html = render_to_string(
                "fornecedores/_fornecedor_edit_modal.html",
                {
                    "fornecedor": self.object,
                    "form": FornecedorForm(instance=self.object),
                    "update_url": reverse("fornecedores:update", args=[self.object.pk]),
                },
                request=self.request,
            )
            form_html = render_to_string(
                "components/_form.html",
                {"form": FornecedorForm(), "form_action": reverse("fornecedores:create")},
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
                {"form": form, "form_action": reverse("fornecedores:create")},
                request=self.request,
            )
            return JsonResponse({"ok": False, "form_html": form_html}, status=400)
        return super().form_invalid(form)


class FornecedorUpdateView(BaseTenantUpdateView):
    model = Fornecedor
    form_class = FornecedorForm
    success_url_name = "fornecedores:list"

    def form_valid(self, form):
        nome = (form.cleaned_data.get("nome") or "").strip()
        documento = (form.cleaned_data.get("documento") or "").strip()
        email = (form.cleaned_data.get("email") or "").strip()
        duplicado = (
            Fornecedor.objects.filter(company=self.request.tenant, nome__iexact=nome)
            .exclude(pk=form.instance.pk)
            .exists()
        )
        if duplicado:
            form.add_error("nome", "Fornecedor ja cadastrado.")
            return self.form_invalid(form)
        if documento:
            if (
                Fornecedor.objects.filter(company=self.request.tenant, documento__iexact=documento)
                .exclude(pk=form.instance.pk)
                .exists()
            ):
                form.add_error("documento", "Documento ja cadastrado.")
                return self.form_invalid(form)
        if email:
            if (
                Fornecedor.objects.filter(company=self.request.tenant, email__iexact=email)
                .exclude(pk=form.instance.pk)
                .exists()
            ):
                form.add_error("email", "Email ja cadastrado.")
                return self.form_invalid(form)
        response = super().form_valid(form)
        if self.request.headers.get("X-Requested-With") == "XMLHttpRequest":
            row_html = render_to_string(
                "fornecedores/_fornecedor_row.html",
                {"fornecedor": self.object},
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
                    "form_action": reverse("fornecedores:update", args=[self.get_object().pk]),
                },
                request=self.request,
            )
            return JsonResponse(
                {"ok": False, "form_html": form_html, "row_id": self.get_object().pk},
                status=400,
            )
        return super().form_invalid(form)


class FornecedorToggleActiveView(PermissionRequiredMixin, View):
    permission_required = "fornecedores.change_fornecedor"

    def post(self, request, pk):
        fornecedor = Fornecedor.objects.filter(pk=pk, company=request.tenant).first()
        if not fornecedor:
            return JsonResponse({"ok": False}, status=404)
        produtos = list(
            ProdutoFornecedor.objects.filter(fornecedor=fornecedor)
            .select_related("produto")
            .values_list("produto__nome", flat=True)
            .distinct()
        )
        if produtos:
            return JsonResponse(
                {"ok": False, "blocked": True, "produtos": produtos, "row_id": fornecedor.pk},
                status=400,
            )
        fornecedor.ativo = not fornecedor.ativo
        fornecedor.updated_by = request.user
        fornecedor.save(update_fields=["ativo", "updated_by"])
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            row_html = render_to_string(
                "fornecedores/_fornecedor_row.html",
                {"fornecedor": fornecedor},
                request=request,
            )
            return JsonResponse({"ok": True, "row_id": fornecedor.pk, "row_html": row_html})
        return HttpResponseRedirect(reverse("fornecedores:list"))


class FornecedorDeleteView(PermissionRequiredMixin, View):
    permission_required = "fornecedores.delete_fornecedor"

    def post(self, request, pk):
        fornecedor = Fornecedor.objects.filter(pk=pk, company=request.tenant).first()
        if not fornecedor:
            return JsonResponse({"ok": False}, status=404)
        produtos = list(
            ProdutoFornecedor.objects.filter(fornecedor=fornecedor)
            .select_related("produto")
            .values_list("produto__nome", flat=True)
            .distinct()
        )
        if produtos:
            return JsonResponse(
                {"ok": False, "blocked": True, "produtos": produtos, "row_id": fornecedor.pk},
                status=400,
            )
        fornecedor.delete()
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({"ok": True, "row_id": pk})
        return HttpResponseRedirect(reverse("fornecedores:list"))


class FornecedorUsoView(PermissionRequiredMixin, View):
    permission_required = "fornecedores.view_fornecedor"

    def get(self, request, pk):
        fornecedor = Fornecedor.objects.filter(pk=pk, company=request.tenant).first()
        if not fornecedor:
            return JsonResponse({"ok": False}, status=404)
        produtos = list(
            ProdutoFornecedor.objects.filter(fornecedor=fornecedor)
            .select_related("produto")
            .values_list("produto__nome", flat=True)
            .distinct()
        )
        return JsonResponse({"ok": True, "produtos": produtos})
