import base64
import json
import uuid
import binascii
from decimal import Decimal, InvalidOperation

from django.core.files.base import ContentFile
from django.contrib.auth.hashers import check_password
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.db import transaction
from django.utils import timezone
from django.http import JsonResponse, HttpResponseRedirect
from django.views import View
from django.template.loader import render_to_string
from django.urls import reverse

MAX_ASSINATURA_SIZE = 3 * 1024 * 1024  # 3MB

from apps.core.views import BaseTenantCreateView, BaseTenantListView
from apps.estoque.models import Estoque, MovimentacaoEstoque
from apps.funcionarios.models import Funcionario, FuncionarioHistorico, FuncionarioProduto
from apps.produtos.models import ProdutoFornecedor
from apps.tipos_funcionario.models import TipoFuncionarioProduto
from .forms import EntregaForm
from .models import Entrega, EntregaItem


class EntregaListView(BaseTenantListView):
    model = Entrega
    template_name = "entregas/list.html"
    form_class = None
    create_form_class = EntregaForm
    paginate_by = 10
    title = "Entregas"
    headers = [
        "Entrega",
        "Funcionario",
        "Data solicitada",
        "Data entrega",
        "Usuario",
        "Planta",
        "Situacao",
    ]
    row_fields = [
        "id",
        "funcionario",
        "created_at",
        "entregue_em",
        "created_by",
        "funcionario.planta",
        "status",
    ]
    filter_definitions = [
        {"name": "funcionario__nome", "label": "Funcionario", "lookup": "icontains", "type": "text"},
        {"name": "produto__nome", "label": "Produto", "lookup": "icontains", "type": "text"},
    ]
    create_url_name = "entregas:create"

    def get_queryset(self):
        queryset = super().get_queryset()
        planta_id = self.request.session.get("planta_id")
        if planta_id:
            queryset = queryset.filter(funcionario__planta_id=planta_id)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        planta_id = self.request.session.get("planta_id")
        if context.get("can_add"):
            context["create_form"] = self.create_form_class(tenant=self.request.tenant, planta_id=planta_id)
        else:
            context["create_form"] = None
        context["edit_rows"] = []
        context["solicitacao_url"] = reverse("entregas:solicitar")
        return context


