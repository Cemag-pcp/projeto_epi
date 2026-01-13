from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.http import JsonResponse
from django.template.loader import render_to_string
from django.urls import reverse, reverse_lazy

from apps.core.views import BaseTenantCreateView, BaseTenantListView, BaseTenantUpdateView
from .forms import AcessoEPIForm, ConsumoParceiroForm, EmpresaParceiraForm, TerceiroForm
from .models import AcessoEPI, ConsumoParceiro, EmpresaParceira, Terceiro


@login_required
@require_GET
def terceiros_por_empresa(request):
    empresa_id = request.GET.get("empresa_id")
    qs = Terceiro.objects.filter(company=request.tenant, ativo=True).order_by("nome")
    if empresa_id:
        qs = qs.filter(empresa_parceira_id=empresa_id)
    else:
        qs = qs.none()
    data = [{"id": terceiro.pk, "label": str(terceiro)} for terceiro in qs]
    return JsonResponse({"items": data})


class EmpresaParceiraListView(BaseTenantListView):
    model = EmpresaParceira
    template_name = "acessos/empresas_list.html"
    form_class = EmpresaParceiraForm
    title = "Empresas parceiras"
    subtitle = "Cadastre empresas parceiras para consumo e acesso."
    headers = ["Nome", "Documento", "Contato", "Ativo"]
    row_fields = ["nome", "documento", "contato", "ativo"]
    filter_definitions = [
        {"name": "nome", "label": "Nome", "lookup": "icontains", "type": "text"},
        {"name": "documento", "label": "Documento", "lookup": "icontains", "type": "text"},
    ]
    create_url_name = "acessos:empresas_create"
    update_url_name = "acessos:empresas_update"


