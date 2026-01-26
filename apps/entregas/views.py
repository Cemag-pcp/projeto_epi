import base64
import json
import logging
import uuid
import binascii
from decimal import Decimal, InvalidOperation

from django.core.files.base import ContentFile
from django.contrib.auth.hashers import check_password
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.db import transaction
from django.db.models import Max, Sum
from django.utils import timezone
from django.http import JsonResponse, HttpResponseRedirect
from django.views import View
from django.template.loader import render_to_string
from django.urls import reverse

logger = logging.getLogger(__name__)

MAX_ASSINATURA_SIZE = 3 * 1024 * 1024  # 3MB

from apps.core.views import BaseTenantCreateView, BaseTenantListView
from apps.estoque.models import Estoque, MovimentacaoEstoque
from apps.funcionarios.models import Funcionario, FuncionarioHistorico, FuncionarioProduto
from apps.produtos.models import ProdutoFornecedor
from apps.tipos_funcionario.models import TipoFuncionarioProduto
from .forms import EntregaForm
from .models import Devolucao, DevolucaoItem, Entrega, EntregaItem


def _get_or_create_estoque_for_update(*, request, produto, deposito, grade):
    """
    Retorna um unico Estoque (lockado) para (company, produto, deposito, grade).
    Se houver duplicidade, retorna (None, mensagem) para evitar movimentar o estoque errado.
    """
    qs = Estoque.objects.select_for_update().filter(
        company=request.tenant,
        produto=produto,
        deposito=deposito,
        grade=(grade or "").strip(),
    )
    ids = list(qs.values_list("pk", flat=True)[:2])
    if len(ids) > 1:
        produto_label = str(produto) if produto else "-"
        deposito_label = str(deposito) if deposito else "-"
        grade_label = (grade or "").strip() or "(Sem Grade)"
        return None, (
            "Existe mais de um estoque para este produto/deposito/grade. "
            f"Produto: {produto_label} | Deposito: {deposito_label} | Grade: {grade_label}. "
            "Consolide os registros de estoque duplicados."
        )
    if ids:
        return qs.get(pk=ids[0]), None
    estoque = Estoque.objects.create(
        company=request.tenant,
        produto=produto,
        deposito=deposito,
        grade=(grade or "").strip(),
        quantidade=Decimal("0"),
        created_by=request.user,
        updated_by=request.user,
    )
    return estoque, None


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
        context["can_devolver"] = self.request.user.has_perm("entregas.add_devolucao")
        if context["can_devolver"]:
            funcionarios = Funcionario.objects.filter(company=self.request.tenant, ativo=True)
            if planta_id:
                funcionarios = funcionarios.filter(planta_id=planta_id)
            context["devolucao_funcionarios"] = funcionarios.order_by("nome").only("id", "nome", "registro")
        else:
            context["devolucao_funcionarios"] = []
        context["devolucao_itens_url"] = reverse("entregas:devolucao_itens")
        context["devolucao_confirmar_url"] = reverse("entregas:devolucao_confirmar")
        context["condicao_choices"] = DevolucaoItem.CONDICAO_CHOICES
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
            logger.warning("Entrega validacao_payload com JSON invalido.")
            return {}
        if not isinstance(data, dict):
            logger.warning("Entrega validacao_payload nao eh dict (type=%s).", type(data).__name__)
            return {}
        return {str(key): value for key, value in data.items() if value}

    def _decode_assinatura(self, raw_value):
        """
        Converte o payload base64 de assinatura em um ContentFile validando tipo e tamanho.
        """
        if not raw_value or not isinstance(raw_value, str):
            logger.warning(
                "Entrega assinatura ausente/invalida (type=%s).",
                type(raw_value).__name__,
            )
            return None, "Assinatura obrigatoria."
        base64_data = raw_value
        extension = "png"
        if raw_value.startswith("data:"):
            try:
                header, base64_data = raw_value.split(",", 1)
            except ValueError:
                logger.warning("Entrega assinatura com header data: invalido (sem virgula).")
                return None, "Assinatura invalida."
            if "jpeg" in header or "jpg" in header:
                extension = "jpg"
            elif "webp" in header:
                extension = "webp"
        try:
            decoded = base64.b64decode(base64_data)
        except (binascii.Error, ValueError):
            logger.warning("Entrega assinatura com base64 invalido (len=%s).", len(base64_data or ""))
            return None, "Assinatura invalida."
        if len(decoded) > MAX_ASSINATURA_SIZE:
            logger.warning("Entrega assinatura excede limite (bytes=%s).", len(decoded))
            return None, "Assinatura excede o limite de 3MB."
        filename = f"assinatura-{uuid.uuid4().hex[:12]}.{extension}"
        logger.warning("Entrega assinatura decodificada (bytes=%s, ext=%s, name=%s).", len(decoded), extension, filename)
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
        logger.warning(
            "Entrega validar recebimento: funcionario_ids=%s payload_keys=%s",
            list(funcionario_ids),
            sorted(list(payload_map.keys())),
        )
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
                logger.warning(
                    "Entrega validar recebimento (senha): funcionario_id=%s valor_presente=%s",
                    funcionario.id,
                    bool(valor),
                )
                if not valor:
                    continue
                if not check_password(valor, funcionario.senha_recebimento or ""):
                    invalid.append(funcionario)
            if tipo == "assinatura":
                logger.warning(
                    "Entrega validar recebimento (assinatura): funcionario_id=%s valor_presente=%s len=%s",
                    funcionario.id,
                    bool(valor),
                    len(valor or ""),
                )
                if not valor:
                    continue
                file_obj, error = self._decode_assinatura(valor)
                if error or not file_obj:
                    invalid.append(funcionario)
                else:
                    assinaturas[funcionario.id] = file_obj
        missing = [func for func in required if not (payload_map.get(str(func.id)) or "").strip()]
        if missing:
            logger.warning(
                "Entrega validar recebimento: faltando payload para funcionarios=%s",
                [func.id for func in missing],
            )
            self._assinatura_files = {}
            return False, "required", missing
        if invalid:
            logger.warning(
                "Entrega validar recebimento: payload invalido para funcionarios=%s",
                [func.id for func in invalid],
            )
            self._assinatura_files = {}
            return False, "invalid", invalid
        self._assinatura_files = assinaturas
        logger.warning(
            "Entrega validar recebimento OK: assinaturas_para=%s",
            sorted(list(assinaturas.keys())),
        )
        return True, None, []

    def _apply_assinatura(self, entrega):
        assinatura_file = None
        assinatura_files = getattr(self, "_assinatura_files", {}) or {}
        funcionario_id_raw = getattr(entrega, "funcionario_id", None)
        candidate_keys = []
        candidate_keys.append(funcionario_id_raw)
        if funcionario_id_raw is not None:
            candidate_keys.append(str(funcionario_id_raw))
            try:
                candidate_keys.append(int(funcionario_id_raw))
            except (TypeError, ValueError):
                pass
        for key in dict.fromkeys(candidate_keys):
            if key in assinatura_files:
                assinatura_file = assinatura_files.get(key)
                break
        if not assinatura_file:
            logger.warning(
                "Entrega sem assinatura para salvar: entrega_id=%s funcionario_id=%s(func_id_type=%s) assinatura_keys=%s(keys_type=%s)",
                getattr(entrega, "pk", None),
                funcionario_id_raw,
                type(funcionario_id_raw).__name__,
                sorted(list(assinatura_files.keys())),
                type(next(iter(assinatura_files.keys()), None)).__name__ if assinatura_files else "-",
            )
            return
        try:
            if entrega.assinatura:
                logger.warning(
                    "Entrega removendo assinatura anterior: entrega_id=%s assinatura=%s",
                    getattr(entrega, "pk", None),
                    entrega.assinatura.name,
                )
                entrega.assinatura.delete(save=False)
            assinatura_file.seek(0)
            logger.warning(
                "Entrega salvando assinatura: entrega_id=%s name=%s size=%s",
                getattr(entrega, "pk", None),
                getattr(assinatura_file, "name", None),
                getattr(assinatura_file, "size", None),
            )
            entrega.assinatura.save(assinatura_file.name, assinatura_file, save=False)
        except Exception:
            logger.exception(
                "Entrega falhou ao salvar assinatura (file->storage): entrega_id=%s funcionario_id=%s",
                getattr(entrega, "pk", None),
                entrega.funcionario_id,
            )
            raise
        try:
            entrega.updated_by = self.request.user
        except Exception:
            pass
        try:
            entrega.save(update_fields=["assinatura", "updated_by"])
        except Exception:
            logger.exception(
                "Entrega falhou ao salvar entrega com assinatura (db): entrega_id=%s assinatura=%s",
                getattr(entrega, "pk", None),
                getattr(entrega.assinatura, "name", None),
            )
            raise
        logger.warning(
            "Entrega assinatura salva: entrega_id=%s assinatura=%s",
            getattr(entrega, "pk", None),
            getattr(entrega.assinatura, "name", None),
        )

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
        # Se nenhuma regra de disponibilizacao foi configurada ainda,
        # permite todos os produtos (evita tela vazia para empresas novas).
        restrictions_exist = (
            FuncionarioProduto.objects.filter(company=self.request.tenant).exists()
            or TipoFuncionarioProduto.objects.filter(company=self.request.tenant).exists()
        )
        if not restrictions_exist:
            return True, None

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
            ativo=True,
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
            grade = (item.get("grade") or "").strip()
            itens.append(
                EntregaItem(
                    company=self.request.tenant,
                    entrega=entrega,
                    produto=item["produto"],
                    deposito_id=item["deposito_id"],
                    quantidade=item["quantidade"],
                    ca=item["ca"],
                    grade=grade,
                    observacao=item["observacao"],
                    created_by=self.request.user,
                    updated_by=self.request.user,
                )
            )
            estoque_key = (item["produto"].pk, int(item["deposito_id"]), grade)
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
            grade = (item.get("grade") or "").strip()
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
            grades = produto_fornecedor.produto.grade_opcoes() if produto_fornecedor.produto else []
            if grades and not grade:
                errors.append(f"Item {idx}: selecione a grade do produto.")
                continue
            if grade and grade not in grades:
                errors.append(f"Item {idx}: grade invalida para o produto selecionado.")
                continue
            permitido, motivo = self._is_produto_permitido(funcionario_id, produto_fornecedor)
            if not permitido:
                errors.append(f"Item {idx}: {motivo}")
                continue
            grade_value = (grade or "").strip()
            estoque_filters = {
                "company": self.request.tenant,
                "produto": produto_fornecedor.produto,
                "deposito_id": deposito_id,
                "grade": grade_value,
            }
            planta_id = self.request.session.get("planta_id")
            if planta_id:
                estoque_filters["deposito__planta_id"] = planta_id
            estoque = Estoque.objects.filter(**estoque_filters).select_related("deposito").first()
            if not estoque:
                errors.append(f"Item {idx}: nao existe estoque para este produto no deposito informado.")
                continue
            key = (produto_fornecedor.produto_id, int(deposito_id), grade_value)
            produto_ca = (produto_fornecedor.produto.ca or "").strip()
            required_map[key] = {
                "estoque": estoque,
                "quantidade": required_map.get(key, {}).get("quantidade", Decimal("0")) + quantidade,
                "produto_label": f"{produto_fornecedor.produto} | CA {produto_ca or '-'}",
                "deposito_label": estoque.deposito.nome if estoque.deposito_id else "-",
                "grade": grade_value,
            }
            created.append(
                {
                    "funcionario_id": funcionario_id,
                    "deposito_id": deposito_id,
                    "produto": produto_fornecedor.produto,
                    "quantidade": quantidade,
                    "ca": produto_ca,
                    "grade": grade_value,
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
        grade = (self.request.POST.get("grade") or "").strip()
        grades = produto_fornecedor.produto.grade_opcoes() if produto_fornecedor.produto else []
        if grades and not grade:
            form.add_error("grade", "Selecione a grade do produto.")
            return self.form_invalid(form)
        if grade and grade not in grades:
            form.add_error("grade", "Grade invalida para o produto selecionado.")
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
            "grade": grade,
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
                                "produto": f"{produto_fornecedor.produto} | CA {(produto_fornecedor.produto.ca or '').strip() or '-'}",
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
                grade=grade,
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
            return JsonResponse({"ok": False, "depositos": [], "grades": []})
        produto_fornecedor = ProdutoFornecedor.objects.filter(
            company=request.tenant,
            pk=produto_fornecedor_id,
        ).select_related("produto").first()
        if not produto_fornecedor:
            return JsonResponse({"ok": False, "depositos": [], "grades": []})
        grades = []
        if produto_fornecedor.produto_id and produto_fornecedor.produto:
            grades = produto_fornecedor.produto.grade_opcoes()
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
            .values("deposito_id", "deposito__nome")
            .distinct()
            .order_by("deposito__nome")
        )
        items = [{"id": item["deposito_id"], "nome": item["deposito__nome"]} for item in depositos]
        return JsonResponse({"ok": True, "depositos": items, "grades": grades})


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

        restrictions_exist = (
            FuncionarioProduto.objects.filter(company=request.tenant).exists()
            or TipoFuncionarioProduto.objects.filter(company=request.tenant).exists()
        )
        if not restrictions_exist:
            produtos = (
                ProdutoFornecedor.objects.filter(company=request.tenant, produto__ativo=True)
                .select_related("produto", "fornecedor")
                .order_by("produto__nome")
            )
            items = [
                {
                    "id": item.pk,
                    "label": f"{item.produto} | CA {item.produto.ca or '-'} | {item.fornecedor}",
                }
                for item in produtos
            ]
            return JsonResponse({"ok": True, "produtos": items})

        funcionario_ids = FuncionarioProduto.objects.filter(
            company=request.tenant,
            funcionario_id=funcionario.pk,
            produto_fornecedor__produto__ativo=True,
            ativo=True,
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
                "label": f"{item.produto} | CA {item.produto.ca or '-'} | {item.fornecedor}",
            }
            for item in produtos
        ]
        return JsonResponse({"ok": True, "produtos": items})


