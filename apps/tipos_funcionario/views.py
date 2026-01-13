import json

from django.contrib.auth.mixins import PermissionRequiredMixin
from django.http import JsonResponse, HttpResponseRedirect
from django.template.loader import render_to_string
from django.urls import reverse
from django.views import View

from apps.core.views import BaseTenantCreateView, BaseTenantListView, BaseTenantUpdateView
from apps.funcionarios.models import Funcionario
from .forms import TipoFuncionarioForm, TipoFuncionarioProdutoForm
from .models import TipoFuncionario, TipoFuncionarioProduto


class TipoFuncionarioListView(BaseTenantListView):
    model = TipoFuncionario
    template_name = "tipos_funcionario/list.html"
    form_class = TipoFuncionarioForm
    title = "Tipos de Funcionario"
    headers = ["Nome", "Descricao", "Ativo"]
    row_fields = ["nome", "descricao", "ativo"]
    create_url_name = "tipos_funcionario:create"
    update_url_name = "tipos_funcionario:update"


class TipoFuncionarioCreateView(BaseTenantCreateView):
    model = TipoFuncionario
    form_class = TipoFuncionarioForm
    success_url_name = "tipos_funcionario:list"

    def form_valid(self, form):
        response = super().form_valid(form)
        if self.request.headers.get("X-Requested-With") == "XMLHttpRequest":
            row_html = render_to_string(
                "tipos_funcionario/_tipo_funcionario_row.html",
                {"tipo": self.object},
                request=self.request,
            )
            edit_modal_html = render_to_string(
                "tipos_funcionario/_tipo_funcionario_edit_modal.html",
                {
                    "tipo": self.object,
                    "form": TipoFuncionarioForm(instance=self.object),
                    "update_url": reverse("tipos_funcionario:update", args=[self.object.pk]),
                },
                request=self.request,
            )
            form_html = render_to_string(
                "components/_form.html",
                {"form": TipoFuncionarioForm(), "form_action": reverse("tipos_funcionario:create")},
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
                {"form": form, "form_action": reverse("tipos_funcionario:create")},
                request=self.request,
            )
            return JsonResponse({"ok": False, "form_html": form_html}, status=400)
        return super().form_invalid(form)


class TipoFuncionarioUpdateView(BaseTenantUpdateView):
    model = TipoFuncionario
    form_class = TipoFuncionarioForm
    success_url_name = "tipos_funcionario:list"

    def form_valid(self, form):
        response = super().form_valid(form)
        if self.request.headers.get("X-Requested-With") == "XMLHttpRequest":
            row_html = render_to_string(
                "tipos_funcionario/_tipo_funcionario_row.html",
                {"tipo": self.object},
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
                    "form_action": reverse("tipos_funcionario:update", args=[self.get_object().pk]),
                },
                request=self.request,
            )
            return JsonResponse(
                {"ok": False, "form_html": form_html, "row_id": self.get_object().pk},
                status=400,
            )
        return super().form_invalid(form)


class TipoFuncionarioToggleActiveView(PermissionRequiredMixin, View):
    permission_required = "tipos_funcionario.change_tipofuncionario"

    def post(self, request, pk):
        tipo = TipoFuncionario.objects.filter(pk=pk, company=request.tenant).first()
        if not tipo:
            return JsonResponse({"ok": False}, status=404)
        tipo.ativo = not tipo.ativo
        tipo.updated_by = request.user
        tipo.save(update_fields=["ativo", "updated_by"])
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            row_html = render_to_string(
                "tipos_funcionario/_tipo_funcionario_row.html",
                {"tipo": tipo},
                request=request,
            )
            return JsonResponse({"ok": True, "row_id": tipo.pk, "row_html": row_html})
        return HttpResponseRedirect(reverse("tipos_funcionario:list"))


