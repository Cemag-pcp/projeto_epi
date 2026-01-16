import re
from datetime import date
from decimal import Decimal, InvalidOperation

from django.contrib.auth.mixins import PermissionRequiredMixin
from django.db import transaction
from django.db.models import Avg, OuterRef, Subquery
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.views import View
from django.core.paginator import InvalidPage, Paginator
from django.db.models import Q

from django_tenants.utils import schema_context

from apps.core.views import BaseTenantCreateView, BaseTenantListView, BaseTenantUpdateView
from apps.caepi.models import CaEPI
from apps.fornecedores.models import Fornecedor
from .forms import (
    FamiliaProdutoForm,
    LocalizacaoProdutoForm,
    LocalRetiradaForm,
    PeriodicidadeForm,
    ProdutoForm,
    SubfamiliaProdutoForm,
    TipoProdutoForm,
)
from .models import (
    FamiliaProduto,
    LocalizacaoProduto,
    LocalRetirada,
    Periodicidade,
    Produto,
    ProdutoAnexo,
    ProdutoFornecedor,
    SubfamiliaProduto,
    TipoProduto,
)
from apps.estoque.models import ActionLog, MovimentacaoEstoque


class ProdutoListView(BaseTenantListView):
    model = Produto
    template_name = "produtos/list.html"
    form_class = ProdutoForm
    paginate_by = 10
    title = "Produtos"
    headers = [
        "CA",
        "Codigo",
        "Descricao",
        "Referencia",
        "Qtde a entregar",
        "Periodicidade",
        "Unidade",
        "Valor medio",
        "Ativo",
    ]
    row_fields = [
        "ca_fornecedor",
        "codigo_externo",
        "nome",
        "referencia",
        "estoque_ideal",
        "periodicidade_label",
        "unidade",
        "valor_medio",
        "ativo",
    ]
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
    create_url_name = "produtos:create"
    update_url_name = "produtos:update"

    def get(self, request, *args, **kwargs):
        if request.headers.get("X-Requested-With") != "XMLHttpRequest":
            return super().get(request, *args, **kwargs)
        self.object_list = self.get_queryset()
        context = self.get_context_data()
        rows_html = render_to_string(
            "produtos/_produto_rows.html",
            {"object_list": context.get("object_list", []), "headers": self.headers},
            request=request,
        )
        modals_html = render_to_string(
            "produtos/_produto_modals.html",
            {"edit_rows": context.get("edit_rows", [])},
            request=request,
        )
        pagination_html = render_to_string(
            "components/_pagination.html",
            {"page_obj": context.get("page_obj")},
            request=request,
        )
        return JsonResponse(
            {
                "ok": True,
                "rows_html": rows_html,
                "modals_html": modals_html,
                "pagination_html": pagination_html,
            }
        )

    def get_queryset(self):
        queryset = super().get_queryset()
        ca_subquery = (
            ProdutoFornecedor.objects.filter(produto=OuterRef("pk"))
            .exclude(ca="")
            .values("ca")[:1]
        )
        return queryset.annotate(
            ca_fornecedor=Subquery(ca_subquery),
            valor_medio=Avg("fornecedores_rel__valor"),
        )


class ProdutoFornecedorAnexoMixin:
    def _get_annotated_produto(self, produto_id):
        ca_subquery = (
            ProdutoFornecedor.objects.filter(produto=OuterRef("pk"))
            .exclude(ca="")
            .values("ca")[:1]
        )
        return (
            Produto.objects.filter(pk=produto_id)
            .annotate(
                ca_fornecedor=Subquery(ca_subquery),
                valor_medio=Avg("fornecedores_rel__valor"),
            )
            .get()
        )

    def _parse_indexed_data(self, prefix, data):
        pattern = re.compile(rf"^{re.escape(prefix)}\[(\d+)\]\[([^\]]+)\]$")
        grouped = {}
        for key, value in data.items():
            match = pattern.match(key)
            if not match:
                continue
            index = int(match.group(1))
            field = match.group(2)
            grouped.setdefault(index, {})[field] = value
        return grouped

    def _parse_decimal(self, raw_value, field_label, errors, row_index):
        value = (raw_value or "").strip()
        if not value:
            return None
        try:
            return Decimal(value.replace(",", "."))
        except InvalidOperation:
            errors.append(f"{field_label} invalido na linha {row_index}.")
            return None

    def _save_fornecedores(self, produto, errors, replace=False):
        fornecedores_data = self._parse_indexed_data("fornecedores", self.request.POST)
        fornecedores_to_create = []
        for index in sorted(fornecedores_data.keys()):
            fields = fornecedores_data[index]
            cleaned = {key: (value or "").strip() for key, value in fields.items()}
            if not any(cleaned.values()):
                continue
            fornecedor_id = cleaned.get("fornecedor")
            if not fornecedor_id:
                errors.append(f"Fornecedor obrigatorio na linha {index + 1}.")
                continue
            valor_raw = cleaned.get("valor")
            valor = None
            if valor_raw and valor_raw.strip():
                valor = self._parse_decimal(valor_raw, "Valor", errors, index + 1)
                # Valor invalido ja gera erro em _parse_decimal
                if valor is None:
                    continue
            fator_compra = self._parse_decimal(cleaned.get("fator_compra"), "Fator de compra", errors, index + 1)
            fornecedores_to_create.append(
                ProdutoFornecedor(
                    produto=produto,
                    fornecedor_id=fornecedor_id,
                    company=self.request.tenant,
                    created_by=self.request.user,
                    updated_by=self.request.user,
                    ca=cleaned.get("ca", ""),
                    codigo_barras=cleaned.get("codigo_barras", ""),
                    codigo_fornecedor=cleaned.get("codigo_fornecedor", ""),
                    valor=valor,
                    fator_compra=fator_compra if fator_compra is not None else Decimal("1"),
                )
            )
        if errors:
            return
        if replace:
            ProdutoFornecedor.objects.filter(produto=produto).delete()
        if fornecedores_to_create:
            ProdutoFornecedor.objects.bulk_create(fornecedores_to_create)

    def _save_anexos(self, produto, errors, replace=False):
        anexos_data = self._parse_indexed_data("anexos", self.request.POST)
        indices = set(anexos_data.keys())
        for key in self.request.FILES.keys():
            match = re.match(r"^anexos\[(\d+)\]\[arquivo\]$", key)
            if match:
                indices.add(int(match.group(1)))
        existing = {}
        if replace:
            existing = {anexo.pk: anexo for anexo in produto.anexos.all()}
        seen_ids = set()
        for index in sorted(indices):
            fields = anexos_data.get(index, {})
            descricao = (fields.get("descricao") or "").strip()
            anexo_id = (fields.get("id") or "").strip()
            arquivo = self.request.FILES.get(f"anexos[{index}][arquivo]")
            if not arquivo and not descricao and not anexo_id:
                continue
            if anexo_id:
                try:
                    anexo_id_int = int(anexo_id)
                except ValueError:
                    errors.append(f"Anexo invalido na linha {index + 1}.")
                    continue
                seen_ids.add(anexo_id_int)
                anexo = existing.get(anexo_id_int)
                if not anexo:
                    continue
                if arquivo:
                    anexo.arquivo = arquivo
                anexo.descricao = descricao
                anexo.updated_by = self.request.user
                anexo.save()
                continue
            if not arquivo:
                errors.append(f"Arquivo obrigatorio no anexo {index + 1}.")
                continue
            ProdutoAnexo.objects.create(
                produto=produto,
                arquivo=arquivo,
                descricao=descricao,
                company=self.request.tenant,
                created_by=self.request.user,
                updated_by=self.request.user,
            )
        if replace and existing:
            for anexo_id, anexo in existing.items():
                if anexo_id not in seen_ids:
                    anexo.delete()

    def _assign_tenant_fields(self, form):
        if getattr(form.instance, "company_id", None) is None:
            form.instance.company = self.request.tenant
        if getattr(form.instance, "created_by_id", None) is None:
            form.instance.created_by = self.request.user
        form.instance.updated_by = self.request.user