class EntregaDetailView(PermissionRequiredMixin, View):
    permission_required = "entregas.view_entrega"

    def _build_detail_context(self, request, entrega):
        itens_qs = entrega.itens.select_related("produto", "deposito", "produto__periodicidade")
        itens_source = list(itens_qs)
        if not itens_source:
            itens_source = [
                EntregaItem(
                    entrega=entrega,
                    produto=entrega.produto,
                    deposito=entrega.deposito,
                    quantidade=entrega.quantidade,
                    ca=entrega.ca or "",
                    grade="",
                    observacao=entrega.observacao or "",
                )
            ]

        devolucao_map = {}
        entrega_item_ids = [item.pk for item in itens_source if getattr(item, "pk", None)]
        if entrega_item_ids:
            devolucao_rows = (
                DevolucaoItem.objects.filter(company=request.tenant, entrega_item_id__in=entrega_item_ids)
                .values("entrega_item_id")
                .annotate(total=Sum("quantidade"), last=Max("devolucao__devolvida_em"))
            )
            devolucao_map = {
                row["entrega_item_id"]: {
                    "total": row.get("total") or Decimal("0"),
                    "last": row.get("last"),
                }
                for row in devolucao_rows
            }

        itens = []
        total_quantidade = Decimal("0")
        total_valor = Decimal("0")
        total_valor_ok = True
        depositos = set()

        for item in itens_source:
            if item.deposito:
                depositos.add(item.deposito.nome)
            produto = item.produto
            produto_fornecedor = ProdutoFornecedor.objects.filter(
                company=request.tenant,
                produto=produto,
            )
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

            devolvida_quantidade = Decimal("0")
            devolvida_em = None
            saldo_devolucao = None
            devolvido = False
            if getattr(item, "pk", None) and item.pk in devolucao_map:
                devolvida_quantidade = devolucao_map[item.pk]["total"]
                devolvida_em = devolucao_map[item.pk]["last"]
            if item.quantidade is not None:
                saldo_devolucao = item.quantidade - (devolvida_quantidade or Decimal("0"))
                devolvido = saldo_devolucao <= 0

            itens.append(
                {
                    "id": getattr(item, "pk", None),
                    "codigo": codigo,
                    "produto": produto,
                    "quantidade": item.quantidade,
                    "valor_unitario": valor_unitario,
                    "total_item": total_item,
                    "grade": (item.grade or "").strip() or "Sem Grade",
                    "ca": item.ca or "-",
                    "epi": "Sim" if produto and produto.controle_epi else "Nao",
                    "periodicidade": periodicidade_label,
                    "data_troca": data_troca,
                    "devolvida_quantidade": devolvida_quantidade,
                    "devolvida_em": devolvida_em,
                    "saldo_devolucao": saldo_devolucao,
                    "devolvido": devolvido,
                }
            )

        deposito_label = "-"
        if len(depositos) == 1:
            deposito_label = list(depositos)[0]
        elif len(depositos) > 1:
            deposito_label = "Varios"

        return {
            "entrega": entrega,
            "itens": itens,
            "total_quantidade": total_quantidade,
            "total_valor": total_valor if total_valor_ok else None,
            "deposito_label": deposito_label,
            "empresa_nome": getattr(request.tenant, "name", "-"),
            "can_devolver": request.user.has_perm("entregas.add_devolucao"),
            "devolver_url": reverse("entregas:devolver", args=[entrega.pk]),
            "condicao_choices": DevolucaoItem.CONDICAO_CHOICES,
        }

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

        context = self._build_detail_context(request, entrega)
        html = render_to_string(
            "entregas/_entrega_detail.html",
            context,
            request=request,
        )
        return JsonResponse({"ok": True, "html": html})