class TipoFuncionarioDeleteView(PermissionRequiredMixin, View):
    permission_required = "tipos_funcionario.delete_tipofuncionario"

    def post(self, request, pk):
        tipo = TipoFuncionario.objects.filter(pk=pk, company=request.tenant).first()
        if not tipo:
            return JsonResponse({"ok": False}, status=404)
        funcionarios = list(
            Funcionario.objects.filter(company=request.tenant, tipo=tipo)
            .values("id", "nome")
            .distinct()
        )
        if funcionarios:
            return JsonResponse(
                {"ok": False, "blocked": True, "funcionarios": funcionarios, "row_id": tipo.pk},
                status=400,
            )
        tipo.delete()
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({"ok": True, "row_id": pk})
        return HttpResponseRedirect(reverse("tipos_funcionario:list"))


class TipoFuncionarioUsoView(PermissionRequiredMixin, View):
    permission_required = "tipos_funcionario.view_tipofuncionario"

    def get(self, request, pk):
        tipo = TipoFuncionario.objects.filter(pk=pk, company=request.tenant).first()
        if not tipo:
            return JsonResponse({"ok": False}, status=404)
        funcionarios = list(
            Funcionario.objects.filter(company=request.tenant, tipo=tipo)
            .values("id", "nome")
            .distinct()
        )
        return JsonResponse({"ok": True, "funcionarios": funcionarios})


