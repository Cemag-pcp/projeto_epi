import base64
import binascii
import json
import uuid
from decimal import Decimal, InvalidOperation

from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.http import JsonResponse
from django.template.loader import render_to_string
from django.urls import reverse, reverse_lazy
from django.db import transaction

from apps.core.views import BaseTenantCreateView, BaseTenantListView, BaseTenantUpdateView
from apps.depositos.models import Deposito
from apps.estoque.models import Estoque, MovimentacaoEstoque
from apps.funcionarios.models import Planta
from apps.produtos.models import Produto
from .forms import (
    AcessoEPIForm,
    ConsumoParceiroBatchForm,
    ConsumoParceiroForm,
    EmpresaParceiraForm,
    TerceiroForm,
)
from .models import AcessoEPI, ConsumoParceiro, EmpresaParceira, Terceiro

MAX_ASSINATURA_SIZE = 3 * 1024 * 1024  # 3MB


def _decode_assinatura(raw_value):
    if not raw_value or not isinstance(raw_value, str):
        return None, "Assinatura obrigatoria."
    base64_data = raw_value
    extension = "png"
    if raw_value.startswith("data:"):
        try:
            header, base64_data = raw_value.split(",", 1)
        except ValueError:
            return None, "Assinatura invalida."
        if "jpeg" in header or "jpg" in header:
            extension = "jpg"
        elif "webp" in header:
            extension = "webp"
    try:
        decoded = base64.b64decode(base64_data)
    except (binascii.Error, ValueError):
        return None, "Assinatura invalida."
    if len(decoded) > MAX_ASSINATURA_SIZE:
        return None, "Assinatura excede o limite de 3MB."
    filename = f"assinatura-{uuid.uuid4().hex[:12]}.{extension}"
    return ContentFile(decoded, name=filename), None


def _get_consumo_terceiros_deposito(request):
    tenant = request.tenant
    planta_id = request.session.get("planta_id")
    planta = None
    if planta_id:
        planta = Planta.objects.filter(company=tenant, pk=planta_id, ativo=True).first()
    if planta is None:
        planta = Planta.objects.filter(company=tenant, ativo=True).order_by("nome").first()
    if planta is None:
        return None
    deposito = (
        Deposito.objects.filter(company=tenant, planta=planta, nome__iexact="Consumo terceiros")
        .order_by("pk")
        .first()
    )
    if deposito:
        return deposito
    return Deposito.objects.create(
        company=tenant,
        planta=planta,
        nome="Consumo terceiros",
        ativo=True,
    )


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