class EntregaCreateView(BaseTenantCreateView):
    model = Entrega
    form_class = EntregaForm
    success_url_name = "entregas:list"

    def _parse_validacao_payload(self, payload):
        if not payload:
            return {}
        try:
            data = json.loads(payload)
        except json.JSONDecodeError:
            return {}
        if not isinstance(data, dict):
            return {}
        return {str(key): value for key, value in data.items() if value}

    def _decode_assinatura(self, raw_value):
        """
        Converte o payload base64 de assinatura em um ContentFile validando tipo e tamanho.
        """
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

    def _build_validacao_message(self, funcionarios, status):
        if any(func.validacao_recebimento == "assinatura" for func in funcionarios):
            if status == "invalid":
                return "Assinatura invalida para o funcionario informado."
            return "Assinatura do funcionario obrigatoria para concluir a entrega."
        if status == "invalid":
            return "Senha invalida para o funcionario informado."
        return "Informe a senha do funcionario para continuar."

    def _validate_recebimento(self, funcionario_ids, payload_map):
        self._assinatura_files = {}
        funcionarios = list(
            Funcionario.objects.filter(company=self.request.tenant, pk__in=funcionario_ids).only(
                "id",
                "nome",
                "validacao_recebimento",
                "senha_recebimento",
            )
        )
        assinaturas = {}
        required = []
        invalid = []
        for funcionario in funcionarios:
            tipo = funcionario.validacao_recebimento
            if tipo == "nenhum":
                continue
            required.append(funcionario)
            valor = (payload_map.get(str(funcionario.id)) or "").strip()
            if tipo == "senha":
                if not valor:
                    continue
                if not check_password(valor, funcionario.senha_recebimento or ""):
                    invalid.append(funcionario)
            if tipo == "assinatura":
                if not valor:
                    continue
                file_obj, error = self._decode_assinatura(valor)
                if error or not file_obj:
                    invalid.append(funcionario)
                else:
                    assinaturas[funcionario.id] = file_obj
        missing = [func for func in required if not (payload_map.get(str(func.id)) or "").strip()]
        if missing:
            self._assinatura_files = {}
            return False, "required", missing
        if invalid:
            self._assinatura_files = {}
            return False, "invalid", invalid
        self._assinatura_files = assinaturas
        return True, None, []

    def _apply_assinatura(self, entrega):
        assinatura_file = getattr(self, "_assinatura_files", {}).get(entrega.funcionario_id)
        if not assinatura_file:
            return
        if entrega.assinatura:
            entrega.assinatura.delete(save=False)
        assinatura_file.seek(0)
        entrega.assinatura.save(assinatura_file.name, assinatura_file, save=True)

    def _get_validacao_funcionario(self, funcionario_id):
        funcionario = (
            Funcionario.objects.filter(company=self.request.tenant, pk=funcionario_id)
            .only("validacao_recebimento")
            .first()
        )
        if not funcionario:
            return "nenhum"
        return funcionario.validacao_recebimento or "nenhum"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["tenant"] = self.request.tenant
        kwargs["planta_id"] = self.request.session.get("planta_id")
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

    def _is_produto_permitido(self, funcionario_id, produto_fornecedor):
        funcionario = Funcionario.objects.filter(
            company=self.request.tenant,
            pk=funcionario_id,
        ).select_related("tipo").first()
        if not funcionario:
            return False, "Funcionario invalido."
        permitido_funcionario = FuncionarioProduto.objects.filter(
            company=self.request.tenant,
            funcionario_id=funcionario_id,
            produto_fornecedor_id=produto_fornecedor.pk,
        ).exists()
        permitido_tipo = False
        if funcionario.tipo_id:
            permitido_tipo = TipoFuncionarioProduto.objects.filter(
                company=self.request.tenant,
                tipo_funcionario_id=funcionario.tipo_id,
                produto_fornecedor_id=produto_fornecedor.pk,
            ).exists()
        if permitido_funcionario or permitido_tipo:
            return True, None
        if not funcionario.tipo_id:
            return False, "Funcionario sem tipo definido."
        return False, "Produto nao liberado para o tipo ou para o funcionario."

    def _validate_and_create_items(self, items, form, allow_negative=False):
        result = self._validate_items(items, form, allow_negative=allow_negative)
        if result in (None, "confirm"):
            return result
        created, required_map = result

        primeiro = created[0]
        validacao_entrega = self._get_validacao_funcionario(primeiro["funcionario_id"])
        entrega = Entrega.objects.create(
            company=self.request.tenant,
            funcionario_id=primeiro["funcionario_id"],
            produto=primeiro["produto"],
            deposito_id=primeiro["deposito_id"],
            quantidade=primeiro["quantidade"],
            ca=primeiro["ca"],
            observacao=primeiro["observacao"],
            entregue_em=timezone.now(),
            created_by=self.request.user,
            updated_by=self.request.user,
            status="entregue",
            validacao_recebimento=validacao_entrega,
        )
        self._apply_assinatura(entrega)
        itens = []
        for item in created:
            itens.append(
                EntregaItem(
                    company=self.request.tenant,
                    entrega=entrega,
                    produto=item["produto"],
                    deposito_id=item["deposito_id"],
                    quantidade=item["quantidade"],
                    ca=item["ca"],
                    observacao=item["observacao"],
                    created_by=self.request.user,
                    updated_by=self.request.user,
                )
            )
            estoque_key = (item["produto"].pk, int(item["deposito_id"]))
            MovimentacaoEstoque.objects.create(
                company=self.request.tenant,
                estoque=required_map[estoque_key]["estoque"],
                tipo=MovimentacaoEstoque.SAIDA,
                quantidade=item["quantidade"],
                observacao=f"Entrega #{entrega.pk} para {entrega.funcionario}",
                created_by=self.request.user,
                updated_by=self.request.user,
            )
            FuncionarioHistorico.objects.create(
                company=self.request.tenant,
                funcionario=entrega.funcionario,
                descricao=(
                    f"Entrega: {item['produto']} (Qtd {item['quantidade']}) "
                    f"no deposito {required_map[estoque_key]['estoque'].deposito}."
                ),
                created_by=self.request.user,
                updated_by=self.request.user,
            )
        EntregaItem.objects.bulk_create(itens)
        return entrega

    def _validate_items(self, items, form, allow_negative=False):
        errors = []
        created = []
        required_map = {}
        confirm_items = []
        funcionario_ref = None

        for idx, item in enumerate(items, start=1):
            funcionario_id = item.get("funcionario_id")
            deposito_id = item.get("deposito_id")
            produto_fornecedor_id = item.get("produto_fornecedor_id")
            quantidade_raw = item.get("quantidade")
            if not funcionario_id or not deposito_id or not produto_fornecedor_id or not quantidade_raw:
                errors.append(f"Item {idx}: preencha funcionario, produto, deposito e quantidade.")
                continue
            if funcionario_ref is None:
                funcionario_ref = funcionario_id
            elif str(funcionario_ref) != str(funcionario_id):
                errors.append("Todos os itens devem pertencer ao mesmo funcionario.")
                continue
            try:
                quantidade = Decimal(str(quantidade_raw))
            except (InvalidOperation, ValueError):
                errors.append(f"Item {idx}: quantidade invalida.")
                continue
            if quantidade <= 0:
                errors.append(f"Item {idx}: quantidade deve ser maior que zero.")
                continue
            produto_fornecedor = (
                ProdutoFornecedor.objects.filter(company=self.request.tenant, pk=produto_fornecedor_id)
                .select_related("produto")
                .first()
            )
            if not produto_fornecedor:
                errors.append(f"Item {idx}: produto/CA invalido.")
                continue
            permitido, motivo = self._is_produto_permitido(funcionario_id, produto_fornecedor)
            if not permitido:
                errors.append(f"Item {idx}: {motivo}")
                continue
            estoque_filters = {
                "company": self.request.tenant,
                "produto": produto_fornecedor.produto,
                "deposito_id": deposito_id,
            }
            planta_id = self.request.session.get("planta_id")
            if planta_id:
                estoque_filters["deposito__planta_id"] = planta_id
            estoque = Estoque.objects.filter(**estoque_filters).select_related("deposito").first()
            if not estoque:
                errors.append(f"Item {idx}: nao existe estoque para este produto no deposito informado.")
                continue
            key = (produto_fornecedor.produto_id, int(deposito_id))
            required_map[key] = {
                "estoque": estoque,
                "quantidade": required_map.get(key, {}).get("quantidade", Decimal("0")) + quantidade,
                "produto_label": f"{produto_fornecedor.produto} | CA {produto_fornecedor.ca or '-'}",
                "deposito_label": estoque.deposito.nome if estoque.deposito_id else "-",
            }
            created.append(
                {
                    "funcionario_id": funcionario_id,
                    "deposito_id": deposito_id,
                    "produto": produto_fornecedor.produto,
                    "quantidade": quantidade,
                    "ca": produto_fornecedor.ca or "",
                    "observacao": item.get("observacao") or "",
                }
            )

        if errors:
            for error in errors:
                form.add_error(None, error)
            return None

        for key, payload in required_map.items():
            estoque = (
                Estoque.objects.select_for_update()
                .filter(pk=payload["estoque"].pk)
                .first()
            )
            if not estoque:
                form.add_error(None, "Nao existe estoque para um dos itens.")
                return None
            if estoque.deposito and estoque.deposito.bloquear_movimento_negativo:
                if payload["quantidade"] > estoque.quantidade:
                    deposito_label = payload.get("deposito_label") or "deposito informado"
                    form.add_error(
                        None,
                        f"Movimento negativo bloqueado para o deposito {deposito_label}.",
                    )
                    return None
            if not allow_negative and payload["quantidade"] > estoque.quantidade:
                confirm_items.append(
                    {
                        "produto": payload.get("produto_label", "-"),
                        "deposito": payload.get("deposito_label", "-"),
                        "quantidade": str(payload["quantidade"]),
                        "estoque": str(estoque.quantidade),
                    }
                )
            payload["estoque"] = estoque

        if confirm_items and not allow_negative:
            self._confirm_items = confirm_items
            return "confirm"

        return created, required_map

    def post(self, request, *args, **kwargs):
        payload = request.POST.get("itens_payload")
        allow_negative = request.POST.get("allow_negative") == "1"
        validacao_payload = self._parse_validacao_payload(request.POST.get("validacao_payload"))
        if payload:
            form = self.get_form()
            items, error = self._parse_items_payload(payload)
            if error:
                form.add_error(None, error)
                return self.form_invalid(form)
            funcionario_ids = list(
                {str(item.get("funcionario_id")) for item in items if item.get("funcionario_id")}
            )
            if funcionario_ids:
                ok, status, funcionarios = self._validate_recebimento(funcionario_ids, validacao_payload)
                if not ok:
                    message = self._build_validacao_message(funcionarios, status)
                    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                        return JsonResponse(
                            {
                                "ok": False,
                                "validate": True,
                                "message": message,
                                "funcionarios": [
                                    {
                                        "id": func.id,
                                        "nome": func.nome,
                                        "validacao": func.validacao_recebimento,
                                    }
                                    for func in funcionarios
                                ],
                                "invalid": status == "invalid",
                            },
                        )
                    form.add_error(None, message)
                    return self.form_invalid(form)
            with transaction.atomic():
                self._confirm_items = []
                entrega = self._validate_and_create_items(items, form, allow_negative=allow_negative)
                if entrega == "confirm":
                    message = "Item com estoque zero, deseja continuar?"
                    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                        return JsonResponse(
                            {
                                "ok": False,
                                "confirm": True,
                                "message": message,
                                "confirm_items": self._confirm_items,
                            },
                        )
                    form.add_error(None, message)
                    return self.form_invalid(form)
                if not entrega:
                    return self.form_invalid(form)
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                row_html = render_to_string(
                    "entregas/_entrega_row.html",
                    {"entrega": entrega},
                    request=request,
                )
                form_html = render_to_string(
                    "entregas/_entrega_form.html",
                    {
                        "form": self.form_class(tenant=request.tenant, planta_id=request.session.get("planta_id")),
                        "form_action": reverse("entregas:create"),
                        "form_hide_actions": True,
                        "form_id": "entrega-form",
                    },
                    request=request,
                )
                return JsonResponse(
                    {
                        "ok": True,
                        "action": "create",
                        "row_id": entrega.pk,
                        "row_html": row_html,
                        "form_html": form_html,
                    }
                )
            return HttpResponseRedirect(self.get_success_url())
        return super().post(request, *args, **kwargs)

    def form_valid(self, form):
        produto_fornecedor = form.cleaned_data.get("produto_fornecedor")
        entrega = form.save(commit=False)
        if entrega.entregue_em is None:
            entrega.entregue_em = timezone.now()
        produto = entrega.produto
        deposito = entrega.deposito
        quantidade = entrega.quantidade
        allow_negative = self.request.POST.get("allow_negative") == "1"
        validacao_payload = self._parse_validacao_payload(self.request.POST.get("validacao_payload"))
        if not produto_fornecedor:
            form.add_error("produto_fornecedor", "Selecione o produto.")
            return self.form_invalid(form)
        if entrega.funcionario_id:
            ok, status, funcionarios = self._validate_recebimento([str(entrega.funcionario_id)], validacao_payload)
            if not ok:
                message = self._build_validacao_message(funcionarios, status)
                if self.request.headers.get("X-Requested-With") == "XMLHttpRequest":
                    return JsonResponse(
                        {
                            "ok": False,
                            "validate": True,
                            "message": message,
                            "funcionarios": [
                                {
                                    "id": func.id,
                                    "nome": func.nome,
                                    "validacao": func.validacao_recebimento,
                                }
                                for func in funcionarios
                            ],
                            "invalid": status == "invalid",
                        },
                )
                form.add_error(None, message)
                return self.form_invalid(form)
            entrega.validacao_recebimento = entrega.funcionario.validacao_recebimento or "nenhum"
        permitido, motivo = self._is_produto_permitido(entrega.funcionario_id, produto_fornecedor)
        if not permitido:
            form.add_error(None, motivo)
            return self.form_invalid(form)
        estoque_filters = {
            "company": self.request.tenant,
            "produto": produto,
            "deposito": deposito,
        }
        planta_id = self.request.session.get("planta_id")
        if planta_id:
            estoque_filters["deposito__planta_id"] = planta_id
        estoque = Estoque.objects.filter(**estoque_filters).first()
        if not estoque:
            form.add_error("deposito", "Nao existe estoque para este produto no deposito informado.")
            return self.form_invalid(form)
        if deposito and deposito.bloquear_movimento_negativo and quantidade > estoque.quantidade:
            deposito_label = deposito.nome if deposito else "deposito informado"
            form.add_error(None, f"Movimento negativo bloqueado para o deposito {deposito_label}.")
            return self.form_invalid(form)
        if not allow_negative and (estoque.quantidade <= 0 or quantidade > estoque.quantidade):
            message = "Item com estoque zero, deseja continuar?"
            if self.request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return JsonResponse(
                    {
                        "ok": False,
                        "confirm": True,
                        "message": message,
                        "confirm_items": [
                            {
                                "produto": f"{produto_fornecedor.produto} | CA {produto_fornecedor.ca or '-'}",
                                "deposito": deposito.nome if deposito else "-",
                                "quantidade": str(quantidade),
                                "estoque": str(estoque.quantidade),
                            }
                        ],
                    },
                )
            form.add_error(None, message)
            return self.form_invalid(form)
        with transaction.atomic():
            response = super().form_valid(form)
            self._apply_assinatura(self.object)
            EntregaItem.objects.create(
                company=self.request.tenant,
                entrega=self.object,
                produto=produto,
                deposito=deposito,
                quantidade=quantidade,
                ca=self.object.ca or "",
                observacao=self.object.observacao or "",
                created_by=self.request.user,
                updated_by=self.request.user,
            )
            MovimentacaoEstoque.objects.create(
                company=self.request.tenant,
                estoque=estoque,
                tipo=MovimentacaoEstoque.SAIDA,
                quantidade=quantidade,
                observacao=f"Entrega #{self.object.pk} para {self.object.funcionario}",
                created_by=self.request.user,
                updated_by=self.request.user,
            )
            FuncionarioHistorico.objects.create(
                company=self.request.tenant,
                funcionario=self.object.funcionario,
                descricao=(
                    f"Entrega: {self.object.produto} (Qtd {self.object.quantidade}) "
                    f"no deposito {self.object.deposito}."
                ),
                created_by=self.request.user,
                updated_by=self.request.user,
            )
        if self.request.headers.get("X-Requested-With") == "XMLHttpRequest":
            row_html = render_to_string(
                "entregas/_entrega_row.html",
                {"entrega": self.object},
                request=self.request,
            )
            form_html = render_to_string(
                "entregas/_entrega_form.html",
                {
                    "form": self.form_class(tenant=self.request.tenant, planta_id=self.request.session.get("planta_id")),
                    "form_action": reverse("entregas:create"),
                    "form_hide_actions": True,
                    "form_id": "entrega-form",
                },
                request=self.request,
            )
            return JsonResponse(
                {
                    "ok": True,
                    "action": "create",
                    "row_id": self.object.pk,
                    "row_html": row_html,
                    "form_html": form_html,
                }
            )
        return response

    def form_invalid(self, form):
        if self.request.headers.get("X-Requested-With") == "XMLHttpRequest":
            form_html = render_to_string(
                "entregas/_entrega_form.html",
                {
                    "form": form,
                    "form_action": reverse("entregas:create"),
                    "form_hide_actions": True,
                    "form_id": "entrega-form",
                },
                request=self.request,
            )
            return JsonResponse({"ok": False, "form_html": form_html}, status=400)
        return super().form_invalid(form)


