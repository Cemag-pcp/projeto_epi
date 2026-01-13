from django.contrib.auth.mixins import PermissionRequiredMixin
from django.http import JsonResponse, HttpResponseRedirect
from django.template.loader import render_to_string
from django.urls import reverse
from django.views import View

from apps.core.views import BaseTenantCreateView, BaseTenantListView, BaseTenantUpdateView
from .forms import DepositoForm
from .models import Deposito


class DepositoListView(BaseTenantListView):
    model = Deposito
    template_name = "depositos/list.html"
    form_class = DepositoForm
    title = "Depositos"
    permission_required = "depositos.view_deposito"
    headers = ["Nome", "Endereco", "Planta", "Bloquear negativo", "Ativo"]
    row_fields = ["nome", "endereco", "planta", "bloquear_movimento_negativo", "ativo"]
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
    create_url_name = "depositos:create"
    update_url_name = "depositos:update"

    def get_create_url(self):
        if not self.request.user.has_perm("depositos.add_deposito"):
            return ""
        return super().get_create_url()

    def get_queryset(self):
        queryset = super().get_queryset()
        planta_id = self.request.session.get("planta_id")
        if planta_id:
            queryset = queryset.filter(planta_id=planta_id)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        planta_id = self.request.session.get("planta_id")
        if not self.request.user.has_perm("depositos.add_deposito"):
            context["create_form"] = None
        if not self.request.user.has_perm("depositos.change_deposito"):
            context["edit_rows"] = []
        if context.get("create_form"):
            context["create_form"] = DepositoForm(
                tenant=self.request.tenant,
                planta_id=planta_id,
            )
        if self.request.user.has_perm("depositos.change_deposito"):
            context["edit_rows"] = [
                {
                    "object": obj,
                    "form": DepositoForm(
                        instance=obj,
                        tenant=self.request.tenant,
                        planta_id=planta_id,
                    ),
                    "update_url": reverse("depositos:update", args=[obj.pk]),
                }
                for obj in context["object_list"]
            ]
        return context


class DepositoCreateView(BaseTenantCreateView):
    model = Deposito
    form_class = DepositoForm
    success_url_name = "depositos:list"
    permission_required = "depositos.add_deposito"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["tenant"] = self.request.tenant
        kwargs["planta_id"] = self.request.session.get("planta_id")
        return kwargs

    def form_valid(self, form):
        nome = (form.cleaned_data.get("nome") or "").strip()
        if (
            nome
            and Deposito.objects.filter(company=self.request.tenant, nome__iexact=nome).exists()
        ):
            form.add_error("nome", "Deposito ja cadastrado.")
            return self.form_invalid(form)
        response = super().form_valid(form)
        if self.request.headers.get("X-Requested-With") == "XMLHttpRequest":
            row_html = render_to_string(
                "depositos/_deposito_row.html",
                {"deposito": self.object},
                request=self.request,
            )
            edit_modal_html = render_to_string(
                "depositos/_deposito_edit_modal.html",
                {
                    "deposito": self.object,
                    "form": DepositoForm(
                        instance=self.object,
                        tenant=self.request.tenant,
                        planta_id=self.request.session.get("planta_id"),
                    ),
                    "update_url": reverse("depositos:update", args=[self.object.pk]),
                },
                request=self.request,
            )
            form_html = render_to_string(
                "components/_form.html",
                {
                    "form": DepositoForm(
                        tenant=self.request.tenant,
                        planta_id=self.request.session.get("planta_id"),
                    ),
                    "form_action": reverse("depositos:create"),
                },
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
                {"form": form, "form_action": reverse("depositos:create")},
                request=self.request,
            )
            return JsonResponse({"ok": False, "form_html": form_html}, status=400)
        return super().form_invalid(form)


class DepositoUpdateView(BaseTenantUpdateView):
    model = Deposito
    form_class = DepositoForm
    success_url_name = "depositos:list"
    permission_required = "depositos.change_deposito"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["tenant"] = self.request.tenant
        kwargs["planta_id"] = self.request.session.get("planta_id")
        return kwargs

    def form_valid(self, form):
        nome = (form.cleaned_data.get("nome") or "").strip()
        if (
            nome
            and Deposito.objects.filter(company=self.request.tenant, nome__iexact=nome)
            .exclude(pk=form.instance.pk)
            .exists()
        ):
            form.add_error("nome", "Deposito ja cadastrado.")
            return self.form_invalid(form)
        response = super().form_valid(form)
        if self.request.headers.get("X-Requested-With") == "XMLHttpRequest":
            row_html = render_to_string(
                "depositos/_deposito_row.html",
                {"deposito": self.object},
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
                    "form_action": reverse("depositos:update", args=[self.get_object().pk]),
                },
                request=self.request,
            )
            return JsonResponse(
                {"ok": False, "form_html": form_html, "row_id": self.get_object().pk},
                status=400,
            )
        return super().form_invalid(form)


class DepositoToggleActiveView(PermissionRequiredMixin, View):
    permission_required = "depositos.change_deposito"

    def post(self, request, pk):
        deposito = Deposito.objects.filter(pk=pk, company=request.tenant).first()
        if not deposito:
            return JsonResponse({"ok": False}, status=404)
        deposito.ativo = not deposito.ativo
        deposito.updated_by = request.user
        deposito.save(update_fields=["ativo", "updated_by"])
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            row_html = render_to_string(
                "depositos/_deposito_row.html",
                {"deposito": deposito},
                request=request,
            )
            return JsonResponse({"ok": True, "row_id": deposito.pk, "row_html": row_html})
        return HttpResponseRedirect(reverse("depositos:list"))