class ProdutoCreateView(ProdutoFornecedorAnexoMixin, BaseTenantCreateView):
    model = Produto
    form_class = ProdutoForm
    success_url_name = "produtos:list"

    def form_valid(self, form):
        errors = []
        try:
            with transaction.atomic():
                self._assign_tenant_fields(form)
                self.object = form.save()
                self._save_fornecedores(self.object, errors)
                self._save_anexos(self.object, errors)
                if errors:
                    raise ValueError("produto_create_errors")
                ActionLog.objects.create(
                    company=self.request.tenant,
                    actor=self.request.user,
                    action="produto_criado",
                    reference=f"Produto:{self.object.pk}",
                )
        except ValueError:
            for error in errors:
                form.add_error(None, error)
            return self.form_invalid(form)
        if self.request.headers.get("X-Requested-With") == "XMLHttpRequest":
            produto = self._get_annotated_produto(self.object.pk)
            row_html = render_to_string(
                "produtos/_produto_row.html",
                {"produto": produto},
                request=self.request,
            )
            edit_modal_html = render_to_string(
                "produtos/_produto_modal_form.html",
                {
                    "modal_id": f"editModal-{produto.pk}",
                    "modal_label_id": f"editModalLabel-{produto.pk}",
                    "modal_title": "Editar",
                    "form": ProdutoForm(instance=produto),
                    "form_action": reverse("produtos:update", args=[produto.pk]),
                    "prefix": f"edit-{produto.pk}",
                    "fornecedores": produto.fornecedores_rel.all(),
                    "anexos": produto.anexos.all(),
                },
                request=self.request,
            )
            create_modal_html = render_to_string(
                "produtos/_produto_modal_form.html",
                {
                    "modal_id": "createModal",
                    "modal_label_id": "createModalLabel",
                    "modal_title": "Novo produto",
                    "form": ProdutoForm(),
                    "form_action": reverse("produtos:create"),
                    "prefix": "create",
                    "fornecedores": None,
                    "anexos": None,
                },
                request=self.request,
            )
            return JsonResponse(
                {
                    "ok": True,
                    "action": "create",
                    "row_id": produto.pk,
                    "row_html": row_html,
                    "edit_modal_html": edit_modal_html,
                    "create_modal_html": create_modal_html,
                }
            )
        return HttpResponseRedirect(self.get_success_url())

    def form_invalid(self, form):
        if self.request.headers.get("X-Requested-With") == "XMLHttpRequest":
            modal_html = render_to_string(
                "produtos/_produto_modal_form.html",
                {
                    "modal_id": "createModal",
                    "modal_label_id": "createModalLabel",
                    "modal_title": "Novo produto",
                    "form": form,
                    "form_action": self.request.path,
                    "prefix": "create",
                    "fornecedores": None,
                    "anexos": None,
                    },
                request=self.request,
            )
            return JsonResponse({"ok": False, "form_html": modal_html}, status=200)
        return super().form_invalid(form)


class ProdutoUpdateView(ProdutoFornecedorAnexoMixin, BaseTenantUpdateView):
    model = Produto
    form_class = ProdutoForm
    success_url_name = "produtos:list"

    def form_valid(self, form):
        errors = []
        try:
            with transaction.atomic():
                self._assign_tenant_fields(form)
                self.object = form.save()
                self._save_fornecedores(self.object, errors, replace=True)
                self._save_anexos(self.object, errors, replace=True)
                if errors:
                    raise ValueError("produto_update_errors")
                ActionLog.objects.create(
                    company=self.request.tenant,
                    actor=self.request.user,
                    action="produto_atualizado",
                    reference=f"Produto:{self.object.pk}",
                )
        except ValueError:
            for error in errors:
                form.add_error(None, error)
            return self.form_invalid(form)
        if self.request.headers.get("X-Requested-With") == "XMLHttpRequest":
            produto = self._get_annotated_produto(self.object.pk)
            row_html = render_to_string(
                "produtos/_produto_row.html",
                {"produto": produto},
                request=self.request,
            )
            edit_modal_html = render_to_string(
                "produtos/_produto_modal_form.html",
                {
                    "modal_id": f"editModal-{produto.pk}",
                    "modal_label_id": f"editModalLabel-{produto.pk}",
                    "modal_title": "Editar",
                    "form": ProdutoForm(instance=produto),
                    "form_action": self.request.path,
                    "prefix": f"edit-{produto.pk}",
                    "fornecedores": produto.fornecedores_rel.all(),
                    "anexos": produto.anexos.all(),
                },
                request=self.request,
            )
            return JsonResponse(
                {
                    "ok": True,
                    "action": "update",
                    "row_id": produto.pk,
                    "row_html": row_html,
                    "edit_modal_html": edit_modal_html,
                }
            )
        return HttpResponseRedirect(self.get_success_url())

    def form_invalid(self, form):
        if self.request.headers.get("X-Requested-With") == "XMLHttpRequest":
            produto = form.instance
            modal_html = render_to_string(
                "produtos/_produto_modal_form.html",
                {
                    "modal_id": f"editModal-{produto.pk}",
                    "modal_label_id": f"editModalLabel-{produto.pk}",
                    "modal_title": "Editar",
                    "form": form,
                    "form_action": self.request.path,
                    "prefix": f"edit-{produto.pk}",
                    "fornecedores": produto.fornecedores_rel.all(),
                    "anexos": produto.anexos.all(),
                },
                request=self.request,
            )
            return JsonResponse({"ok": False, "form_html": modal_html}, status=200)
        return super().form_invalid(form)