class EmpresaParceiraCreateView(BaseTenantCreateView):
    model = EmpresaParceira
    form_class = EmpresaParceiraForm
    success_url_name = "acessos:empresas_list"

    def form_valid(self, form):
        response = super().form_valid(form)
        if self.request.headers.get("X-Requested-With") == "XMLHttpRequest":
            row_html = render_to_string(
                "acessos/_empresa_row.html",
                {"empresa": self.object, "row_fields": EmpresaParceiraListView.row_fields},
                request=self.request,
            )
            edit_modal_html = render_to_string(
                "acessos/_empresa_edit_modal.html",
                {
                    "empresa": self.object,
                    "form": EmpresaParceiraForm(instance=self.object),
                    "update_url": reverse("acessos:empresas_update", args=[self.object.pk]),
                },
                request=self.request,
            )
            form_html = render_to_string(
                "components/_form.html",
                {
                    "form": EmpresaParceiraForm(),
                    "form_action": reverse("acessos:empresas_create"),
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
                {"form": form, "form_action": reverse("acessos:empresas_create")},
                request=self.request,
            )
            return JsonResponse({"ok": False, "form_html": form_html}, status=400)
        return super().form_invalid(form)


class EmpresaParceiraUpdateView(BaseTenantUpdateView):
    model = EmpresaParceira
    form_class = EmpresaParceiraForm
    success_url_name = "acessos:empresas_list"

    def form_valid(self, form):
        response = super().form_valid(form)
        if self.request.headers.get("X-Requested-With") == "XMLHttpRequest":
            row_html = render_to_string(
                "acessos/_empresa_row.html",
                {"empresa": self.object, "row_fields": EmpresaParceiraListView.row_fields},
                request=self.request,
            )
            return JsonResponse(
                {"ok": True, "action": "update", "row_id": self.object.pk, "row_html": row_html}
            )
        return response

    def form_invalid(self, form):
        if self.request.headers.get("X-Requested-With") == "XMLHttpRequest":
            form_html = render_to_string(
                "components/_form.html",
                {
                    "form": form,
                    "form_action": reverse("acessos:empresas_update", args=[self.get_object().pk]),
                },
                request=self.request,
            )
            return JsonResponse(
                {"ok": False, "form_html": form_html, "row_id": self.get_object().pk},
                status=400,
            )
        return super().form_invalid(form)


class TerceiroListView(BaseTenantListView):
    model = Terceiro
    form_class = TerceiroForm
    title = "Terceiros"
    subtitle = "Cadastre terceiros vinculados a empresas parceiras."
    headers = ["Nome", "Documento", "Empresa", "Telefone", "Ativo"]
    row_fields = ["nome", "documento", "empresa_parceira", "telefone", "ativo"]
    filter_definitions = [
        {"name": "nome", "label": "Nome", "lookup": "icontains", "type": "text"},
        {"name": "empresa_parceira__nome", "label": "Empresa", "lookup": "icontains", "type": "text"},
    ]
    create_url_name = "acessos:terceiros_create"
    update_url_name = "acessos:terceiros_update"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if context.get("can_add"):
            context["create_form"] = TerceiroForm(tenant=self.request.tenant)
        else:
            context["create_form"] = None
        if context.get("can_change"):
            context["edit_rows"] = [
                {
                    "object": obj,
                    "form": TerceiroForm(instance=obj, tenant=self.request.tenant),
                    "update_url": reverse_lazy(self.update_url_name, args=[obj.pk]),
                }
                for obj in context.get("object_list", [])
            ]
        else:
            context["edit_rows"] = []
        return context


class TerceiroCreateView(BaseTenantCreateView):
    model = Terceiro
    form_class = TerceiroForm
    success_url_name = "acessos:terceiros_list"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["tenant"] = self.request.tenant
        return kwargs


class TerceiroUpdateView(BaseTenantUpdateView):
    model = Terceiro
    form_class = TerceiroForm
    success_url_name = "acessos:terceiros_list"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["tenant"] = self.request.tenant
        return kwargs


class AcessoEPIListView(BaseTenantListView):
    model = AcessoEPI
    template_name = "acessos/acessos_list.html"
    form_class = AcessoEPIForm
    title = "Acessos de EPI"
    subtitle = "Registre acessos de funcionarios e terceiros."
    headers = ["Pessoa", "Tipo", "Planta", "Data/Hora", "EPI", "Treinamento", "Permitido"]
    row_fields = [
        "identificacao_label",
        "tipo_pessoa",
        "planta",
        "data_hora_label",
        "status_epi_label",
        "status_treinamento_label",
        "permitido",
    ]
    filter_definitions = [
        {
            "name": "tipo_pessoa",
            "label": "Tipo",
            "lookup": "exact",
            "type": "select",
            "options": [("", "Todos")] + list(AcessoEPI.TIPO_PESSOA_CHOICES),
        },
    ]
    create_url_name = "acessos:acessos_create"
    update_url_name = "acessos:acessos_update"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if context.get("can_add"):
            context["create_form"] = AcessoEPIForm(tenant=self.request.tenant)
        else:
            context["create_form"] = None
        if context.get("can_change"):
            context["edit_rows"] = [
                {
                    "object": obj,
                    "form": AcessoEPIForm(instance=obj, tenant=self.request.tenant),
                    "update_url": reverse_lazy(self.update_url_name, args=[obj.pk]),
                }
                for obj in context.get("object_list", [])
            ]
        else:
            context["edit_rows"] = []
        return context


class AcessoEPICreateView(BaseTenantCreateView):
    model = AcessoEPI
    form_class = AcessoEPIForm
    success_url_name = "acessos:acessos_list"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["tenant"] = self.request.tenant
        return kwargs

    def form_valid(self, form):
        response = super().form_valid(form)
        if self.request.headers.get("X-Requested-With") == "XMLHttpRequest":
            row_html = render_to_string(
                "acessos/_acesso_row.html",
                {"acesso": self.object, "row_fields": AcessoEPIListView.row_fields},
                request=self.request,
            )
            edit_modal_html = render_to_string(
                "acessos/_acesso_edit_modal.html",
                {
                    "acesso": self.object,
                    "form": AcessoEPIForm(instance=self.object, tenant=self.request.tenant),
                    "update_url": reverse("acessos:acessos_update", args=[self.object.pk]),
                },
                request=self.request,
            )
            form_html = render_to_string(
                "components/_form.html",
                {
                    "form": AcessoEPIForm(tenant=self.request.tenant),
                    "form_action": reverse("acessos:acessos_create"),
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
                {"form": form, "form_action": reverse("acessos:acessos_create")},
                request=self.request,
            )
            return JsonResponse({"ok": False, "form_html": form_html}, status=400)
        return super().form_invalid(form)


class AcessoEPIUpdateView(BaseTenantUpdateView):
    model = AcessoEPI
    form_class = AcessoEPIForm
    success_url_name = "acessos:acessos_list"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["tenant"] = self.request.tenant
        return kwargs

    def form_valid(self, form):
        response = super().form_valid(form)
        if self.request.headers.get("X-Requested-With") == "XMLHttpRequest":
            row_html = render_to_string(
                "acessos/_acesso_row.html",
                {"acesso": self.object, "row_fields": AcessoEPIListView.row_fields},
                request=self.request,
            )
            return JsonResponse(
                {"ok": True, "action": "update", "row_id": self.object.pk, "row_html": row_html}
            )
        return response

    def form_invalid(self, form):
        if self.request.headers.get("X-Requested-With") == "XMLHttpRequest":
            form_html = render_to_string(
                "components/_form.html",
                {
                    "form": form,
                    "form_action": reverse("acessos:acessos_update", args=[self.get_object().pk]),
                },
                request=self.request,
            )
            return JsonResponse(
                {"ok": False, "form_html": form_html, "row_id": self.get_object().pk},
                status=400,
            )
        return super().form_invalid(form)


class ConsumoParceiroListView(BaseTenantListView):
    model = ConsumoParceiro
    template_name = "acessos/consumos_list.html"
    form_class = ConsumoParceiroForm
    title = "Consumo de empresas parceiras"
    subtitle = "Registre consumo de EPIs por empresas parceiras."
    headers = ["Terceiro", "Empresa", "Produto", "Quantidade", "Data", "Observacao"]
    row_fields = ["terceiro", "empresa_parceira_label", "produto", "quantidade", "data", "observacao"]
    filter_definitions = [
        {"name": "terceiro__nome", "label": "Terceiro", "lookup": "icontains", "type": "text"},
        {
            "name": "terceiro__empresa_parceira__nome",
            "label": "Empresa",
            "lookup": "icontains",
            "type": "text",
        },
        {"name": "produto__nome", "label": "Produto", "lookup": "icontains", "type": "text"},
    ]
    create_url_name = "acessos:consumos_create"
    update_url_name = "acessos:consumos_update"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if context.get("can_add"):
            context["create_form"] = ConsumoParceiroForm(tenant=self.request.tenant)
        else:
            context["create_form"] = None
        if context.get("can_change"):
            context["edit_rows"] = [
                {
                    "object": obj,
                    "form": ConsumoParceiroForm(instance=obj, tenant=self.request.tenant),
                    "update_url": reverse_lazy(self.update_url_name, args=[obj.pk]),
                }
                for obj in context.get("object_list", [])
            ]
        else:
            context["edit_rows"] = []
        return context

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if context.get("can_add"):
            context["create_form"] = ConsumoParceiroForm(tenant=self.request.tenant)
        else:
            context["create_form"] = None
        if context.get("can_change"):
            context["edit_rows"] = [
                {
                    "object": obj,
                    "form": ConsumoParceiroForm(instance=obj, tenant=self.request.tenant),
                    "update_url": reverse_lazy(self.update_url_name, args=[obj.pk]),
                }
                for obj in context.get("object_list", [])
            ]
        else:
            context["edit_rows"] = []
        return context


class ConsumoParceiroCreateView(BaseTenantCreateView):
    model = ConsumoParceiro
    form_class = ConsumoParceiroForm
    success_url_name = "acessos:consumos_list"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["tenant"] = self.request.tenant
        return kwargs

    def form_valid(self, form):
        response = super().form_valid(form)
        if self.request.headers.get("X-Requested-With") == "XMLHttpRequest":
            row_html = render_to_string(
                "acessos/_consumo_row.html",
                {"consumo": self.object, "row_fields": ConsumoParceiroListView.row_fields},
                request=self.request,
            )
            edit_modal_html = render_to_string(
                "acessos/_consumo_edit_modal.html",
                {
                    "consumo": self.object,
                    "form": ConsumoParceiroForm(instance=self.object, tenant=self.request.tenant),
                    "update_url": reverse("acessos:consumos_update", args=[self.object.pk]),
                },
                request=self.request,
            )
            form_html = render_to_string(
                "components/_form.html",
                {
                    "form": ConsumoParceiroForm(tenant=self.request.tenant),
                    "form_action": reverse("acessos:consumos_create"),
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
                {"form": form, "form_action": reverse("acessos:consumos_create")},
                request=self.request,
            )
            return JsonResponse({"ok": False, "form_html": form_html}, status=400)
        return super().form_invalid(form)


class ConsumoParceiroUpdateView(BaseTenantUpdateView):
    model = ConsumoParceiro
    form_class = ConsumoParceiroForm
    success_url_name = "acessos:consumos_list"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["tenant"] = self.request.tenant
        return kwargs

    def form_valid(self, form):
        response = super().form_valid(form)
        if self.request.headers.get("X-Requested-With") == "XMLHttpRequest":
            row_html = render_to_string(
                "acessos/_consumo_row.html",
                {"consumo": self.object, "row_fields": ConsumoParceiroListView.row_fields},
                request=self.request,
            )
            return JsonResponse(
                {"ok": True, "action": "update", "row_id": self.object.pk, "row_html": row_html}
            )
        return response

    def form_invalid(self, form):
        if self.request.headers.get("X-Requested-With") == "XMLHttpRequest":
            form_html = render_to_string(
                "components/_form.html",
                {
                    "form": form,
                    "form_action": reverse("acessos:consumos_update", args=[self.get_object().pk]),
                },
                request=self.request,
            )
            return JsonResponse(
                {"ok": False, "form_html": form_html, "row_id": self.get_object().pk},
                status=400,
            )
        return super().form_invalid(form)