class EntregaDepositosView(PermissionRequiredMixin, View):
    permission_required = "entregas.view_entrega"

    def get(self, request):
        produto_fornecedor_id = request.GET.get("produto_fornecedor_id")
        if not produto_fornecedor_id:
            return JsonResponse({"ok": False, "depositos": []})
        produto_fornecedor = ProdutoFornecedor.objects.filter(
            company=request.tenant,
            pk=produto_fornecedor_id,
        ).select_related("produto").first()
        if not produto_fornecedor:
            return JsonResponse({"ok": False, "depositos": []})
        depositos_filters = {
            "company": request.tenant,
            "produto": produto_fornecedor.produto,
            "deposito__ativo": True,
        }
        planta_id = request.session.get("planta_id")
        if planta_id:
            depositos_filters["deposito__planta_id"] = planta_id
        depositos = (
            Estoque.objects.filter(**depositos_filters)
            .select_related("deposito")
            .order_by("deposito__nome")
        )
        items = [{"id": item.deposito_id, "nome": item.deposito.nome} for item in depositos]
        return JsonResponse({"ok": True, "depositos": items})


class EntregaProdutosView(PermissionRequiredMixin, View):
    permission_required = "entregas.view_entrega"

    def get(self, request):
        funcionario_id = request.GET.get("funcionario_id")
        if not funcionario_id:
            return JsonResponse({"ok": False, "produtos": []})
        funcionario = Funcionario.objects.filter(
            company=request.tenant,
            pk=funcionario_id,
        ).select_related("tipo").first()
        if not funcionario:
            return JsonResponse({"ok": False, "produtos": []})
        funcionario_ids = FuncionarioProduto.objects.filter(
            company=request.tenant,
            funcionario_id=funcionario.pk,
            produto_fornecedor__produto__ativo=True,
        ).values_list("produto_fornecedor_id", flat=True)
        tipo_ids = []
        if funcionario.tipo_id:
            tipo_ids = TipoFuncionarioProduto.objects.filter(
                company=request.tenant,
                tipo_funcionario_id=funcionario.tipo_id,
                produto_fornecedor__produto__ativo=True,
            ).values_list("produto_fornecedor_id", flat=True)
        produto_ids = set(funcionario_ids) | set(tipo_ids)
        if not produto_ids:
            return JsonResponse({"ok": False, "produtos": []})
        produtos = (
            ProdutoFornecedor.objects.filter(company=request.tenant, pk__in=produto_ids, produto__ativo=True)
            .select_related("produto", "fornecedor")
            .order_by("produto__nome")
        )
        items = [
            {
                "id": item.pk,
                "label": f"{item.produto} | CA {item.ca or '-'} | {item.fornecedor}",
            }
            for item in produtos
        ]
        return JsonResponse({"ok": True, "produtos": items})