class TipoProdutoListView(BaseTenantListView):
    model = TipoProduto
    template_name = "produtos/tipos_list.html"
    form_class = TipoProdutoForm
    title = "Tipos de Produto"
    headers = ["Nome", "Ativo"]
    row_fields = ["nome", "ativo"]
    create_url_name = "produtos:tipos_create"
    update_url_name = "produtos:tipos_update"


class TipoProdutoCreateView(BaseTenantCreateView):
    model = TipoProduto
    form_class = TipoProdutoForm
    success_url_name = "produtos:tipos_list"

    def form_valid(self, form):
        response = super().form_valid(form)
        if self.request.headers.get("X-Requested-With") == "XMLHttpRequest":
            row_html = render_to_string(
                "produtos/_tipo_produto_row.html",
                {"tipo": self.object},
                request=self.request,
            )
            edit_modal_html = render_to_string(
                "produtos/_tipo_produto_edit_modal.html",
                {
                    "tipo": self.object,
                    "form": TipoProdutoForm(instance=self.object),
                    "update_url": reverse("produtos:tipos_update", args=[self.object.pk]),
                },
                request=self.request,
            )
            form_html = render_to_string(
                "components/_form.html",
                {"form": TipoProdutoForm(), "form_action": reverse("produtos:tipos_create")},
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
                {"form": form, "form_action": reverse("produtos:tipos_create")},
                request=self.request,
            )
            return JsonResponse({"ok": False, "form_html": form_html}, status=400)
        return super().form_invalid(form)


class TipoProdutoUpdateView(BaseTenantUpdateView):
    model = TipoProduto
    form_class = TipoProdutoForm
    success_url_name = "produtos:tipos_list"

    def form_valid(self, form):
        response = super().form_valid(form)
        if self.request.headers.get("X-Requested-With") == "XMLHttpRequest":
            row_html = render_to_string(
                "produtos/_tipo_produto_row.html",
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
                    "form_action": reverse("produtos:tipos_update", args=[self.get_object().pk]),
                },
                request=self.request,
            )
            return JsonResponse(
                {"ok": False, "form_html": form_html, "row_id": self.get_object().pk},
                status=400,
            )
        return super().form_invalid(form)


class TipoProdutoToggleActiveView(PermissionRequiredMixin, View):
    permission_required = "produtos.change_tipoproduto"

    def post(self, request, pk):
        tipo = TipoProduto.objects.filter(pk=pk, company=request.tenant).first()
        if not tipo:
            return JsonResponse({"ok": False}, status=404)
        tipo.ativo = not tipo.ativo
        tipo.updated_by = request.user
        tipo.save(update_fields=["ativo", "updated_by"])
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            row_html = render_to_string(
                "produtos/_tipo_produto_row.html",
                {"tipo": tipo},
                request=request,
            )
            return JsonResponse({"ok": True, "row_id": tipo.pk, "row_html": row_html})
        return HttpResponseRedirect(reverse("produtos:tipos_list"))


class TipoProdutoDeleteView(PermissionRequiredMixin, View):
    permission_required = "produtos.delete_tipoproduto"

    def post(self, request, pk):
        tipo = TipoProduto.objects.filter(pk=pk, company=request.tenant).first()
        if not tipo:
            return JsonResponse({"ok": False}, status=404)
        tipo.delete()
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({"ok": True, "row_id": pk})
        return HttpResponseRedirect(reverse("produtos:tipos_list"))


class FamiliaProdutoListView(BaseTenantListView):
    model = FamiliaProduto
    template_name = "produtos/familias_list.html"
    form_class = FamiliaProdutoForm
    title = "Familias de Produto"
    headers = ["Nome", "Ativo"]
    row_fields = ["nome", "ativo"]
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
    create_url_name = "produtos:familias_create"
    update_url_name = "produtos:familias_update"


class FamiliaProdutoCreateView(BaseTenantCreateView):
    model = FamiliaProduto
    form_class = FamiliaProdutoForm
    success_url_name = "produtos:familias_list"

    def form_valid(self, form):
        nome = (form.cleaned_data.get("nome") or "").strip()
        if (
            nome
            and FamiliaProduto.objects.filter(company=self.request.tenant, nome__iexact=nome).exists()
        ):
            form.add_error("nome", "Familia ja cadastrada.")
            return self.form_invalid(form)
        response = super().form_valid(form)
        if self.request.headers.get("X-Requested-With") == "XMLHttpRequest":
            row_html = render_to_string(
                "produtos/_familia_produto_row.html",
                {"familia": self.object},
                request=self.request,
            )
            edit_modal_html = render_to_string(
                "produtos/_familia_produto_edit_modal.html",
                {
                    "familia": self.object,
                    "form": FamiliaProdutoForm(instance=self.object),
                    "update_url": reverse("produtos:familias_update", args=[self.object.pk]),
                },
                request=self.request,
            )
            form_html = render_to_string(
                "components/_form.html",
                {"form": FamiliaProdutoForm(), "form_action": reverse("produtos:familias_create")},
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
                {"form": form, "form_action": reverse("produtos:familias_create")},
                request=self.request,
            )
            return JsonResponse({"ok": False, "form_html": form_html}, status=400)
        return super().form_invalid(form)


class FamiliaProdutoUpdateView(BaseTenantUpdateView):
    model = FamiliaProduto
    form_class = FamiliaProdutoForm
    success_url_name = "produtos:familias_list"

    def form_valid(self, form):
        nome = (form.cleaned_data.get("nome") or "").strip()
        if (
            nome
            and FamiliaProduto.objects.filter(company=self.request.tenant, nome__iexact=nome)
            .exclude(pk=form.instance.pk)
            .exists()
        ):
            form.add_error("nome", "Familia ja cadastrada.")
            return self.form_invalid(form)
        response = super().form_valid(form)
        if self.request.headers.get("X-Requested-With") == "XMLHttpRequest":
            row_html = render_to_string(
                "produtos/_familia_produto_row.html",
                {"familia": self.object},
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
                    "form_action": reverse("produtos:familias_update", args=[self.get_object().pk]),
                },
                request=self.request,
            )
            return JsonResponse(
                {"ok": False, "form_html": form_html, "row_id": self.get_object().pk},
                status=400,
            )
        return super().form_invalid(form)