class EntregaDevolucaoCreateView(PermissionRequiredMixin, View):
    permission_required = "entregas.add_devolucao"

    def post(self, request, pk):
        entrega = (
            Entrega.objects.filter(pk=pk, company=request.tenant)
            .select_related("funcionario", "produto", "deposito")
            .first()
        )
        if not entrega:
            return JsonResponse({"ok": False, "message": "Entrega nao encontrada."}, status=404)
        if entrega.status == "cancelada":
            return JsonResponse({"ok": False, "message": "Entrega cancelada nao pode ser devolvida."}, status=400)

        entrega_item_id = request.POST.get("entrega_item_id")
        quantidade_raw = request.POST.get("quantidade")
        condicao = (request.POST.get("condicao") or "").strip()
        motivo = (request.POST.get("motivo") or "").strip()
        volta_para_estoque = (request.POST.get("volta_para_estoque") or "1").strip().lower() not in (
            "0",
            "false",
            "off",
            "nao",
            "não",
            "",
        )

        if not entrega_item_id:
            return JsonResponse({"ok": False, "message": "Informe o item da entrega."}, status=400)
        try:
            quantidade = Decimal(str(quantidade_raw))
        except (InvalidOperation, ValueError):
            return JsonResponse({"ok": False, "message": "Quantidade invalida."}, status=400)
        if quantidade <= 0:
            return JsonResponse({"ok": False, "message": "Quantidade deve ser maior que zero."}, status=400)
        condicoes_validas = {value for value, _ in DevolucaoItem.CONDICAO_CHOICES}
        if condicao not in condicoes_validas:
            return JsonResponse({"ok": False, "message": "Condicao invalida."}, status=400)
        if condicao == DevolucaoItem.CONDICAO_OUTRA and not motivo:
            return JsonResponse({"ok": False, "message": "Informe o motivo para a condicao 'Outra'."}, status=400)

        estoque = None
        try:
            with transaction.atomic():
                entrega_item = (
                    EntregaItem.objects.select_for_update()
                    .filter(pk=entrega_item_id, company=request.tenant, entrega_id=entrega.pk)
                    .select_related("produto", "deposito", "entrega")
                    .first()
                )
                if not entrega_item:
                    return JsonResponse(
                        {"ok": False, "message": "Item da entrega nao encontrado."},
                        status=404,
                    )

                devolucoes_qs = DevolucaoItem.objects.select_for_update().filter(
                    company=request.tenant,
                    entrega_item=entrega_item,
                )
                devolvido_total = devolucoes_qs.aggregate(total=Sum("quantidade")).get("total") or Decimal("0")
                saldo = entrega_item.quantidade - devolvido_total
                if saldo <= 0:
                    return JsonResponse(
                        {"ok": False, "message": "Este item ja foi devolvido completamente."},
                        status=400,
                    )
                if quantidade > saldo:
                    return JsonResponse(
                        {"ok": False, "message": f"Quantidade excede o saldo de devolucao ({saldo})."},
                        status=400,
                    )

                if volta_para_estoque:
                    estoque, estoque_error = _get_or_create_estoque_for_update(
                        request=request,
                        produto=entrega_item.produto,
                        deposito=entrega_item.deposito,
                        grade=entrega_item.grade,
                    )
                    if estoque_error:
                        raise ValidationError(estoque_error)

                devolucao = Devolucao.objects.create(
                    company=request.tenant,
                    entrega=entrega,
                    devolvida_em=timezone.now(),
                    created_by=request.user,
                    updated_by=request.user,
                )
                DevolucaoItem.objects.create(
                    company=request.tenant,
                    devolucao=devolucao,
                    entrega_item=entrega_item,
                    quantidade=quantidade,
                    condicao=condicao,
                    motivo=motivo,
                    volta_para_estoque=volta_para_estoque,
                    created_by=request.user,
                    updated_by=request.user,
                )

            condicao_label = dict(DevolucaoItem.CONDICAO_CHOICES).get(condicao, condicao)
            destino_label = "estoque" if volta_para_estoque else "descarte"
            observacao = f"Devolucao da entrega #{entrega.pk} ({condicao_label}) - {destino_label}"
            if motivo:
                observacao = f"{observacao} - {motivo}"

            if volta_para_estoque and estoque:
                MovimentacaoEstoque.objects.create(
                    company=request.tenant,
                    estoque=estoque,
                    tipo=MovimentacaoEstoque.ENTRADA,
                    quantidade=quantidade,
                    observacao=observacao,
                    created_by=request.user,
                    updated_by=request.user,
                )
            FuncionarioHistorico.objects.create(
                company=request.tenant,
                funcionario=entrega.funcionario,
                descricao=(
                    f"Devolucao: {entrega_item.produto} (Qtd {quantidade}) "
                    f"no deposito {entrega_item.deposito}. Condicao: {condicao_label}. Destino: {destino_label}."
                    + (f" Motivo: {motivo}." if motivo else "")
                ),
                created_by=request.user,
                updated_by=request.user,
            )
        except ValidationError as exc:
            message = exc.message_dict if hasattr(exc, "message_dict") else None
            if isinstance(message, dict):
                message = next(iter(message.values()), ["Erro"])[0]
            message = str(exc)
            return JsonResponse({"ok": False, "message": message}, status=400)

        detail_view = EntregaDetailView()
        context = detail_view._build_detail_context(request, entrega)
        html = render_to_string(
            "entregas/_entrega_detail.html",
            context,
            request=request,
        )
        return JsonResponse({"ok": True, "html": html})