@login_required
@require_GET
def depositos_por_produto(request):
    produto_id = request.GET.get("produto_id")
    if not produto_id:
        return JsonResponse({"ok": True, "depositos": []})
    tenant = request.tenant
    planta_id = request.session.get("planta_id")
    estoque_qs = Estoque.objects.filter(company=tenant, produto_id=produto_id).select_related("deposito")
    if planta_id:
        estoque_qs = estoque_qs.filter(deposito__planta_id=planta_id)
    estoque_qs = estoque_qs.filter(deposito__ativo=True)
    depositos = []
    seen = set()
    for estoque in estoque_qs.order_by("deposito__nome"):
        if estoque.deposito_id in seen:
            continue
        seen.add(estoque.deposito_id)
        depositos.append({"id": estoque.deposito_id, "nome": estoque.deposito.nome})
    return JsonResponse({"ok": True, "depositos": depositos})


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
    template_name = "acessos/terceiros_list.html"
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
    headers = ["Terceiro", "Empresa", "Produto", "Deposito", "Quantidade", "Data", "Observacao"]
    row_fields = [
        "terceiro",
        "empresa_parceira_label",
        "produto",
        "deposito",
        "quantidade",
        "data",
        "observacao",
    ]
    filter_definitions = [
        {"name": "terceiro__nome", "label": "Terceiro", "lookup": "icontains", "type": "text"},
        {
            "name": "terceiro__empresa_parceira__nome",
            "label": "Empresa",
            "lookup": "icontains",
            "type": "text",
        },
        {"name": "produto__nome", "label": "Produto", "lookup": "icontains", "type": "text"},
        {"name": "deposito__nome", "label": "Deposito", "lookup": "icontains", "type": "text"},
    ]
    create_url_name = "acessos:consumos_create"
    update_url_name = "acessos:consumos_update"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if context.get("can_add"):
            context["create_form"] = ConsumoParceiroBatchForm(tenant=self.request.tenant)
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

    def post(self, request, *args, **kwargs):
        itens_payload = request.POST.get("itens_payload")
        assinatura_payload = request.POST.get("assinatura_payload")
        if not itens_payload:
            return super().post(request, *args, **kwargs)

        form = ConsumoParceiroBatchForm(request.POST, tenant=request.tenant)
        items = None
        try:
            items = json.loads(itens_payload)
        except json.JSONDecodeError:
            items = None
        if not isinstance(items, list) or not items:
            form.add_error(None, "Adicione ao menos um produto para registrar o consumo.")
        assinatura_file, assinatura_error = _decode_assinatura(assinatura_payload)
        if assinatura_error:
            form.add_error(None, assinatura_error)
        if not form.is_valid():
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                form_html = render_to_string(
                    "acessos/_consumo_batch_form.html",
                    {
                        "form": form,
                        "form_action": reverse("acessos:consumos_create"),
                        "form_id": "consumo-form",
                    },
                    request=request,
                )
                return JsonResponse({"ok": False, "form_html": form_html}, status=400)
            return super().post(request, *args, **kwargs)

        terceiro = form.cleaned_data["terceiro"]
        data = form.cleaned_data["data"]
        observacao = form.cleaned_data.get("observacao") or ""

        parsed_items = []
        product_ids = []
        seen_products = set()
        deposito_ids = []
        for idx, item in enumerate(items, start=1):
            produto_id = item.get("produto_id")
            deposito_id = item.get("deposito_id")
            quantidade_raw = item.get("quantidade")
            if not produto_id or not deposito_id or quantidade_raw in (None, ""):
                form.add_error(None, f"Item {idx}: informe produto, deposito e quantidade.")
                continue
            try:
                produto_id_int = int(produto_id)
            except (TypeError, ValueError):
                form.add_error(None, f"Item {idx}: produto invalido.")
                continue
            if produto_id_int in seen_products:
                form.add_error(None, f"Item {idx}: produto duplicado.")
                continue
            seen_products.add(produto_id_int)
            try:
                deposito_id_int = int(deposito_id)
            except (TypeError, ValueError):
                form.add_error(None, f"Item {idx}: deposito invalido.")
                continue
            try:
                quantidade = Decimal(str(quantidade_raw))
            except (InvalidOperation, ValueError):
                form.add_error(None, f"Item {idx}: quantidade invalida.")
                continue
            if quantidade <= 0:
                form.add_error(None, f"Item {idx}: quantidade deve ser maior que zero.")
                continue
            product_ids.append(produto_id_int)
            deposito_ids.append(deposito_id_int)
            parsed_items.append(
                {"produto_id": produto_id_int, "deposito_id": deposito_id_int, "quantidade": quantidade}
            )

        produtos = Produto.objects.filter(company=request.tenant, ativo=True, pk__in=product_ids).in_bulk()
        depositos = Deposito.objects.filter(company=request.tenant, ativo=True, pk__in=deposito_ids).in_bulk()
        for idx, row in enumerate(parsed_items, start=1):
            if row["produto_id"] not in produtos:
                form.add_error(None, f"Item {idx}: produto invalido.")
            if row["deposito_id"] not in depositos:
                form.add_error(None, f"Item {idx}: deposito invalido.")
            if not Estoque.objects.filter(
                company=request.tenant,
                produto_id=row["produto_id"],
                deposito_id=row["deposito_id"],
            ).exists():
                form.add_error(None, f"Item {idx}: produto nao cadastrado no deposito informado.")

        if form.errors:
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                form_html = render_to_string(
                    "acessos/_consumo_batch_form.html",
                    {
                        "form": form,
                        "form_action": reverse("acessos:consumos_create"),
                        "form_id": "consumo-form",
                    },
                    request=request,
                )
                return JsonResponse({"ok": False, "form_html": form_html}, status=400)
            return super().post(request, *args, **kwargs)

        try:
            with transaction.atomic():
                first = parsed_items[0]
                estoque_first = Estoque.objects.select_for_update().filter(
                    company=request.tenant,
                    produto_id=first["produto_id"],
                    deposito_id=first["deposito_id"],
                ).first()
                if not estoque_first:
                    raise ValidationError("Produto nao cadastrado no deposito informado.")
                primeiro = ConsumoParceiro.objects.create(
                    company=request.tenant,
                    terceiro=terceiro,
                    produto=produtos[first["produto_id"]],
                    deposito=depositos[first["deposito_id"]],
                    quantidade=first["quantidade"],
                    data=data,
                    observacao=observacao,
                    created_by=request.user,
                    updated_by=request.user,
                )
                assinatura_file.seek(0)
                primeiro.assinatura.save(assinatura_file.name, assinatura_file, save=True)
                assinatura_name = primeiro.assinatura.name
                MovimentacaoEstoque.objects.create(
                    company=request.tenant,
                    estoque=estoque_first,
                    tipo=MovimentacaoEstoque.SAIDA,
                    quantidade=first["quantidade"],
                    observacao=f"Consumo terceiro: {terceiro}",
                    created_by=request.user,
                    updated_by=request.user,
                )
                for row in parsed_items[1:]:
                    estoque_obj = Estoque.objects.select_for_update().filter(
                        company=request.tenant,
                        produto_id=row["produto_id"],
                        deposito_id=row["deposito_id"],
                    ).first()
                    if not estoque_obj:
                        raise ValidationError("Produto nao cadastrado no deposito informado.")
                    MovimentacaoEstoque.objects.create(
                        company=request.tenant,
                        estoque=estoque_obj,
                        tipo=MovimentacaoEstoque.SAIDA,
                        quantidade=row["quantidade"],
                        observacao=f"Consumo terceiro: {terceiro}",
                        created_by=request.user,
                        updated_by=request.user,
                    )
                    ConsumoParceiro.objects.create(
                        company=request.tenant,
                        terceiro=terceiro,
                        produto=produtos[row["produto_id"]],
                        deposito=depositos[row["deposito_id"]],
                        quantidade=row["quantidade"],
                        data=data,
                        observacao=observacao,
                        assinatura=assinatura_name,
                        created_by=request.user,
                        updated_by=request.user,
                    )
        except ValidationError as exc:
            form.add_error(None, "; ".join(exc.messages) if getattr(exc, "messages", None) else str(exc))
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                form_html = render_to_string(
                    "acessos/_consumo_batch_form.html",
                    {
                        "form": form,
                        "form_action": reverse("acessos:consumos_create"),
                        "form_id": "consumo-form",
                    },
                    request=request,
                )
                return JsonResponse({"ok": False, "form_html": form_html}, status=400)
            return super().post(request, *args, **kwargs)

        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({"ok": True, "action": "create_batch"})
        return super().post(request, *args, **kwargs)

    def form_valid(self, form):
        with transaction.atomic():
            response = super().form_valid(form)
            produto = form.cleaned_data.get("produto")
            quantidade = form.cleaned_data.get("quantidade")
            terceiro = form.cleaned_data.get("terceiro")
            deposito = form.cleaned_data.get("deposito")
            if produto and deposito and quantidade and quantidade > 0:
                estoque_obj = Estoque.objects.select_for_update().filter(
                    company=self.request.tenant,
                    produto=produto,
                    deposito=deposito,
                ).first()
                if not estoque_obj:
                    raise ValidationError("Produto nao cadastrado no deposito informado.")
                MovimentacaoEstoque.objects.create(
                    company=self.request.tenant,
                    estoque=estoque_obj,
                    tipo=MovimentacaoEstoque.SAIDA,
                    quantidade=quantidade,
                    observacao=f"Consumo terceiro: {terceiro}" if terceiro else "Consumo terceiro",
                    created_by=self.request.user,
                    updated_by=self.request.user,
                )
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