class FamiliaProdutoToggleActiveView(PermissionRequiredMixin, View):
    permission_required = "produtos.change_familiaproduto"

    def post(self, request, pk):
        familia = FamiliaProduto.objects.filter(pk=pk, company=request.tenant).first()
        if not familia:
            return JsonResponse({"ok": False}, status=404)
        produtos = list(
            Produto.objects.filter(company=request.tenant, familia=familia)
            .values("id", "nome")
            .distinct()
        )
        if produtos:
            return JsonResponse(
                {"ok": False, "blocked": True, "produtos": produtos, "row_id": familia.pk},
                status=400,
            )
        familia.ativo = not familia.ativo
        familia.updated_by = request.user
        familia.save(update_fields=["ativo", "updated_by"])
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            row_html = render_to_string(
                "produtos/_familia_produto_row.html",
                {"familia": familia},
                request=request,
            )
            return JsonResponse({"ok": True, "row_id": familia.pk, "row_html": row_html})
        return HttpResponseRedirect(reverse("produtos:familias_list"))


class FamiliaProdutoDeleteView(PermissionRequiredMixin, View):
    permission_required = "produtos.delete_familiaproduto"

    def post(self, request, pk):
        familia = FamiliaProduto.objects.filter(pk=pk, company=request.tenant).first()
        if not familia:
            return JsonResponse({"ok": False}, status=404)
        produtos = list(
            Produto.objects.filter(company=request.tenant, familia=familia)
            .values("id", "nome")
            .distinct()
        )
        if produtos:
            return JsonResponse(
                {"ok": False, "blocked": True, "produtos": produtos, "row_id": familia.pk},
                status=400,
            )
        familia.delete()
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({"ok": True, "row_id": pk})
        return HttpResponseRedirect(reverse("produtos:familias_list"))


class FamiliaProdutoUsoView(View):
    def get(self, request, pk):
        familia = FamiliaProduto.objects.filter(pk=pk, company=request.tenant).first()
        if not familia:
            return JsonResponse({"ok": False}, status=404)
        produtos = list(
            Produto.objects.filter(company=request.tenant, familia=familia)
            .values("id", "nome")
            .distinct()
        )
        return JsonResponse({"ok": True, "produtos": produtos})


class SubfamiliaProdutoListView(BaseTenantListView):
    model = SubfamiliaProduto
    template_name = "produtos/subfamilias_list.html"
    form_class = SubfamiliaProdutoForm
    title = "Subfamilias de Produto"
    headers = ["Nome", "Ativo"]
    row_fields = ["nome", "ativo"]
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
    create_url_name = "produtos:subfamilias_create"
    update_url_name = "produtos:subfamilias_update"


class SubfamiliaProdutoCreateView(BaseTenantCreateView):
    model = SubfamiliaProduto
    form_class = SubfamiliaProdutoForm
    success_url_name = "produtos:subfamilias_list"

    def form_valid(self, form):
        nome = (form.cleaned_data.get("nome") or "").strip()
        if (
            nome
            and SubfamiliaProduto.objects.filter(
                company=self.request.tenant,
                nome__iexact=nome,
            ).exists()
        ):
            form.add_error("nome", "Subfamilia ja cadastrada.")
            return self.form_invalid(form)
        response = super().form_valid(form)
        if self.request.headers.get("X-Requested-With") == "XMLHttpRequest":
            row_html = render_to_string(
                "produtos/_subfamilia_produto_row.html",
                {"subfamilia": self.object},
                request=self.request,
            )
            edit_modal_html = render_to_string(
                "produtos/_subfamilia_produto_edit_modal.html",
                {
                    "subfamilia": self.object,
                    "form": SubfamiliaProdutoForm(instance=self.object),
                    "update_url": reverse("produtos:subfamilias_update", args=[self.object.pk]),
                },
                request=self.request,
            )
            form_html = render_to_string(
                "components/_form.html",
                {"form": SubfamiliaProdutoForm(), "form_action": reverse("produtos:subfamilias_create")},
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
                {"form": form, "form_action": reverse("produtos:subfamilias_create")},
                request=self.request,
            )
            return JsonResponse({"ok": False, "form_html": form_html}, status=400)
        return super().form_invalid(form)


class SubfamiliaProdutoUpdateView(BaseTenantUpdateView):
    model = SubfamiliaProduto
    form_class = SubfamiliaProdutoForm
    success_url_name = "produtos:subfamilias_list"

    def form_valid(self, form):
        nome = (form.cleaned_data.get("nome") or "").strip()
        if (
            nome
            and SubfamiliaProduto.objects.filter(
                company=self.request.tenant,
                nome__iexact=nome,
            )
            .exclude(pk=form.instance.pk)
            .exists()
        ):
            form.add_error("nome", "Subfamilia ja cadastrada.")
            return self.form_invalid(form)
        response = super().form_valid(form)
        if self.request.headers.get("X-Requested-With") == "XMLHttpRequest":
            row_html = render_to_string(
                "produtos/_subfamilia_produto_row.html",
                {"subfamilia": self.object},
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
                    "form_action": reverse("produtos:subfamilias_update", args=[self.get_object().pk]),
                },
                request=self.request,
            )
            return JsonResponse(
                {"ok": False, "form_html": form_html, "row_id": self.get_object().pk},
                status=400,
            )
        return super().form_invalid(form)


class SubfamiliaProdutoToggleActiveView(PermissionRequiredMixin, View):
    permission_required = "produtos.change_subfamiliaproduto"

    def post(self, request, pk):
        subfamilia = SubfamiliaProduto.objects.filter(pk=pk, company=request.tenant).first()
        if not subfamilia:
            return JsonResponse({"ok": False}, status=404)
        produtos = list(
            Produto.objects.filter(company=request.tenant, subfamilia=subfamilia)
            .values("id", "nome")
            .distinct()
        )
        if produtos:
            return JsonResponse(
                {"ok": False, "blocked": True, "produtos": produtos, "row_id": subfamilia.pk},
                status=400,
            )
        subfamilia.ativo = not subfamilia.ativo
        subfamilia.updated_by = request.user
        subfamilia.save(update_fields=["ativo", "updated_by"])
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            row_html = render_to_string(
                "produtos/_subfamilia_produto_row.html",
                {"subfamilia": subfamilia},
                request=request,
            )
            return JsonResponse({"ok": True, "row_id": subfamilia.pk, "row_html": row_html})
        return HttpResponseRedirect(reverse("produtos:subfamilias_list"))