class DevolucaoFuncionarioItensView(PermissionRequiredMixin, View):
    permission_required = "entregas.add_devolucao"

    def get(self, request):
        funcionario_id = request.GET.get("funcionario_id")
        if not funcionario_id:
            return JsonResponse({"ok": False, "items": []}, status=400)
        funcionario = (
            Funcionario.objects.filter(company=request.tenant, pk=funcionario_id, ativo=True)
            .only("id", "nome")
            .first()
        )
        if not funcionario:
            return JsonResponse({"ok": False, "items": []}, status=404)

        # Regra: apenas o ultimo recebimento de cada item (produto+grade) fica "ativo" para devolucao.
        # (Parcial depende da quantidade do ultimo recebimento.)
        itens_qs = (
            EntregaItem.objects.filter(company=request.tenant, entrega__funcionario_id=funcionario_id)
            .exclude(entrega__status="cancelada")
            .exclude(entrega__entregue_em__isnull=True)
            .select_related("produto", "deposito", "entrega")
            .order_by("-entrega__entregue_em", "-entrega_id", "-id")
        )

        latest_by_key = {}
        latest_items = []
        for item in itens_qs:
            produto_id = item.produto_id
            grade_key = ((item.grade or "").strip() or "").lower()
            key = (produto_id, grade_key)
            if key in latest_by_key:
                continue
            latest_by_key[key] = item
            latest_items.append(item)

        devolvido_map_rows = (
            DevolucaoItem.objects.filter(
                company=request.tenant,
                entrega_item_id__in=[item.pk for item in latest_items],
            )
            .values("entrega_item_id")
            .annotate(total=Sum("quantidade"))
        )
        devolvido_map = {row["entrega_item_id"]: row.get("total") or Decimal("0") for row in devolvido_map_rows}

        items = []
        for item in latest_items:
            devolvido = devolvido_map.get(item.pk) or Decimal("0")
            saldo = item.quantidade - devolvido
            if saldo <= 0:
                continue
            produto_label = str(item.produto) if item.produto_id else "-"
            deposito_label = str(item.deposito) if item.deposito_id else "-"
            grade_label = (item.grade or "").strip() or "Sem Grade"
            entregue_em = item.entrega.entregue_em if item.entrega_id else None
            entrega_label = f"Entrega #{item.entrega_id}" if item.entrega_id else "Entrega"
            items.append(
                {
                    "entrega_item_id": item.pk,
                    "entrega_id": item.entrega_id,
                    "entrega_label": entrega_label,
                    "entregue_em": entregue_em.isoformat() if entregue_em else None,
                    "produto_label": produto_label,
                    "deposito_label": deposito_label,
                    "grade": grade_label,
                    "saldo": str(saldo),
                }
            )
        return JsonResponse({"ok": True, "funcionario": {"id": funcionario.id, "nome": funcionario.nome}, "items": items})