class EntregaDetailView(PermissionRequiredMixin, View):
    permission_required = "entregas.view_entrega"

    def get(self, request, pk):
        entrega = Entrega.objects.filter(pk=pk, company=request.tenant).select_related(
            "funcionario",
            "funcionario__centro_custo",
            "funcionario__setor",
            "funcionario__ghe",
            "funcionario__cargo",
            "funcionario__lider",
            "funcionario__gestor",
            "funcionario__planta",
            "deposito",
            "produto",
            "produto__periodicidade",
        ).first()
        if not entrega:
            return JsonResponse({"ok": False}, status=404)

        itens_qs = entrega.itens.select_related("produto", "deposito", "produto__periodicidade")
        itens = []
        total_quantidade = Decimal("0")
        total_valor = Decimal("0")
        total_valor_ok = True
        depositos = set()

        if not itens_qs.exists():
            itens_qs = [
                EntregaItem(
                    entrega=entrega,
                    produto=entrega.produto,
                    deposito=entrega.deposito,
                    quantidade=entrega.quantidade,
                    ca=entrega.ca or "",
                    observacao=entrega.observacao or "",
                )
            ]

        for item in itens_qs:
            if item.deposito:
                depositos.add(item.deposito.nome)
            produto = item.produto
            produto_fornecedor = ProdutoFornecedor.objects.filter(
                company=request.tenant,
                produto=produto,
            )
            if item.ca:
                produto_fornecedor = produto_fornecedor.filter(ca=item.ca)
            produto_fornecedor = produto_fornecedor.select_related("fornecedor").order_by("pk").first()
            valor_unitario = produto_fornecedor.valor if produto_fornecedor else None
            total_item = None
            if valor_unitario is not None:
                total_item = valor_unitario * item.quantidade
            if total_item is None:
                total_valor_ok = False
            else:
                total_valor += total_item
            total_quantidade += item.quantidade

            periodicidade_label = "-"
            data_troca = None
            if produto:
                periodicidade_label = produto.periodicidade_label()
                if produto.periodicidade and entrega.entregue_em:
                    dias = (produto.periodicidade_quantidade or 0) * (
                        produto.periodicidade.fator_dias or 0
                    )
                    if dias:
                        data_troca = entrega.entregue_em + timezone.timedelta(days=dias)

            codigo = "-"
            if produto:
                codigo = getattr(produto, "codigo", "") or "-"

            itens.append(
                {
                    "codigo": codigo,
                    "produto": produto,
                    "quantidade": item.quantidade,
                    "valor_unitario": valor_unitario,
                    "total_item": total_item,
                    "grade": "Sem Grade",
                    "ca": item.ca or "-",
                    "epi": "Sim" if produto and produto.controle_epi else "Nao",
                    "periodicidade": periodicidade_label,
                    "data_troca": data_troca,
                }
            )

        deposito_label = "-"
        if len(depositos) == 1:
            deposito_label = list(depositos)[0]
        elif len(depositos) > 1:
            deposito_label = "Varios"

        context = {
            "entrega": entrega,
            "itens": itens,
            "total_quantidade": total_quantidade,
            "total_valor": total_valor if total_valor_ok else None,
            "deposito_label": deposito_label,
            "empresa_nome": getattr(request.tenant, "name", "-"),
        }
        html = render_to_string(
            "entregas/_entrega_detail.html",
            context,
            request=request,
        )
        return JsonResponse({"ok": True, "html": html})