class SubfamiliaProdutoDeleteView(PermissionRequiredMixin, View):
    permission_required = "produtos.delete_subfamiliaproduto"

    def post(self, request, pk):
        subfamilia = SubfamiliaProduto.objects.filter(pk=pk, company=request.tenant).first()
        if not subfamilia:
            return JsonResponse({"ok": False}, status=404)
        produtos = list(
            Produto.objects.filter(company=request.tenant, subfamilia=subfamilia)
            .values("id", "nome")
            .distinct()
        )
        if produtos:
            return JsonResponse(
                {"ok": False, "blocked": True, "produtos": produtos, "row_id": subfamilia.pk},
                status=400,
            )
        subfamilia.delete()
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({"ok": True, "row_id": pk})
        return HttpResponseRedirect(reverse("produtos:subfamilias_list"))


class SubfamiliaProdutoUsoView(View):
    def get(self, request, pk):
        subfamilia = SubfamiliaProduto.objects.filter(pk=pk, company=request.tenant).first()
        if not subfamilia:
            return JsonResponse({"ok": False}, status=404)
        produtos = list(
            Produto.objects.filter(company=request.tenant, subfamilia=subfamilia)
            .values("id", "nome")
            .distinct()
        )
        return JsonResponse({"ok": True, "produtos": produtos})


class LocalRetiradaListView(BaseTenantListView):
    model = LocalRetirada
    template_name = "produtos/locais_retirada_list.html"
    form_class = LocalRetiradaForm
    title = "Locais de Retirada"
    headers = ["Nome", "Ativo"]
    row_fields = ["nome", "ativo"]
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
    create_url_name = "produtos:locais_retirada_create"
    update_url_name = "produtos:locais_retirada_update"


class LocalRetiradaCreateView(BaseTenantCreateView):
    model = LocalRetirada
    form_class = LocalRetiradaForm
    success_url_name = "produtos:locais_retirada_list"

    def form_valid(self, form):
        nome = (form.cleaned_data.get("nome") or "").strip()
        if (
            nome
            and LocalRetirada.objects.filter(company=self.request.tenant, nome__iexact=nome).exists()
        ):
            form.add_error("nome", "Local de retirada ja cadastrado.")
            return self.form_invalid(form)
        response = super().form_valid(form)
        if self.request.headers.get("X-Requested-With") == "XMLHttpRequest":
            row_html = render_to_string(
                "produtos/_local_retirada_row.html",
                {"local_retirada": self.object},
                request=self.request,
            )
            edit_modal_html = render_to_string(
                "produtos/_local_retirada_edit_modal.html",
                {
                    "local_retirada": self.object,
                    "form": LocalRetiradaForm(instance=self.object),
                    "update_url": reverse("produtos:locais_retirada_update", args=[self.object.pk]),
                },
                request=self.request,
            )
            form_html = render_to_string(
                "components/_form.html",
                {"form": LocalRetiradaForm(), "form_action": reverse("produtos:locais_retirada_create")},
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
                {"form": form, "form_action": reverse("produtos:locais_retirada_create")},
                request=self.request,
            )
            return JsonResponse({"ok": False, "form_html": form_html}, status=400)
        return super().form_invalid(form)


class LocalRetiradaUpdateView(BaseTenantUpdateView):
    model = LocalRetirada
    form_class = LocalRetiradaForm
    success_url_name = "produtos:locais_retirada_list"

    def form_valid(self, form):
        nome = (form.cleaned_data.get("nome") or "").strip()
        if (
            nome
            and LocalRetirada.objects.filter(company=self.request.tenant, nome__iexact=nome)
            .exclude(pk=form.instance.pk)
            .exists()
        ):
            form.add_error("nome", "Local de retirada ja cadastrado.")
            return self.form_invalid(form)
        response = super().form_valid(form)
        if self.request.headers.get("X-Requested-With") == "XMLHttpRequest":
            row_html = render_to_string(
                "produtos/_local_retirada_row.html",
                {"local_retirada": self.object},
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
                    "form_action": reverse("produtos:locais_retirada_update", args=[self.get_object().pk]),
                },
                request=self.request,
            )
            return JsonResponse(
                {"ok": False, "form_html": form_html, "row_id": self.get_object().pk},
                status=400,
            )
        return super().form_invalid(form)


class LocalRetiradaToggleActiveView(PermissionRequiredMixin, View):
    permission_required = "produtos.change_localretirada"

    def post(self, request, pk):
        local_retirada = LocalRetirada.objects.filter(pk=pk, company=request.tenant).first()
        if not local_retirada:
            return JsonResponse({"ok": False}, status=404)
        local_retirada.ativo = not local_retirada.ativo
        local_retirada.updated_by = request.user
        local_retirada.save(update_fields=["ativo", "updated_by"])
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            row_html = render_to_string(
                "produtos/_local_retirada_row.html",
                {"local_retirada": local_retirada},
                request=request,
            )
            return JsonResponse({"ok": True, "row_id": local_retirada.pk, "row_html": row_html})
        return HttpResponseRedirect(reverse("produtos:locais_retirada_list"))


class LocalRetiradaDeleteView(PermissionRequiredMixin, View):
    permission_required = "produtos.delete_localretirada"

    def post(self, request, pk):
        local_retirada = LocalRetirada.objects.filter(pk=pk, company=request.tenant).first()
        if not local_retirada:
            return JsonResponse({"ok": False}, status=404)
        local_retirada.delete()
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({"ok": True, "row_id": pk})
        return HttpResponseRedirect(reverse("produtos:locais_retirada_list"))


class PeriodicidadeListView(BaseTenantListView):
    model = Periodicidade
    template_name = "produtos/periodicidades_list.html"
    form_class = PeriodicidadeForm
    title = "Periodicidades"
    headers = ["Nome", "Fator (dias)", "Ativo"]
    row_fields = ["nome", "fator_dias", "ativo"]
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
    create_url_name = "produtos:periodicidades_create"
    update_url_name = "produtos:periodicidades_update"


