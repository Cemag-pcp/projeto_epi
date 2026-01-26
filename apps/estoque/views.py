from django.contrib.auth.mixins import PermissionRequiredMixin
from django.core.exceptions import PermissionDenied
from django.core.paginator import EmptyPage, InvalidPage, Paginator
from django.http import JsonResponse
from django.template.loader import render_to_string
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View

from apps.produtos.models import Produto
from apps.depositos.models import Deposito

from apps.core.views import BaseTenantCreateView, BaseTenantListView
from .forms import EstoqueForm, MovimentacaoEstoqueForm
from .models import Estoque, MovimentacaoEstoque


class EstoqueModuleRequiredMixin:
    def dispatch(self, request, *args, **kwargs):
        tenant = getattr(request, "tenant", None)
        if tenant and not getattr(tenant, "estoque_enabled", True):
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return JsonResponse(
                    {"ok": False, "detail": "Modulo de estoque desativado."},
                    status=403,
                )
            raise PermissionDenied("Modulo de estoque desativado.")
        return super().dispatch(request, *args, **kwargs)


class EstoqueListView(EstoqueModuleRequiredMixin, BaseTenantListView):
    model = Estoque
    template_name = "estoque/list.html"
    title = "Estoque"
    headers = ["Produto", "CA", "Codigo", "Grade", "Deposito", "Quantidade", "Status"]
    row_fields = ["produto", "produto__ca", "produto__codigo", "grade", "deposito", "quantidade", "status"]
    filter_definitions = [
        {"name": "produto__nome", "label": "Produto", "lookup": "icontains", "type": "text"},
        {"name": "produto__ca", "label": "CA", "lookup": "icontains", "type": "text"},
        {"name": "produto__codigo", "label": "Codigo", "lookup": "icontains", "type": "text"},
        {"name": "grade", "label": "Grade", "lookup": "icontains", "type": "text"},
        {"name": "deposito__nome", "label": "Deposito", "lookup": "icontains", "type": "text"},
    ]
    create_url_name = "estoque:create"

    def get_queryset(self):
        queryset = super().get_queryset().select_related(
            "produto",
            "deposito",
        ).order_by("produto__nome", "grade", "deposito__nome")
        planta_id = self.request.session.get("planta_id")
        if planta_id:
            queryset = queryset.filter(deposito__planta_id=planta_id)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        planta_id = self.request.session.get("planta_id")
        if context.get("can_add"):
            context["create_form"] = EstoqueForm(tenant=self.request.tenant, planta_id=planta_id)
        else:
            context["create_form"] = None
        if self.request.user.has_perm("estoque.add_movimentacaoestoque"):
            context["movement_rows"] = [
                {
                    "object": obj,
                    "form": MovimentacaoEstoqueForm(
                        initial={"estoque": obj},
                        tenant=self.request.tenant,
                        planta_id=planta_id,
                    ),
                    "action_url": reverse_lazy("estoque:movimentar"),
                }
                for obj in context["object_list"]
            ]
        else:
            context["movement_rows"] = []
        return context


class EstoqueGradesView(PermissionRequiredMixin, EstoqueModuleRequiredMixin, View):
    permission_required = "estoque.view_estoque"

    def get(self, request, *args, **kwargs):
        produto_id = request.GET.get("produto_id")
        if not produto_id:
            return JsonResponse({"ok": False, "grades": []})
        produto = Produto.objects.filter(company=request.tenant, pk=produto_id).first()
        if not produto:
            return JsonResponse({"ok": False, "grades": []})
        grades = produto.grade_opcoes()
        return JsonResponse({"ok": True, "grades": grades})


class EstoqueCreateView(EstoqueModuleRequiredMixin, BaseTenantCreateView):
    model = Estoque
    form_class = EstoqueForm
    success_url_name = "estoque:list"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["tenant"] = self.request.tenant
        kwargs["planta_id"] = self.request.session.get("planta_id")
        return kwargs

    def form_valid(self, form):
        response = super().form_valid(form)
        if self.request.headers.get("X-Requested-With") == "XMLHttpRequest":
            planta_id = self.request.session.get("planta_id")
            form_html = render_to_string(
                "estoque/_estoque_form.html",
                {
                    "form": EstoqueForm(tenant=self.request.tenant, planta_id=planta_id),
                    "form_action": reverse_lazy("estoque:create"),
                    "form_id": "estoque-form",
                },
                request=self.request,
            )
            return JsonResponse(
                {
                    "ok": True,
                    "message": "Criado com sucesso.",
                    "form_html": form_html,
                }
            )
        return response

    def form_invalid(self, form):
        if self.request.headers.get("X-Requested-With") == "XMLHttpRequest":
            message = None
            non_field = form.non_field_errors()
            if non_field:
                message = str(non_field[0])
            form_html = render_to_string(
                "estoque/_estoque_form.html",
                {
                    "form": form,
                    "form_action": self.request.path,
                    "form_id": "estoque-form",
                },
                request=self.request,
            )
            return JsonResponse(
                {
                    "ok": False,
                    "message": message or "Nao foi possivel salvar o estoque.",
                    "form_html": form_html,
                },
                status=400,
            )
        return super().form_invalid(form)


class MovimentacaoCreateView(EstoqueModuleRequiredMixin, BaseTenantCreateView):
    model = MovimentacaoEstoque
    form_class = MovimentacaoEstoqueForm
    success_url_name = "estoque:list"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["tenant"] = self.request.tenant
        kwargs["planta_id"] = self.request.session.get("planta_id")
        return kwargs