class DevolucaoFuncionarioConfirmView(PermissionRequiredMixin, View):
    permission_required = "entregas.add_devolucao"

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
        filename = f"assinatura-devolucao-{uuid.uuid4().hex[:12]}.{extension}"
        return ContentFile(decoded, name=filename), None

    def _build_validacao_message(self, funcionarios, status):
        if any(func.validacao_recebimento == "assinatura" for func in funcionarios):
            if status == "invalid":
                return "Assinatura invalida para o funcionario informado."
            return "Assinatura do funcionario obrigatoria para concluir a devolucao."
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

    def _apply_assinatura(self, devolucao, funcionario_id):
        assinatura_file = getattr(self, "_assinatura_files", {}).get(int(funcionario_id))
        if not assinatura_file:
            return
        if devolucao.assinatura:
            devolucao.assinatura.delete(save=False)
        assinatura_file.seek(0)
        devolucao.assinatura.save(assinatura_file.name, assinatura_file, save=False)
        try:
            devolucao.updated_by = self.request.user
        except Exception:
            pass
        devolucao.save(update_fields=["assinatura", "updated_by"])

    def _parse_items_payload(self, payload):
        try:
            data = json.loads(payload)
        except json.JSONDecodeError:
            return None, "Itens invalidos."
        if not isinstance(data, list) or not data:
            return None, "Itens invalidos."
        items = []
        for item in data:
            if not isinstance(item, dict):
                return None, "Itens invalidos."
            items.append(item)
        return items, None

    def _parse_bool(self, value, default=True):
        if value is None:
            return default
        if isinstance(value, bool):
            return value
        raw = str(value).strip().lower()
        if raw in ("1", "true", "on", "sim", "yes"):
            return True
        if raw in ("0", "false", "off", "nao", "não", "no", ""):
            return False
        return default

    def _latest_entrega_item_ids(self, request, funcionario_id, entrega_items):
        keys = set()
        for item in entrega_items:
            produto_id = item.produto_id
            grade_key = ((item.grade or "").strip() or "").lower()
            keys.add((produto_id, grade_key))
        if not keys:
            return {}

        # Busca entregas do funcionario (entregues e nao canceladas), ordenadas do mais recente.
        qs = (
            EntregaItem.objects.filter(company=request.tenant, entrega__funcionario_id=funcionario_id)
            .exclude(entrega__status="cancelada")
            .exclude(entrega__entregue_em__isnull=True)
            .select_related("entrega")
            .order_by("-entrega__entregue_em", "-entrega_id", "-id")
        )
        latest = {}
        for row in qs:
            produto_id = row.produto_id
            grade_key = ((row.grade or "").strip() or "").lower()
            key = (produto_id, grade_key)
            if key not in keys or key in latest:
                continue
            latest[key] = row.pk
            if len(latest) == len(keys):
                break
        return latest

    def post(self, request):
        payload = request.POST.get("itens_payload")
        validacao_payload = self._parse_validacao_payload(request.POST.get("validacao_payload"))
        items, error = self._parse_items_payload(payload)
        if error:
            return JsonResponse({"ok": False, "message": error}, status=400)

        funcionario_ids = list({str(item.get("funcionario_id")) for item in items if item.get("funcionario_id")})
        if len(funcionario_ids) != 1:
            return JsonResponse({"ok": False, "message": "Todos os itens devem pertencer ao mesmo funcionario."}, status=400)
        funcionario_id = funcionario_ids[0]

        ok, status, funcionarios = self._validate_recebimento([funcionario_id], validacao_payload)
        if not ok:
            message = self._build_validacao_message(funcionarios, status)
            return JsonResponse(
                {
                    "ok": False,
                    "validate": True,
                    "message": message,
                    "funcionarios": [
                        {"id": func.id, "nome": func.nome, "validacao": func.validacao_recebimento}
                        for func in funcionarios
                    ],
                    "invalid": status == "invalid",
                },
                status=400,
            )

        try:
            with transaction.atomic():
                entrega_item_ids = [item.get("entrega_item_id") for item in items if item.get("entrega_item_id")]
                entrega_items = list(
                    EntregaItem.objects.select_for_update()
                    .filter(company=request.tenant, pk__in=entrega_item_ids, entrega__funcionario_id=funcionario_id)
                    .exclude(entrega__status="cancelada")
                    .exclude(entrega__entregue_em__isnull=True)
                    .select_related("produto", "deposito", "entrega", "entrega__funcionario")
                    .order_by("id")
                )
                entrega_item_map = {str(item.pk): item for item in entrega_items}
                if len(entrega_item_map) != len(set(str(x) for x in entrega_item_ids)):
                    return JsonResponse({"ok": False, "message": "Um ou mais itens sao invalidos."}, status=400)

                latest_ids = self._latest_entrega_item_ids(request, funcionario_id, entrega_items)
                for entrega_item in entrega_items:
                    produto_id = entrega_item.produto_id
                    grade_key = ((entrega_item.grade or "").strip() or "").lower()
                    key = (produto_id, grade_key)
                    if latest_ids.get(key) != entrega_item.pk:
                        return JsonResponse(
                            {"ok": False, "message": "Um ou mais itens nao sao o ultimo recebimento (inativo)."},
                            status=400,
                        )

                devolvido_rows = (
                    DevolucaoItem.objects.filter(
                        company=request.tenant,
                        entrega_item_id__in=[item.pk for item in entrega_items],
                    )
                    .values("entrega_item_id")
                    .annotate(total=Sum("quantidade"))
                )
                devolvido_map = {
                    str(row["entrega_item_id"]): row.get("total") or Decimal("0") for row in devolvido_rows
                }

                condicoes_validas = {value for value, _ in DevolucaoItem.CONDICAO_CHOICES}
                grouped = {}
                for item_payload in items:
                    entrega_item_id = str(item_payload.get("entrega_item_id") or "")
                    entrega_item = entrega_item_map.get(entrega_item_id)
                    if not entrega_item:
                        return JsonResponse({"ok": False, "message": "Um ou mais itens sao invalidos."}, status=400)
                    try:
                        quantidade = Decimal(str(item_payload.get("quantidade")))
                    except (InvalidOperation, ValueError):
                        return JsonResponse({"ok": False, "message": "Quantidade invalida."}, status=400)
                    if quantidade <= 0:
                        return JsonResponse({"ok": False, "message": "Quantidade deve ser maior que zero."}, status=400)
                    condicao = (item_payload.get("condicao") or "").strip()
                    motivo = (item_payload.get("motivo") or "").strip()
                    volta_para_estoque = self._parse_bool(item_payload.get("volta_para_estoque"), default=True)
                    if condicao not in condicoes_validas:
                        return JsonResponse({"ok": False, "message": "Condicao invalida."}, status=400)
                    if condicao == DevolucaoItem.CONDICAO_OUTRA and not motivo:
                        return JsonResponse({"ok": False, "message": "Informe o motivo para a condicao 'Outra'."}, status=400)

                    devolvido_total = devolvido_map.get(entrega_item_id) or Decimal("0")
                    saldo = entrega_item.quantidade - devolvido_total
                    if saldo <= 0:
                        return JsonResponse({"ok": False, "message": "Um item ja foi devolvido completamente."}, status=400)
                    if quantidade > saldo:
                        return JsonResponse({"ok": False, "message": f"Quantidade excede o saldo ({saldo})."}, status=400)

                    grouped.setdefault(entrega_item.entrega_id, []).append(
                        {
                            "entrega_item": entrega_item,
                            "quantidade": quantidade,
                            "condicao": condicao,
                            "motivo": motivo,
                            "volta_para_estoque": volta_para_estoque,
                        }
                    )

                for entrega_id, group_items in grouped.items():
                    entrega = group_items[0]["entrega_item"].entrega
                    devolucao = Devolucao.objects.create(
                        company=request.tenant,
                        entrega=entrega,
                        devolvida_em=timezone.now(),
                        created_by=request.user,
                        updated_by=request.user,
                    )
                    self._apply_assinatura(devolucao, funcionario_id)
                    for row in group_items:
                        entrega_item = row["entrega_item"]
                        quantidade = row["quantidade"]
                        condicao = row["condicao"]
                        motivo = row["motivo"]
                        volta_para_estoque = bool(row.get("volta_para_estoque", True))

                        estoque = None
                        if volta_para_estoque:
                            estoque, estoque_error = _get_or_create_estoque_for_update(
                                request=request,
                                produto=entrega_item.produto,
                                deposito=entrega_item.deposito,
                                grade=entrega_item.grade,
                            )
                            if estoque_error:
                                raise ValidationError(estoque_error)

                        DevolucaoItem.objects.create(
                            company=request.tenant,
                            devolucao=devolucao,
                            entrega_item=entrega_item,
                            quantidade=quantidade,
                            condicao=condicao,
                            motivo=motivo,
                            volta_para_estoque=volta_para_estoque,
                            created_by=request.user,
                            updated_by=request.user,
                        )
                        condicao_label = dict(DevolucaoItem.CONDICAO_CHOICES).get(condicao, condicao)
                        destino_label = "estoque" if volta_para_estoque else "descarte"
                        observacao = f"Devolucao da entrega #{entrega_id} ({condicao_label}) - {destino_label}"
                        if motivo:
                            observacao = f"{observacao} - {motivo}"
                        if volta_para_estoque and estoque:
                            MovimentacaoEstoque.objects.create(
                                company=request.tenant,
                                estoque=estoque,
                                tipo=MovimentacaoEstoque.ENTRADA,
                                quantidade=quantidade,
                                observacao=observacao,
                                created_by=request.user,
                                updated_by=request.user,
                            )
                        FuncionarioHistorico.objects.create(
                            company=request.tenant,
                            funcionario=entrega.funcionario,
                            descricao=(
                                f"Devolucao: {entrega_item.produto} (Qtd {quantidade}) "
                                f"no deposito {entrega_item.deposito}. Condicao: {condicao_label}. Destino: {destino_label}."
                                + (f" Motivo: {motivo}." if motivo else "")
                            ),
                            created_by=request.user,
                            updated_by=request.user,
                        )
        except ValidationError as exc:
            return JsonResponse({"ok": False, "message": str(exc)}, status=400)

        return JsonResponse({"ok": True})


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
                    "ca": (produto_fornecedor.produto.ca or "").strip(),
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
            produto_fornecedor = produto_fornecedor.select_related("fornecedor").order_by("pk").first()
            produto_fornecedor_id = produto_fornecedor.pk if produto_fornecedor else ""
            produto_label = "-"
            if produto_fornecedor:
                produto_label = (
                    f"{produto_fornecedor.produto} | CA {produto_fornecedor.produto.ca or '-'} | "
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
                    "grade": (item.grade or "").strip(),
                    "grade_label": (item.grade or "").strip() or "-",
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
                grade = (item.get("grade") or "").strip()
                itens.append(
                    EntregaItem(
                        company=request.tenant,
                        entrega=entrega,
                        produto=item["produto"],
                        deposito_id=item["deposito_id"],
                        quantidade=item["quantidade"],
                        ca=item["ca"],
                        grade=grade,
                        observacao=item["observacao"],
                        created_by=request.user,
                        updated_by=request.user,
                    )
                )
                estoque_key = (item["produto"].pk, int(item["deposito_id"]), grade)
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
                        grade="",
                        observacao=entrega.observacao or "",
                    )
                ]
            for item in itens_qs:
                estoque, estoque_error = _get_or_create_estoque_for_update(
                    request=request,
                    produto=item.produto,
                    deposito=item.deposito,
                    grade=item.grade,
                )
                if estoque_error:
                    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                        return JsonResponse({"ok": False, "message": estoque_error}, status=400)
                    return HttpResponseRedirect(reverse("entregas:list"))
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