class PeriodicidadeCreateView(BaseTenantCreateView):
    model = Periodicidade
    form_class = PeriodicidadeForm
    success_url_name = "produtos:periodicidades_list"

    def form_valid(self, form):
        nome = (form.cleaned_data.get("nome") or "").strip()
        if (
            nome
            and Periodicidade.objects.filter(company=self.request.tenant, nome__iexact=nome).exists()
        ):
            form.add_error("nome", "Periodicidade ja cadastrada.")
            return self.form_invalid(form)
        response = super().form_valid(form)
        if self.request.headers.get("X-Requested-With") == "XMLHttpRequest":
            row_html = render_to_string(
                "produtos/_periodicidade_row.html",
                {"periodicidade": self.object},
                request=self.request,
            )
            edit_modal_html = render_to_string(
                "produtos/_periodicidade_edit_modal.html",
                {
                    "periodicidade": self.object,
                    "form": PeriodicidadeForm(instance=self.object),
                    "update_url": reverse("produtos:periodicidades_update", args=[self.object.pk]),
                },
                request=self.request,
            )
            form_html = render_to_string(
                "components/_form.html",
                {
                    "form": PeriodicidadeForm(),
                    "form_action": reverse("produtos:periodicidades_create"),
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
                {"form": form, "form_action": reverse("produtos:periodicidades_create")},
                request=self.request,
            )
            return JsonResponse({"ok": False, "form_html": form_html}, status=400)
        return super().form_invalid(form)


class PeriodicidadeUpdateView(BaseTenantUpdateView):
    model = Periodicidade
    form_class = PeriodicidadeForm
    success_url_name = "produtos:periodicidades_list"

    def form_valid(self, form):
        nome = (form.cleaned_data.get("nome") or "").strip()
        if (
            nome
            and Periodicidade.objects.filter(company=self.request.tenant, nome__iexact=nome)
            .exclude(pk=form.instance.pk)
            .exists()
        ):
            form.add_error("nome", "Periodicidade ja cadastrada.")
            return self.form_invalid(form)
        response = super().form_valid(form)
        if self.request.headers.get("X-Requested-With") == "XMLHttpRequest":
            row_html = render_to_string(
                "produtos/_periodicidade_row.html",
                {"periodicidade": self.object},
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
                    "form_action": reverse("produtos:periodicidades_update", args=[self.get_object().pk]),
                },
                request=self.request,
            )
            return JsonResponse(
                {"ok": False, "form_html": form_html, "row_id": self.get_object().pk},
                status=400,
            )
        return super().form_invalid(form)


class PeriodicidadeToggleActiveView(PermissionRequiredMixin, View):
    permission_required = "produtos.change_periodicidade"

    def post(self, request, pk):
        periodicidade = Periodicidade.objects.filter(pk=pk, company=request.tenant).first()
        if not periodicidade:
            return JsonResponse({"ok": False}, status=404)
        periodicidade.ativo = not periodicidade.ativo
        periodicidade.updated_by = request.user
        periodicidade.save(update_fields=["ativo", "updated_by"])
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            row_html = render_to_string(
                "produtos/_periodicidade_row.html",
                {"periodicidade": periodicidade},
                request=request,
            )
            return JsonResponse({"ok": True, "row_id": periodicidade.pk, "row_html": row_html})
        return HttpResponseRedirect(reverse("produtos:periodicidades_list"))


class PeriodicidadeDeleteView(PermissionRequiredMixin, View):
    permission_required = "produtos.delete_periodicidade"

    def post(self, request, pk):
        periodicidade = Periodicidade.objects.filter(pk=pk, company=request.tenant).first()
        if not periodicidade:
            return JsonResponse({"ok": False}, status=404)
        periodicidade.delete()
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({"ok": True, "row_id": pk})
        return HttpResponseRedirect(reverse("produtos:periodicidades_list"))


class LocalizacaoProdutoListView(BaseTenantListView):
    model = LocalizacaoProduto
    template_name = "produtos/localizacoes_list.html"
    form_class = LocalizacaoProdutoForm
    title = "Localizacao de Produtos"
    headers = ["Nome", "Ordem", "Ativo"]
    row_fields = ["nome", "ordem", "ativo"]
    filter_definitions = [
        {"name": "nome", "label": "Nome", "lookup": "icontains", "type": "text"},
        {"name": "ordem", "label": "Ordem", "lookup": "exact", "type": "text"},
        {
            "name": "ativo",
            "label": "Ativo",
            "lookup": "exact_bool",
            "type": "select",
            "options": [("", "Todos"), ("1", "Ativo"), ("0", "Inativo")],
        },
    ]
    create_url_name = "produtos:localizacoes_create"
    update_url_name = "produtos:localizacoes_update"


class LocalizacaoProdutoCreateView(BaseTenantCreateView):
    model = LocalizacaoProduto
    form_class = LocalizacaoProdutoForm
    success_url_name = "produtos:localizacoes_list"

    def form_valid(self, form):
        nome = (form.cleaned_data.get("nome") or "").strip()
        ordem = form.cleaned_data.get("ordem")
        if (
            nome
            and LocalizacaoProduto.objects.filter(company=self.request.tenant, nome__iexact=nome).exists()
        ):
            form.add_error("nome", "Localizacao ja cadastrada.")
            return self.form_invalid(form)
        if (
            ordem is not None
            and LocalizacaoProduto.objects.filter(company=self.request.tenant, ordem=ordem).exists()
        ):
            form.add_error("ordem", "Ordem ja cadastrada.")
            return self.form_invalid(form)
        response = super().form_valid(form)
        if self.request.headers.get("X-Requested-With") == "XMLHttpRequest":
            row_html = render_to_string(
                "produtos/_localizacao_row.html",
                {"localizacao": self.object},
                request=self.request,
            )
            edit_modal_html = render_to_string(
                "produtos/_localizacao_edit_modal.html",
                {
                    "localizacao": self.object,
                    "form": LocalizacaoProdutoForm(instance=self.object),
                    "update_url": reverse("produtos:localizacoes_update", args=[self.object.pk]),
                },
                request=self.request,
            )
            form_html = render_to_string(
                "components/_form.html",
                {
                    "form": LocalizacaoProdutoForm(),
                    "form_action": reverse("produtos:localizacoes_create"),
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
                {"form": form, "form_action": reverse("produtos:localizacoes_create")},
                request=self.request,
            )
            return JsonResponse({"ok": False, "form_html": form_html}, status=400)
        return super().form_invalid(form)


class LocalizacaoProdutoUpdateView(BaseTenantUpdateView):
    model = LocalizacaoProduto
    form_class = LocalizacaoProdutoForm
    success_url_name = "produtos:localizacoes_list"

    def form_valid(self, form):
        nome = (form.cleaned_data.get("nome") or "").strip()
        ordem = form.cleaned_data.get("ordem")
        if (
            nome
            and LocalizacaoProduto.objects.filter(company=self.request.tenant, nome__iexact=nome)
            .exclude(pk=form.instance.pk)
            .exists()
        ):
            form.add_error("nome", "Localizacao ja cadastrada.")
            return self.form_invalid(form)
        if (
            ordem is not None
            and LocalizacaoProduto.objects.filter(company=self.request.tenant, ordem=ordem)
            .exclude(pk=form.instance.pk)
            .exists()
        ):
            form.add_error("ordem", "Ordem ja cadastrada.")
            return self.form_invalid(form)
        response = super().form_valid(form)
        if self.request.headers.get("X-Requested-With") == "XMLHttpRequest":
            row_html = render_to_string(
                "produtos/_localizacao_row.html",
                {"localizacao": self.object},
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
                    "form_action": reverse("produtos:localizacoes_update", args=[self.get_object().pk]),
                },
                request=self.request,
            )
            return JsonResponse(
                {"ok": False, "form_html": form_html, "row_id": self.get_object().pk},
                status=400,
            )
        return super().form_invalid(form)