class ProdutoExtratoView(EstoqueModuleRequiredMixin, BaseTenantListView):
    model = MovimentacaoEstoque
    template_name = "estoque/extrato.html"
    title = "Extrato de produto"
    paginate_by = 10
    page_kwarg = "page"

    def get(self, request, *args, **kwargs):
        page = request.GET.get(self.page_kwarg)
        if page:
            try:
                page_number = int(page)
            except (TypeError, ValueError):
                page_number = 1
            if page_number < 1:
                query = request.GET.copy()
                query[self.page_kwarg] = "1"
                request.GET = query
        try:
            return super().get(request, *args, **kwargs)
        except EmptyPage:
            query = request.GET.copy()
            query[self.page_kwarg] = "1"
            request.GET = query
            return super().get(request, *args, **kwargs)

    def get_queryset(self):
        tenant = self.request.tenant
        planta_id = self.request.session.get("planta_id")
        queryset = MovimentacaoEstoque.objects.filter(company=tenant).select_related(
            "estoque__produto",
            "estoque__deposito",
            "created_by",
            "deposito_destino",
        )
        if planta_id:
            queryset = queryset.filter(estoque__deposito__planta_id=planta_id)
        produto_id = self.request.GET.get("produto_id")
        deposito_id = self.request.GET.get("deposito_id")
        tipo = self.request.GET.get("tipo")
        data_inicio = self.request.GET.get("data_inicio")
        data_fim = self.request.GET.get("data_fim")
        if produto_id:
            queryset = queryset.filter(estoque__produto_id=produto_id)
        if deposito_id:
            queryset = queryset.filter(estoque__deposito_id=deposito_id)
        if tipo:
            queryset = queryset.filter(tipo=tipo)
        if data_inicio:
            queryset = queryset.filter(criado_em__date__gte=data_inicio)
        if data_fim:
            queryset = queryset.filter(criado_em__date__lte=data_fim)
        return queryset

    def get_filters_context(self):
        tenant = self.request.tenant
        planta_id = self.request.session.get("planta_id")
        produtos = Produto.objects.filter(company=tenant, ativo=True).order_by("nome")
        depositos = Deposito.objects.filter(company=tenant, ativo=True)
        if planta_id:
            depositos = depositos.filter(planta_id=planta_id)
        depositos = depositos.order_by("nome")
        return [
            {
                "name": "produto_id",
                "label": "Produto",
                "type": "select",
                "options": [("", "Todos")] + [(p.pk, p.nome) for p in produtos],
                "value": self.request.GET.get("produto_id", ""),
            },
            {
                "name": "deposito_id",
                "label": "Deposito",
                "type": "select",
                "options": [("", "Todos")] + [(d.pk, d.nome) for d in depositos],
                "value": self.request.GET.get("deposito_id", ""),
            },
            {
                "name": "tipo",
                "label": "Tipo",
                "type": "select",
                "options": [("", "Todos")] + list(MovimentacaoEstoque.TIPO_CHOICES),
                "value": self.request.GET.get("tipo", ""),
            },
            {
                "name": "data_inicio",
                "label": "Data inicio",
                "type": "date",
                "options": [],
                "value": self.request.GET.get("data_inicio", ""),
            },
            {
                "name": "data_fim",
                "label": "Data fim",
                "type": "date",
                "options": [],
                "value": self.request.GET.get("data_fim", ""),
            },
        ]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        movimentos = list(context["object_list"])
        estoque_ids = {mov.estoque_id for mov in movimentos}
        saldos = {
            estoque.pk: estoque.quantidade
            for estoque in Estoque.objects.filter(company=self.request.tenant, pk__in=estoque_ids)
        }
        extrato_items = []
        for mov in movimentos:
            saldo_atual = saldos.get(mov.estoque_id, 0)
            if mov.tipo == MovimentacaoEstoque.ENTRADA:
                delta = mov.quantidade
            elif mov.tipo == MovimentacaoEstoque.SAIDA:
                delta = -mov.quantidade
            else:
                delta = -mov.quantidade
            saldo_anterior = saldo_atual - delta
            saldos[mov.estoque_id] = saldo_anterior
            extrato_items.append(
                {
                    "mov": mov,
                    "produto": mov.estoque.produto if mov.estoque_id else None,
                    "grade": (mov.estoque.grade or "").strip() if mov.estoque_id else "",
                    "deposito": mov.estoque.deposito if mov.estoque_id else None,
                    "saldo_anterior": saldo_anterior,
                    "saldo_atual": saldo_atual,
                    "tipo": mov.get_tipo_display(),
                    "data": mov.criado_em,
                    "usuario": mov.created_by,
                    "observacao": mov.observacao,
                    "deposito_destino": mov.deposito_destino,
                }
            )
        context["extrato_items"] = extrato_items
        context["filters"] = self.get_filters_context()
        context["subtitle"] = "Movimentacoes detalhadas do estoque"
        context["now"] = timezone.now()
        return context
    
    def paginate_queryset(self, queryset, page_size):
        paginator = Paginator(queryset, page_size)
        page_kwarg = self.page_kwarg
        page = self.request.GET.get(page_kwarg) or 1
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
        return paginator, page_obj, page_obj.object_list, page_obj.has_other_pages()