class EntregaSolicitacaoCreateView(EntregaCreateView):
    success_url_name = "entregas:list"

    def post(self, request, *args, **kwargs):
        payload = request.POST.get("itens_payload")
        if payload:
            form = self.get_form()
            items, error = self._parse_items_payload(payload)
            if error:
                form.add_error(None, error)
                return self.form_invalid(form)
            with transaction.atomic():
                entrega = self._validate_and_create_items(items, form)
                if not entrega:
                    return self.form_invalid(form)
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                row_html = render_to_string(
                    "entregas/_entrega_row.html",
                    {"entrega": entrega},
                    request=request,
                )
                form_html = render_to_string(
                    "entregas/_entrega_form.html",
                    {
                        "form": self.form_class(tenant=request.tenant, planta_id=request.session.get("planta_id")),
                        "form_action": reverse("entregas:solicitar"),
                        "form_hide_actions": True,
                        "form_id": "entrega-form",
                    },
                    request=request,
                )
                return JsonResponse(
                    {
                        "ok": True,
                        "action": "create",
                        "row_id": entrega.pk,
                        "row_html": row_html,
                        "form_html": form_html,
                    }
                )
            return HttpResponseRedirect(self.get_success_url())
        return super().post(request, *args, **kwargs)

    def _validate_and_create_items(self, items, form, allow_negative=False):
        errors = []
        created = []
        funcionario_ref = None

        for idx, item in enumerate(items, start=1):
            funcionario_id = item.get("funcionario_id")
            deposito_id = item.get("deposito_id")
            produto_fornecedor_id = item.get("produto_fornecedor_id")
            quantidade_raw = item.get("quantidade")
            if not funcionario_id or not deposito_id or not produto_fornecedor_id or not quantidade_raw:
                errors.append(f"Item {idx}: preencha funcionario, produto, deposito e quantidade.")
                continue
            if funcionario_ref is None:
                funcionario_ref = funcionario_id
            elif str(funcionario_ref) != str(funcionario_id):
                errors.append("Todos os itens devem pertencer ao mesmo funcionario.")
                continue
            try:
                quantidade = Decimal(str(quantidade_raw))
            except (InvalidOperation, ValueError):
                errors.append(f"Item {idx}: quantidade invalida.")
                continue
            if quantidade <= 0:
                errors.append(f"Item {idx}: quantidade deve ser maior que zero.")
                continue
            produto_fornecedor = (
                ProdutoFornecedor.objects.filter(company=self.request.tenant, pk=produto_fornecedor_id)
                .select_related("produto")
                .first()
            )
            if not produto_fornecedor:
                errors.append(f"Item {idx}: produto/CA invalido.")
                continue
            permitido, motivo = self._is_produto_permitido(funcionario_id, produto_fornecedor)
            if not permitido:
                errors.append(f"Item {idx}: {motivo}")
                continue
            created.append(
                {
                    "funcionario_id": funcionario_id,
                    "deposito_id": deposito_id,
                    "produto": produto_fornecedor.produto,
                    "quantidade": quantidade,
                    "ca": produto_fornecedor.ca or "",
                    "observacao": item.get("observacao") or "",
                }
            )

        if errors:
            for error in errors:
                form.add_error(None, error)
            return None

        primeiro = created[0]
        entrega = Entrega.objects.create(
            company=self.request.tenant,
            funcionario_id=primeiro["funcionario_id"],
            produto=primeiro["produto"],
            deposito_id=primeiro["deposito_id"],
            quantidade=primeiro["quantidade"],
            ca=primeiro["ca"],
            observacao=primeiro["observacao"],
            entregue_em=None,
            created_by=self.request.user,
            updated_by=self.request.user,
            status="aguardando",
        )
        itens = []
        for item in created:
            itens.append(
                EntregaItem(
                    company=self.request.tenant,
                    entrega=entrega,
                    produto=item["produto"],
                    deposito_id=item["deposito_id"],
                    quantidade=item["quantidade"],
                    ca=item["ca"],
                    observacao=item["observacao"],
                    created_by=self.request.user,
                    updated_by=self.request.user,
                )
            )
        EntregaItem.objects.bulk_create(itens)
        return entrega

    def form_valid(self, form):
        produto_fornecedor = form.cleaned_data.get("produto_fornecedor")
        entrega = form.save(commit=False)
        entrega.entregue_em = None
        if not produto_fornecedor:
            form.add_error("produto_fornecedor", "Selecione o produto.")
            return self.form_invalid(form)
        permitido, motivo = self._is_produto_permitido(entrega.funcionario_id, produto_fornecedor)
        if not permitido:
            form.add_error(None, motivo)
            return self.form_invalid(form)
        with transaction.atomic():
            entrega.status = "aguardando"
            response = BaseTenantCreateView.form_valid(self, form)
            EntregaItem.objects.create(
                company=self.request.tenant,
                entrega=self.object,
                produto=self.object.produto,
                deposito=self.object.deposito,
                quantidade=self.object.quantidade,
                ca=self.object.ca or "",
                observacao=self.object.observacao or "",
                created_by=self.request.user,
                updated_by=self.request.user,
            )
        if self.request.headers.get("X-Requested-With") == "XMLHttpRequest":
            row_html = render_to_string(
                "entregas/_entrega_row.html",
                {"entrega": self.object},
                request=self.request,
            )
            form_html = render_to_string(
                "entregas/_entrega_form.html",
                {
                    "form": self.form_class(tenant=self.request.tenant, planta_id=self.request.session.get("planta_id")),
                    "form_action": reverse("entregas:solicitar"),
                    "form_hide_actions": True,
                    "form_id": "entrega-form",
                },
                request=self.request,
            )
            return JsonResponse(
                {
                    "ok": True,
                    "action": "create",
                    "row_id": self.object.pk,
                    "row_html": row_html,
                    "form_html": form_html,
                }
            )
        return response