class LocalizacaoProdutoToggleActiveView(PermissionRequiredMixin, View):
    permission_required = "produtos.change_localizacaoproduto"

    def post(self, request, pk):
        localizacao = LocalizacaoProduto.objects.filter(pk=pk, company=request.tenant).first()
        if not localizacao:
            return JsonResponse({"ok": False}, status=404)
        localizacao.ativo = not localizacao.ativo
        localizacao.updated_by = request.user
        localizacao.save(update_fields=["ativo", "updated_by"])
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            row_html = render_to_string(
                "produtos/_localizacao_row.html",
                {"localizacao": localizacao},
                request=request,
            )
            return JsonResponse({"ok": True, "row_id": localizacao.pk, "row_html": row_html})
        return HttpResponseRedirect(reverse("produtos:localizacoes_list"))


class LocalizacaoProdutoDeleteView(PermissionRequiredMixin, View):
    permission_required = "produtos.delete_localizacaoproduto"

    def post(self, request, pk):
        localizacao = LocalizacaoProduto.objects.filter(pk=pk, company=request.tenant).first()
        if not localizacao:
            return JsonResponse({"ok": False}, status=404)
        localizacao.delete()
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({"ok": True, "row_id": pk})
        return HttpResponseRedirect(reverse("produtos:localizacoes_list"))


class ProdutoToggleActiveView(PermissionRequiredMixin, ProdutoFornecedorAnexoMixin, View):
    permission_required = "produtos.change_produto"

    def post(self, request, pk):
        produto = get_object_or_404(Produto, pk=pk, company=request.tenant)
        produto.ativo = not produto.ativo
        produto.updated_by = request.user
        produto.save(update_fields=["ativo", "updated_by"])
        ActionLog.objects.create(
            company=request.tenant,
            actor=request.user,
            action="produto_ativado" if produto.ativo else "produto_desativado",
            reference=f"Produto:{produto.pk}",
        )
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            produto = self._get_annotated_produto(produto.pk)
            row_html = render_to_string(
                "produtos/_produto_row.html",
                {"produto": produto},
                request=request,
            )
            return JsonResponse({"ok": True, "row_id": produto.pk, "row_html": row_html})
        return HttpResponseRedirect(reverse("produtos:list"))


class ProdutoHistoricoListView(View):
    def get(self, request, pk):
        produto = get_object_or_404(Produto, pk=pk, company=request.tenant)
        movimentos = (
            MovimentacaoEstoque.objects.filter(
                company=request.tenant,
                estoque__produto=produto,
            )
            .select_related("estoque__deposito", "deposito_destino", "created_by")
            .order_by("-criado_em")
        )
        logs = ActionLog.objects.filter(
            company=request.tenant,
            reference=f"Produto:{produto.pk}",
        ).select_related("actor")
        descricao = request.GET.get("descricao")
        data_inicio = request.GET.get("data_inicio")
        data_fim = request.GET.get("data_fim")
        tipo = request.GET.get("tipo")
        if descricao:
            movimentos = movimentos.filter(observacao__icontains=descricao)
        if data_inicio:
            movimentos = movimentos.filter(criado_em__date__gte=data_inicio)
            logs = logs.filter(created_at__date__gte=data_inicio)
        if data_fim:
            movimentos = movimentos.filter(criado_em__date__lte=data_fim)
            logs = logs.filter(created_at__date__lte=data_fim)
        if tipo:
            movimentos = movimentos.filter(tipo=tipo)
            logs = logs.none()

        registros = []
        for movimento in movimentos:
            if movimento.tipo == "entrada":
                descricao_mov = (
                    f"Entrada de {movimento.quantidade} no deposito {movimento.estoque.deposito}"
                )
            elif movimento.tipo == "saida":
                descricao_mov = (
                    f"Saida de {movimento.quantidade} do deposito {movimento.estoque.deposito}"
                )
            else:
                descricao_mov = (
                    f"Transferencia de {movimento.quantidade} do deposito "
                    f"{movimento.estoque.deposito} para {movimento.deposito_destino or '-'}"
                )
            if movimento.observacao:
                descricao_mov = f"{descricao_mov} ({movimento.observacao})"
            registros.append(
                {
                    "descricao": descricao_mov,
                    "usuario": movimento.created_by,
                    "horario": movimento.criado_em,
                }
            )

        descricao_map = {
            "produto_criado": "Produto criado.",
            "produto_atualizado": "Produto atualizado.",
            "produto_ativado": "Produto ativado.",
            "produto_desativado": "Produto desativado.",
        }
        for log in logs:
            descricao_log = descricao_map.get(log.action, "Alteracao registrada.")
            if descricao and descricao.lower() not in descricao_log.lower():
                continue
            registros.append(
                {
                    "descricao": descricao_log,
                    "usuario": log.actor,
                    "horario": log.created_at,
                }
            )

        registros.sort(key=lambda item: item["horario"], reverse=True)

        paginator = Paginator(registros, 10)
        page = request.GET.get("page") or 1
        try:
            page_number = int(page)
        except (TypeError, ValueError):
            page_number = 1
        if page_number < 1:
            page_number = 1
        try:
            page_obj = paginator.page(page_number)
        except InvalidPage:
            page_obj = paginator.page(1)
        rows_html = render_to_string(
            "produtos/_historico_rows.html",
            {"registros": page_obj.object_list},
            request=request,
        )
        pagination_html = render_to_string(
            "components/_pagination.html",
            {"page_obj": page_obj},
            request=request,
        )
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse(
                {
                    "ok": True,
                    "rows_html": rows_html,
                    "pagination_html": pagination_html,
                }
            )
        return HttpResponseRedirect(reverse("produtos:list"))