class TipoFuncionarioProdutoListView(BaseTenantListView):
    model = TipoFuncionarioProduto
    template_name = "tipos_funcionario/produtos_list.html"
    form_class = TipoFuncionarioProdutoForm
    title = "Produtos por tipo de funcionario"
    headers = ["Tipo de funcionario", "Produto / CA", "Fornecedor"]
    row_fields = ["tipo_funcionario", "produto_fornecedor", "produto_fornecedor.fornecedor"]
    filter_definitions = [
        {"name": "tipo_funcionario__nome", "label": "Tipo", "lookup": "icontains", "type": "text"},
        {"name": "produto_fornecedor__produto__nome", "label": "Produto", "lookup": "icontains", "type": "text"},
    ]
    create_url_name = "tipos_funcionario:produtos_create"
    update_url_name = "tipos_funcionario:produtos_update"

    def get_queryset(self):
        return super().get_queryset().select_related(
            "tipo_funcionario",
            "produto_fornecedor__produto",
            "produto_fornecedor__fornecedor",
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.form_class:
            if context.get("can_add"):
                context["create_form"] = self.form_class(tenant=self.request.tenant)
            else:
                context["create_form"] = None
            if context.get("can_change"):
                context["edit_rows"] = [
                    {
                        "object": obj,
                        "form": self.form_class(instance=obj, tenant=self.request.tenant),
                        "update_url": reverse(self.update_url_name, args=[obj.pk]),
                    }
                    for obj in context.get("object_list", [])
                ]
            else:
                context["edit_rows"] = []
        return context


class TipoFuncionarioProdutoCreateView(BaseTenantCreateView):
    model = TipoFuncionarioProduto
    form_class = TipoFuncionarioProdutoForm
    success_url_name = "tipos_funcionario:produtos_list"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["tenant"] = self.request.tenant
        return kwargs

    def _parse_items_payload(self, payload):
        try:
            data = json.loads(payload)
        except json.JSONDecodeError:
            return None, "Itens invalidos."
        if not isinstance(data, list):
            return None, "Itens invalidos."
        items = []
        for item in data:
            if not isinstance(item, dict):
                return None, "Itens invalidos."
            items.append(item)
        return items, None

    def _validate_and_create_items(self, items, form):
        errors = []
        created = []
        seen = set()

        for idx, item in enumerate(items, start=1):
            tipo_id = item.get("tipo_funcionario_id")
            produto_fornecedor_id = item.get("produto_fornecedor_id")
            if not tipo_id or not produto_fornecedor_id:
                errors.append(f"Item {idx}: selecione o tipo e o produto.")
                continue
            key = (int(tipo_id), int(produto_fornecedor_id))
            if key in seen:
                errors.append(f"Item {idx}: duplicado na lista.")
                continue
            seen.add(key)
            exists = TipoFuncionarioProduto.objects.filter(
                company=self.request.tenant,
                tipo_funcionario_id=tipo_id,
                produto_fornecedor_id=produto_fornecedor_id,
            ).exists()
            if exists:
                errors.append(f"Item {idx}: vinculo ja cadastrado.")
                continue
            created.append(
                TipoFuncionarioProduto(
                    company=self.request.tenant,
                    tipo_funcionario_id=tipo_id,
                    produto_fornecedor_id=produto_fornecedor_id,
                    created_by=self.request.user,
                    updated_by=self.request.user,
                )
            )

        if errors:
            for error in errors:
                form.add_error(None, error)
            return None

        TipoFuncionarioProduto.objects.bulk_create(created)
        return created

    def post(self, request, *args, **kwargs):
        payload = request.POST.get("itens_payload")
        if payload:
            form = self.get_form()
            items, error = self._parse_items_payload(payload)
            if error:
                form.add_error(None, error)
                return self.form_invalid(form)
            created = self._validate_and_create_items(items, form)
            if not created:
                return self.form_invalid(form)
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                row_html = "".join(
                    render_to_string(
                        "tipos_funcionario/_tipo_funcionario_produto_row.html",
                        {"vinculo": obj},
                        request=request,
                    )
                    for obj in created
                )
                form_html = render_to_string(
                    "components/_form.html",
                    {
                        "form": self.form_class(tenant=self.request.tenant),
                        "form_action": reverse("tipos_funcionario:produtos_create"),
                    },
                    request=request,
                )
                return JsonResponse(
                    {
                        "ok": True,
                        "action": "create",
                        "row_ids": [obj.pk for obj in created],
                        "row_html": row_html,
                        "form_html": form_html,
                    }
                )
            return HttpResponseRedirect(self.get_success_url())
        return super().post(request, *args, **kwargs)

    def form_valid(self, form):
        response = super().form_valid(form)
        if self.request.headers.get("X-Requested-With") == "XMLHttpRequest":
            row_html = render_to_string(
                "tipos_funcionario/_tipo_funcionario_produto_row.html",
                {"vinculo": self.object},
                request=self.request,
            )
            edit_modal_html = render_to_string(
                "tipos_funcionario/_tipo_funcionario_produto_edit_modal.html",
                {
                    "vinculo": self.object,
                    "form": TipoFuncionarioProdutoForm(instance=self.object, tenant=self.request.tenant),
                    "update_url": reverse("tipos_funcionario:produtos_update", args=[self.object.pk]),
                },
                request=self.request,
            )
            form_html = render_to_string(
                "components/_form.html",
                {
                    "form": TipoFuncionarioProdutoForm(tenant=self.request.tenant),
                    "form_action": reverse("tipos_funcionario:produtos_create"),
                    "form_hide_actions": True,
                    "form_id": "tipo-produto-form",
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
                {
                    "form": form,
                    "form_action": reverse("tipos_funcionario:produtos_create"),
                    "form_hide_actions": True,
                    "form_id": "tipo-produto-form",
                },
                request=self.request,
            )
            return JsonResponse({"ok": False, "form_html": form_html}, status=400)
        return super().form_invalid(form)


class TipoFuncionarioProdutoUpdateView(BaseTenantUpdateView):
    model = TipoFuncionarioProduto
    form_class = TipoFuncionarioProdutoForm
    success_url_name = "tipos_funcionario:produtos_list"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["tenant"] = self.request.tenant
        return kwargs

    def form_valid(self, form):
        response = super().form_valid(form)
        if self.request.headers.get("X-Requested-With") == "XMLHttpRequest":
            row_html = render_to_string(
                "tipos_funcionario/_tipo_funcionario_produto_row.html",
                {"vinculo": self.object},
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
                    "form_action": reverse("tipos_funcionario:produtos_update", args=[self.get_object().pk]),
                },
                request=self.request,
            )
            return JsonResponse(
                {"ok": False, "form_html": form_html, "row_id": self.get_object().pk},
                status=400,
            )
        return super().form_invalid(form)


class TipoFuncionarioProdutoDeleteView(PermissionRequiredMixin, View):
    permission_required = "tipos_funcionario.delete_tipofuncionarioproduto"

    def post(self, request, pk):
        vinculo = TipoFuncionarioProduto.objects.filter(pk=pk, company=request.tenant).first()
        if not vinculo:
            return JsonResponse({"ok": False}, status=404)
        vinculo.delete()
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({"ok": True, "row_id": pk})
        return HttpResponseRedirect(reverse("tipos_funcionario:produtos_list"))