class EntregaItensView(PermissionRequiredMixin, View):
    permission_required = "entregas.view_entrega"

    def get(self, request, pk):
        entrega = Entrega.objects.filter(pk=pk, company=request.tenant).select_related("funcionario").first()
        if not entrega:
            return JsonResponse({"ok": False}, status=404)
        itens = entrega.itens.select_related("produto", "deposito").all()
        items_payload = []
        for item in itens:
            produto_fornecedor = ProdutoFornecedor.objects.filter(
                company=request.tenant,
                produto=item.produto,
            )
            if item.ca:
                produto_fornecedor = produto_fornecedor.filter(ca=item.ca)
            produto_fornecedor = produto_fornecedor.select_related("fornecedor").order_by("pk").first()
            produto_fornecedor_id = produto_fornecedor.pk if produto_fornecedor else ""
            produto_label = "-"
            if produto_fornecedor:
                produto_label = (
                    f"{produto_fornecedor.produto} | CA {produto_fornecedor.ca or '-'} | "
                    f"{produto_fornecedor.fornecedor}"
                )
            items_payload.append(
                {
                    "funcionario_id": entrega.funcionario_id,
                    "funcionario_label": str(entrega.funcionario),
                    "produto_fornecedor_id": produto_fornecedor_id,
                    "produto_fornecedor_label": produto_label,
                    "deposito_id": item.deposito_id,
                    "deposito_label": str(item.deposito),
                    "quantidade": str(item.quantidade),
                    "observacao": item.observacao or "",
                }
            )
        return JsonResponse({"ok": True, "items": items_payload})