def _caepi_to_dict(item):
    return {
        "RegistroCA": item.registro_ca,
        "DataValidade": item.data_validade,
        "data_validade_display": item.data_validade.strftime("%d/%m/%Y") if item.data_validade else "-",
        "Situacao": item.situacao,
        "NRProcesso": item.nr_processo,
        "CNPJ": item.cnpj,
        "RazaoSocial": item.razao_social,
        "Natureza": item.natureza,
        "NomeEquipamento": item.nome_equipamento,
        "DescricaoEquipamento": item.descricao_equipamento,
        "MarcaCA": item.marca_ca,
        "Referencia": item.referencia,
        "Cor": item.cor,
        "AprovadoParaLaudo": item.aprovado_para_laudo,
        "RestricaoLaudo": item.restricao_laudo,
        "ObservacaoAnaliseLaudo": item.observacao_analise_laudo,
        "CNPJLaboratorio": item.cnpj_laboratorio,
        "RazaoSocialLaboratorio": item.razao_social_laboratorio,
        "NRLaudo": item.nr_laudo,
        "Norma": item.norma,
    }


def _query_caepi(ca, descricao, fornecedor, somente_validos, offset, limit):
    results = []
    selected = None
    data_found = False
    has_more = False
    next_offset = offset + limit

    today = timezone.localdate()
    with schema_context("public"):
        queryset = CaEPI.objects.all()
        data_found = queryset.exists()
        if somente_validos:
            queryset = queryset.filter(data_validade__gte=today)
        if ca:
            queryset = queryset.filter(registro_ca=ca)
        else:
            if descricao:
                queryset = queryset.filter(
                    Q(descricao_equipamento__icontains=descricao)
                    | Q(nome_equipamento__icontains=descricao)
                )
            if fornecedor:
                queryset = queryset.filter(razao_social__icontains=fornecedor)

        # Evita repeticao de um mesmo CA quando ha registros duplicados na base
        queryset = queryset.order_by("registro_ca", "-data_validade").distinct("registro_ca")
        if ca:
            items = list(queryset[:limit])
            results = [_caepi_to_dict(item) for item in items]
            if results:
                selected = results[0]
            has_more = False
        else:
            if descricao or fornecedor:
                items = list(queryset[offset : offset + limit + 1])
                has_more = len(items) > limit
                items = items[:limit]
                results = [_caepi_to_dict(item) for item in items]

    return data_found, results, selected, has_more, next_offset


class CaImportApiView(PermissionRequiredMixin, View):
    permission_required = "produtos.view_produto"

    def get(self, request):
        ca = (request.GET.get("ca") or "").strip()
        descricao = (request.GET.get("descricao") or "").strip()
        fornecedor = (request.GET.get("fornecedor") or "").strip()
        somente_validos = request.GET.get("validos") == "1"
        limit = 20
        try:
            offset = int(request.GET.get("offset") or 0)
        except (TypeError, ValueError):
            offset = 0

        if not ca and not descricao and not fornecedor:
            return JsonResponse(
                {"ok": False, "error": "Informe um valor para buscar."},
                status=400,
            )

        data_found, results, selected, has_more, next_offset = _query_caepi(
            ca, descricao, fornecedor, somente_validos, offset, limit
        )
        searched_ca = bool(ca)
        has_results = bool(results)
        rows_html = ""
        selected_html = ""
        if request.GET.get("render") == "1":
            rows_html = render_to_string(
                "produtos/_ca_import_rows.html",
                {"results": results, "somente_validos": somente_validos},
                request=request,
            )
            selected_html = render_to_string(
                "produtos/_ca_import_selected.html",
                {"selected": selected},
                request=request,
            )
        return JsonResponse(
            {
                "ok": True,
                "data_found": data_found,
                "results": results,
                "selected": selected,
                "has_more": has_more,
                "next_offset": next_offset,
                "searched_ca": searched_ca,
                "has_results": has_results,
                "rows_html": rows_html,
                "selected_html": selected_html,
            }
        )


class CaImportFornecedorApiView(PermissionRequiredMixin, View):
    permission_required = "fornecedores.add_fornecedor"

    def post(self, request):
        nome = (request.POST.get("nome") or "").strip()
        if not nome:
            return JsonResponse({"ok": False, "error": "Fornecedor invalido."}, status=400)

        fornecedor = (
            Fornecedor.objects.filter(company=request.tenant, nome__iexact=nome).first()
        )
        created = False
        if not fornecedor:
            fornecedor = Fornecedor.objects.create(
                company=request.tenant,
                nome=nome,
                created_by=request.user,
                updated_by=request.user,
            )
            created = True

        return JsonResponse(
            {
                "ok": True,
                "id": fornecedor.pk,
                "nome": fornecedor.nome,
                "created": created,
            }
        )


class CaImportView(PermissionRequiredMixin, View):
    permission_required = "produtos.view_produto"
    template_name = "produtos/ca_import.html"

    def get(self, request):
        ca = (request.GET.get("ca") or "").strip()
        descricao = (request.GET.get("descricao") or "").strip()
        fornecedor = (request.GET.get("fornecedor") or "").strip()
        somente_validos = request.GET.get("validos") == "1"
        searched = request.GET.get("buscar") == "1"
        limit = 20
        try:
            offset = int(request.GET.get("offset") or 0)
        except (TypeError, ValueError):
            offset = 0

        results = []
        selected = None
        data_found = False
        has_more = False
        next_offset = offset + limit

        if searched:
            data_found, results, selected, has_more, next_offset = _query_caepi(
                ca, descricao, fornecedor, somente_validos, offset, limit
            )

            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                rows_html = render_to_string(
                    "produtos/_ca_import_rows.html",
                    {"results": results, "somente_validos": somente_validos},
                    request=request,
                )
                return JsonResponse(
                    {
                        "ok": True,
                        "rows_html": rows_html,
                        "has_more": has_more,
                        "next_offset": offset + limit,
                    }
                )

        context = {
            "title": "Importar CA",
            "ca_value": ca,
            "descricao_value": descricao,
            "fornecedor_value": fornecedor,
            "somente_validos": somente_validos,
            "results": results,
            "selected": selected,
            "csv_found": data_found,
            "searched": searched,
            "has_more": has_more,
            "next_offset": next_offset,
            "create_form": ProdutoForm(),
            "create_produto_url": reverse("produtos:create"),
        }
        return render(request, self.template_name, context)