class EntregaAtenderView(EntregaCreateView):
    success_url_name = "entregas:list"

    def post(self, request, pk, *args, **kwargs):
        entrega = Entrega.objects.filter(pk=pk, company=request.tenant).select_related("funcionario").first()
        if not entrega:
            return JsonResponse({"ok": False}, status=404)
        if entrega.status != "aguardando":
            return JsonResponse({"ok": False, "message": "Entrega nao esta aguardando."}, status=400)
        payload = request.POST.get("itens_payload")
        allow_negative = request.POST.get("allow_negative") == "1"
        validacao_payload = self._parse_validacao_payload(request.POST.get("validacao_payload"))
        if not payload:
            return JsonResponse({"ok": False, "message": "Itens obrigatorios."}, status=400)
        form = self.get_form()
        items, error = self._parse_items_payload(payload)
        if error:
            form.add_error(None, error)
            return self.form_invalid(form)
        funcionario_ids = list(
            {str(item.get("funcionario_id")) for item in items if item.get("funcionario_id")}
        )
        if funcionario_ids and str(entrega.funcionario_id) not in funcionario_ids:
            return JsonResponse({"ok": False, "message": "Funcionario invalido para esta entrega."}, status=400)
        if funcionario_ids:
            ok, status, funcionarios = self._validate_recebimento(funcionario_ids, validacao_payload)
            if not ok:
                message = self._build_validacao_message(funcionarios, status)
                if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                    return JsonResponse(
                        {
                            "ok": False,
                            "validate": True,
                            "message": message,
                            "funcionarios": [
                                {
                                    "id": func.id,
                                    "nome": func.nome,
                                    "validacao": func.validacao_recebimento,
                                }
                                for func in funcionarios
                            ],
                            "invalid": status == "invalid",
                        },
                    )
                form.add_error(None, message)
                return self.form_invalid(form)
        with transaction.atomic():
            self._confirm_items = []
            result = self._validate_items(items, form, allow_negative=allow_negative)
            if result == "confirm":
                message = "Item com estoque zero, deseja continuar?"
                if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                    return JsonResponse(
                        {
                            "ok": False,
                            "confirm": True,
                            "message": message,
                            "confirm_items": self._confirm_items,
                        },
                    )
                form.add_error(None, message)
                return self.form_invalid(form)
            if not result:
                return self.form_invalid(form)
            created, required_map = result
            EntregaItem.objects.filter(entrega=entrega).delete()
            itens = []
            for item in created:
                itens.append(
                    EntregaItem(
                        company=request.tenant,
                        entrega=entrega,
                        produto=item["produto"],
                        deposito_id=item["deposito_id"],
                        quantidade=item["quantidade"],
                        ca=item["ca"],
                        observacao=item["observacao"],
                        created_by=request.user,
                        updated_by=request.user,
                    )
                )
                estoque_key = (item["produto"].pk, int(item["deposito_id"]))
                MovimentacaoEstoque.objects.create(
                    company=request.tenant,
                    estoque=required_map[estoque_key]["estoque"],
                    tipo=MovimentacaoEstoque.SAIDA,
                    quantidade=item["quantidade"],
                    observacao=f"Entrega #{entrega.pk} para {entrega.funcionario}",
                    created_by=request.user,
                    updated_by=request.user,
                )
                FuncionarioHistorico.objects.create(
                    company=request.tenant,
                    funcionario=entrega.funcionario,
                    descricao=(
                        f"Entrega: {item['produto']} (Qtd {item['quantidade']}) "
                        f"no deposito {required_map[estoque_key]['estoque'].deposito}."
                    ),
                    created_by=request.user,
                    updated_by=request.user,
                )
            EntregaItem.objects.bulk_create(itens)
            primeiro = created[0]
            entrega.produto = primeiro["produto"]
            entrega.deposito_id = primeiro["deposito_id"]
            entrega.quantidade = primeiro["quantidade"]
            entrega.ca = primeiro["ca"]
            entrega.observacao = primeiro["observacao"]
            entrega.status = "entregue"
            entrega.entregue_em = timezone.now()
            entrega.updated_by = request.user
            entrega.validacao_recebimento = self._get_validacao_funcionario(entrega.funcionario_id)
            entrega.save(
                update_fields=[
                    "produto",
                    "deposito",
                    "quantidade",
                    "ca",
                    "observacao",
                    "status",
                    "entregue_em",
                    "validacao_recebimento",
                    "updated_by",
                ]
            )
            self._apply_assinatura(entrega)
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            row_html = render_to_string(
                "entregas/_entrega_row.html",
                {"entrega": entrega},
                request=request,
            )
            return JsonResponse({"ok": True, "row_id": entrega.pk, "row_html": row_html})
        return HttpResponseRedirect(reverse("entregas:list"))


class EntregaCancelView(PermissionRequiredMixin, View):
    permission_required = "entregas.delete_entrega"

    def post(self, request, pk):
        entrega = Entrega.objects.filter(pk=pk, company=request.tenant).select_related(
            "produto",
            "deposito",
            "funcionario",
        ).first()
        if not entrega:
            return JsonResponse({"ok": False}, status=404)
        motivo = (request.POST.get("motivo_cancelamento") or "").strip()
        if not motivo:
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return JsonResponse(
                    {"ok": False, "message": "Informe o motivo do cancelamento."},
                    status=400,
                )
            return HttpResponseRedirect(reverse("entregas:list"))
        if entrega.status == "cancelada":
            row_html = render_to_string(
                "entregas/_entrega_row.html",
                {"entrega": entrega},
                request=request,
            )
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return JsonResponse(
                    {
                        "ok": True,
                        "row_id": pk,
                        "row_html": row_html,
                        "motivo_cancelamento": entrega.motivo_cancelamento,
                    }
                )
            return HttpResponseRedirect(reverse("entregas:list"))
        with transaction.atomic():
            itens_qs = entrega.itens.select_related("produto", "deposito")
            if not itens_qs.exists():
                itens_qs = [
                    EntregaItem(
                        entrega=entrega,
                        produto=entrega.produto,
                        deposito=entrega.deposito,
                        quantidade=entrega.quantidade,
                        ca=entrega.ca or "",
                        observacao=entrega.observacao or "",
                    )
                ]
            for item in itens_qs:
                estoque, _ = Estoque.objects.select_for_update().get_or_create(
                    company=request.tenant,
                    produto=item.produto,
                    deposito=item.deposito,
                    defaults={"quantidade": 0},
                )
                MovimentacaoEstoque.objects.create(
                    company=request.tenant,
                    estoque=estoque,
                    tipo=MovimentacaoEstoque.ENTRADA,
                    quantidade=item.quantidade,
                    observacao=f"Cancelamento da entrega #{entrega.pk}",
                    created_by=request.user,
                    updated_by=request.user,
                )
                FuncionarioHistorico.objects.create(
                    company=request.tenant,
                    funcionario=entrega.funcionario,
                    descricao=(
                        f"Entrega cancelada: {item.produto} (Qtd {item.quantidade}) "
                        f"no deposito {item.deposito}."
                    ),
                    created_by=request.user,
                    updated_by=request.user,
                )
            entrega.status = "cancelada"
            entrega.motivo_cancelamento = motivo
            entrega.updated_by = request.user
            entrega.save(update_fields=["status", "motivo_cancelamento", "updated_by"])
        row_html = render_to_string(
            "entregas/_entrega_row.html",
            {"entrega": entrega},
            request=request,
        )
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse(
                {
                    "ok": True,
                    "row_id": pk,
                    "row_html": row_html,
                    "motivo_cancelamento": entrega.motivo_cancelamento,
                }
            )
        return HttpResponseRedirect(reverse("entregas:list"))
