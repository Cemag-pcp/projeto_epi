
import json

from django.contrib.auth.hashers import make_password
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.core.paginator import InvalidPage, Paginator
from django.http import JsonResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.template.loader import render_to_string
from django.urls import reverse, reverse_lazy
from django.views import View

from apps.core.views import (
    BaseTenantCreateView,
    BaseTenantDetailView,
    BaseTenantListView,
    BaseTenantUpdateView,
)
from apps.treinamentos.models import TreinamentoCertificado, TreinamentoPendencia
from .forms import (
    AfastamentoForm,
    AdvertenciaForm,
    CentroCustoForm,
    FuncionarioAnexoForm,
    FuncionarioForm,
    GHEForm,
    MotivoAfastamentoForm,
    PlantaForm,
    FuncionarioProdutoForm,
    RiscoAssignForm,
    RiscoForm,
    TurnoForm,
    FuncionarioValidacaoForm,
)
from .models import (
    Afastamento,
    CentroCusto,
    Funcionario,
    FuncionarioAnexo,
    FuncionarioHistorico,
    FuncionarioProduto,
    GHE,
    Advertencia,
    MotivoAfastamento,
    Planta,
    Risco,
    Turno,
)

# Funcionarios

def log_funcionario_event(funcionario, descricao, request):
    FuncionarioHistorico.objects.create(
        company=request.tenant,
        funcionario=funcionario,
        descricao=descricao,
        created_by=request.user,
        updated_by=request.user,
    )


class FuncionarioListView(BaseTenantListView):
    model = Funcionario
    template_name = "funcionarios/list.html"
    form_class = FuncionarioForm
    paginate_by = 10
    title = "Funcionarios"
    headers = ["Registro", "Nome", "CPF", "Setor", "Cargo", "Planta", "Centro de Custo", "GHE", "Ativo"]
    row_fields = ["registro", "nome", "cpf", "setor", "cargo", "planta", "centro_custo", "ghe", "ativo"]
    filter_definitions = [
        {"name": "nome", "label": "Nome", "lookup": "icontains", "type": "text"},
        {"name": "planta__nome", "label": "Planta", "lookup": "icontains", "type": "text"},
        {
            "name": "ativo",
            "label": "Ativo",
            "lookup": "exact_bool",
            "type": "select",
            "options": [("", "Todos"), ("1", "Ativo"), ("0", "Inativo")],
        },
    ]
    create_url_name = "funcionarios:create"
    update_url_name = "funcionarios:update"

    def get(self, request, *args, **kwargs):
        if request.headers.get("X-Requested-With") != "XMLHttpRequest":
            return super().get(request, *args, **kwargs)
        self.object_list = self.get_queryset()
        context = self.get_context_data()
        page_obj = context.get("page_obj")
        rows_html = render_to_string(
            "funcionarios/_funcionario_rows.html",
            {"object_list": context.get("object_list", [])},
            request=request,
        )
        modals_html = render_to_string(
            "funcionarios/_funcionario_edit_modals.html",
            {"edit_rows": context.get("edit_rows", [])},
            request=request,
        )
        pagination_html = render_to_string(
            "components/_pagination.html",
            {"page_obj": page_obj},
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
        planta_id = self.request.session.get("planta_id")
        if planta_id and Planta.objects.filter(
            pk=planta_id,
            company=self.request.tenant,
            ativo=True,
        ).exists():
            queryset = queryset.filter(planta_id=planta_id)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if context.get("can_add"):
            context["create_form"] = FuncionarioForm(include_validacao=False)
        else:
            context["create_form"] = None
        if context.get("can_change"):
            context["edit_rows"] = [
                {
                    "object": obj,
                    "form": FuncionarioForm(instance=obj, include_validacao=False),
                    "update_url": reverse_lazy(self.update_url_name, args=[obj.pk]),
                }
                for obj in context.get("object_list", [])
            ]
        else:
            context["edit_rows"] = []
        context["anexo_form"] = FuncionarioAnexoForm()
        context["anexo_create_url"] = reverse_lazy("funcionarios:anexos_create")
        context["historico_filters"] = [
            {"name": "descricao", "label": "Descricao", "type": "text", "value": ""},
            {"name": "data_inicio", "label": "Data inicio", "type": "date", "value": ""},
            {"name": "data_fim", "label": "Data fim", "type": "date", "value": ""},
        ]
        return context


class FuncionarioCreateView(BaseTenantCreateView):
    model = Funcionario
    form_class = FuncionarioForm
    success_url_name = "funcionarios:list"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["include_validacao"] = False
        return kwargs

    def form_valid(self, form):
        response = super().form_valid(form)
        if self.request.headers.get("X-Requested-With") == "XMLHttpRequest":
            row_html = render_to_string(
                "funcionarios/_funcionario_row.html",
                {"funcionario": self.object},
                request=self.request,
            )
            edit_modal_html = render_to_string(
                "funcionarios/_funcionario_edit_modal.html",
                {
                    "funcionario": self.object,
                    "form": FuncionarioForm(instance=self.object, include_validacao=False),
                    "update_url": reverse("funcionarios:update", args=[self.object.pk]),
                },
                request=self.request,
            )
            form_html = render_to_string(
                "funcionarios/_funcionario_form.html",
                {
                    "form": FuncionarioForm(include_validacao=False),
                    "form_action": reverse("funcionarios:create"),
                    "accordion_id": "funcionarioFormCreate",
                    "form_id": "funcionarioFormCreate-form",
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
                "funcionarios/_funcionario_form.html",
                {
                    "form": form,
                    "form_action": reverse("funcionarios:create"),
                    "accordion_id": "funcionarioFormCreate",
                    "form_id": "funcionarioFormCreate-form",
                },
                request=self.request,
            )
            return JsonResponse({"ok": False, "form_html": form_html}, status=400)
        return super().form_invalid(form)


class FuncionarioUpdateView(BaseTenantUpdateView):
    model = Funcionario
    form_class = FuncionarioForm
    success_url_name = "funcionarios:list"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["include_validacao"] = False
        return kwargs

    def form_valid(self, form):
        response = super().form_valid(form)
        if self.request.headers.get("X-Requested-With") == "XMLHttpRequest":
            row_html = render_to_string(
                "funcionarios/_funcionario_row.html",
                {"funcionario": self.object},
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
                "funcionarios/_funcionario_form.html",
                {
                    "form": form,
                    "form_action": reverse("funcionarios:update", args=[self.get_object().pk]),
                    "accordion_id": f"funcionarioFormEdit-{self.get_object().pk}",
                    "form_id": f"funcionarioFormEdit-{self.get_object().pk}-form",
                },
                request=self.request,
            )
            return JsonResponse(
                {"ok": False, "form_html": form_html, "row_id": self.get_object().pk},
                status=400,
            )
        return super().form_invalid(form)


class FuncionarioDetailView(BaseTenantDetailView):
    model = Funcionario
    template_name = "funcionarios/detail.html"
    afastamentos_paginate_by = 10
    afastamento_filter_definitions = [
        {"name": "data_inicio", "label": "Data inicio", "lookup": "exact", "type": "date"},
        {"name": "data_fim", "label": "Data fim", "lookup": "exact", "type": "date"},
        {"name": "motivo", "label": "Motivo", "lookup": "icontains", "type": "text"},
        {"name": "nome_arquivo", "label": "Nome do arquivo", "lookup": "icontains", "type": "text"},
    ]

    def get_afastamentos_queryset(self):
        queryset = self.object.afastamentos.all()
        for definition in self.afastamento_filter_definitions:
            name = definition["name"]
            lookup = definition.get("lookup", "icontains")
            value = self.request.GET.get(name)
            if value in (None, ""):
                continue
            queryset = queryset.filter(**{f"{name}__{lookup}": value})
        return queryset

    def get_afastamento_filters_context(self):
        filters = []
        for definition in self.afastamento_filter_definitions:
            name = definition["name"]
            filters.append(
                {
                    "name": name,
                    "label": definition.get("label", name.title()),
                    "type": definition.get("type", "text"),
                    "options": definition.get("options", []),
                    "value": self.request.GET.get(name, ""),
                }
            )
        return filters

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        afastamentos_queryset = self.get_afastamentos_queryset()
        paginator = Paginator(afastamentos_queryset, self.afastamentos_paginate_by)
        page = self.request.GET.get("page") or 1
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
        afastamentos = page_obj.object_list
        context["afastamento_form"] = AfastamentoForm(
            initial={"funcionario": self.object},
            tenant=self.request.tenant,
        )
        context["afastamentos_create_url"] = reverse_lazy("funcionarios:afastamentos_create")
        context["afastamento_filters"] = self.get_afastamento_filters_context()
        context["afastamentos"] = afastamentos
        context["afastamentos_page_obj"] = page_obj
        context["riscos"] = self.object.riscos.all()
        context["riscos_assign_url"] = reverse_lazy(
            "funcionarios:riscos_assign",
            args=[self.object.pk],
        )
        context["riscos_assign_form"] = RiscoAssignForm(
            tenant=self.request.tenant, funcionario=self.object
        )
        context["risco_edit_rows"] = [
            {
                "object": risco,
                "form": RiscoForm(instance=risco),
                "update_url": reverse_lazy("funcionarios:riscos_update", args=[risco.pk]),
            }
            for risco in context["riscos"]
        ]
        context["afastamento_edit_rows"] = [
            {
                "object": afastamento,
                "form": AfastamentoForm(instance=afastamento, tenant=self.request.tenant),
                "update_url": reverse_lazy("funcionarios:afastamentos_update", args=[afastamento.pk]),
            }
            for afastamento in afastamentos
        ]
        pendencias_qs = TreinamentoPendencia.objects.filter(funcionario=self.object).select_related("treinamento")
        concluidos = pendencias_qs.filter(status__in=["realizado", "aprovado", "reprovado"])
        pendentes = pendencias_qs.exclude(status__in=["realizado", "aprovado", "reprovado"])
        context["treinamentos_pendentes"] = pendentes
        context["treinamentos_concluidos"] = concluidos
        context["treinamentos_itens"] = list(pendentes) + list(concluidos)
        context["treinamentos_certificados"] = TreinamentoCertificado.objects.filter(
            funcionario=self.object
        ).select_related("treinamento", "turma")
        return context


class AdvertenciaListView(BaseTenantListView):
    model = Advertencia
    template_name = "advertencias/list.html"
    form_class = AdvertenciaForm
    title = "Advertencias"
    subtitle = "Registre advertencias por uso incorreto ou ausencia de EPI."
    headers = ["Funcionario", "Tipo", "Data", "Descricao"]
    row_fields = ["funcionario", "tipo_label", "data", "descricao"]
    filter_definitions = [
        {"name": "funcionario__nome", "label": "Funcionario", "lookup": "icontains", "type": "text"},
        {
            "name": "tipo",
            "label": "Tipo",
            "lookup": "exact",
            "type": "select",
            "options": [("", "Todos")] + list(Advertencia.TIPO_CHOICES),
        },
        {"name": "data", "label": "Data", "lookup": "exact", "type": "date"},
    ]
    create_url_name = "funcionarios:advertencias_create"
    update_url_name = "funcionarios:advertencias_update"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if context.get("can_add"):
            context["create_form"] = AdvertenciaForm(tenant=self.request.tenant)
        else:
            context["create_form"] = None
        if context.get("can_change"):
            context["edit_rows"] = [
                {
                    "object": obj,
                    "form": AdvertenciaForm(instance=obj, tenant=self.request.tenant),
                    "update_url": reverse_lazy(self.update_url_name, args=[obj.pk]),
                }
                for obj in context.get("object_list", [])
            ]
        else:
            context["edit_rows"] = []
        return context


class AdvertenciaCreateView(BaseTenantCreateView):
    model = Advertencia
    form_class = AdvertenciaForm
    success_url_name = "funcionarios:advertencias_list"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["tenant"] = self.request.tenant
        return kwargs

    def form_valid(self, form):
        response = super().form_valid(form)
        if self.request.headers.get("X-Requested-With") == "XMLHttpRequest":
            row_html = render_to_string(
                "advertencias/_advertencia_row.html",
                {"advertencia": self.object},
                request=self.request,
            )
            edit_modal_html = render_to_string(
                "advertencias/_advertencia_edit_modal.html",
                {
                    "advertencia": self.object,
                    "form": AdvertenciaForm(instance=self.object, tenant=self.request.tenant),
                    "update_url": reverse("funcionarios:advertencias_update", args=[self.object.pk]),
                },
                request=self.request,
            )
            form_html = render_to_string(
                "components/_form.html",
                {
                    "form": AdvertenciaForm(tenant=self.request.tenant),
                    "form_action": reverse("funcionarios:advertencias_create"),
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
                {"form": form, "form_action": reverse("funcionarios:advertencias_create")},
                request=self.request,
            )
            return JsonResponse({"ok": False, "form_html": form_html}, status=400)
        return super().form_invalid(form)


class AdvertenciaUpdateView(BaseTenantUpdateView):
    model = Advertencia
    form_class = AdvertenciaForm
    success_url_name = "funcionarios:advertencias_list"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["tenant"] = self.request.tenant
        return kwargs

    def form_valid(self, form):
        response = super().form_valid(form)
        if self.request.headers.get("X-Requested-With") == "XMLHttpRequest":
            row_html = render_to_string(
                "advertencias/_advertencia_row.html",
                {"advertencia": self.object},
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
                    "form_action": reverse("funcionarios:advertencias_update", args=[self.get_object().pk]),
                },
                request=self.request,
            )
            return JsonResponse(
                {"ok": False, "form_html": form_html, "row_id": self.get_object().pk},
                status=400,
            )
        return super().form_invalid(form)


class FuncionarioToggleActiveView(PermissionRequiredMixin, View):
    permission_required = "funcionarios.change_funcionario"

    def post(self, request, pk):
        funcionario = get_object_or_404(Funcionario, pk=pk, company=request.tenant)
        funcionario.ativo = not funcionario.ativo
        funcionario.save(update_fields=["ativo"])
        status_label = "ativado" if funcionario.ativo else "desativado"
        log_funcionario_event(funcionario, f"Funcionario {status_label}.", request)
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({"ok": True, "ativo": funcionario.ativo, "row_id": funcionario.pk})
        return render(request, "funcionarios/list.html")


class FuncionarioValidacaoRecebimentoView(PermissionRequiredMixin, View):
    permission_required = "funcionarios.change_funcionario"

    def get(self, request, pk):
        funcionario = get_object_or_404(Funcionario, pk=pk, company=request.tenant)
        form = FuncionarioValidacaoForm(
            initial={"validacao_recebimento": funcionario.validacao_recebimento}
        )
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            form_html = render_to_string(
                "components/_form.html",
                {
                    "form": form,
                    "form_action": reverse("funcionarios:validacao_recebimento", args=[pk]),
                },
                request=request,
            )
            return JsonResponse({"ok": True, "form_html": form_html})
        return HttpResponseRedirect(reverse("funcionarios:list"))

    def post(self, request, pk):
        funcionario = get_object_or_404(Funcionario, pk=pk, company=request.tenant)
        form = FuncionarioValidacaoForm(request.POST)
        if not form.is_valid():
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                form_html = render_to_string(
                    "components/_form.html",
                    {
                        "form": form,
                        "form_action": reverse("funcionarios:validacao_recebimento", args=[pk]),
                    },
                    request=request,
                )
                return JsonResponse({"ok": False, "form_html": form_html}, status=400)
            return HttpResponseRedirect(reverse("funcionarios:list"))
        validacao = form.cleaned_data.get("validacao_recebimento")
        senha = form.cleaned_data.get("senha_recebimento")
        funcionario.validacao_recebimento = validacao
        if validacao == "senha" and senha:
            funcionario.senha_recebimento = make_password(senha)
        if validacao != "senha":
            funcionario.senha_recebimento = ""
        funcionario.updated_by = request.user
        funcionario.save(update_fields=["validacao_recebimento", "senha_recebimento", "updated_by"])
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({"ok": True, "row_id": funcionario.pk, "validacao": validacao})
        return HttpResponseRedirect(reverse("funcionarios:list"))


class FuncionarioProdutoListView(BaseTenantListView):
    model = FuncionarioProduto
    template_name = "funcionarios/produtos_list.html"
    form_class = FuncionarioProdutoForm
    title = "Produtos liberados por funcionário"
    headers = ["Funcionario", "Produto / CA", "Fornecedor"]
    row_fields = ["funcionario", "produto_fornecedor", "produto_fornecedor.fornecedor"]
    filter_definitions = [
        {"name": "funcionario__nome", "label": "Funcionario", "lookup": "icontains", "type": "text"},
        {"name": "produto_fornecedor__produto__nome", "label": "Produto", "lookup": "icontains", "type": "text"},
    ]
    create_url_name = "funcionarios:produtos_create"
    update_url_name = "funcionarios:produtos_update"

    def get_queryset(self):
        return super().get_queryset().select_related(
            "funcionario",
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


class FuncionarioProdutoCreateView(BaseTenantCreateView):
    model = FuncionarioProduto
    form_class = FuncionarioProdutoForm
    success_url_name = "funcionarios:produtos_list"

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
            funcionario_id = item.get("funcionario_id")
            produto_fornecedor_id = item.get("produto_fornecedor_id")
            if not funcionario_id or not produto_fornecedor_id:
                errors.append(f"Item {idx}: selecione o funcionario e o produto.")
                continue
            key = (int(funcionario_id), int(produto_fornecedor_id))
            if key in seen:
                errors.append(f"Item {idx}: duplicado na lista.")
                continue
            seen.add(key)
            exists = FuncionarioProduto.objects.filter(
                company=self.request.tenant,
                funcionario_id=funcionario_id,
                produto_fornecedor_id=produto_fornecedor_id,
            ).exists()
            if exists:
                errors.append(f"Item {idx}: vinculo ja cadastrado.")
                continue
            created.append(
                FuncionarioProduto(
                    company=self.request.tenant,
                    funcionario_id=funcionario_id,
                    produto_fornecedor_id=produto_fornecedor_id,
                    created_by=self.request.user,
                    updated_by=self.request.user,
                )
            )

        if errors:
            for error in errors:
                form.add_error(None, error)
            return None

        FuncionarioProduto.objects.bulk_create(created)
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
                        "funcionarios/_funcionario_produto_row.html",
                        {"vinculo": obj},
                        request=request,
                    )
                    for obj in created
                )
                form_html = render_to_string(
                    "components/_form.html",
                    {
                        "form": self.form_class(tenant=self.request.tenant),
                        "form_action": reverse("funcionarios:produtos_create"),
                        "form_hide_actions": True,
                        "form_id": "funcionario-produto-form",
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
                "funcionarios/_funcionario_produto_row.html",
                {"vinculo": self.object},
                request=self.request,
            )
            edit_modal_html = render_to_string(
                "funcionarios/_funcionario_produto_edit_modal.html",
                {
                    "vinculo": self.object,
                    "form": FuncionarioProdutoForm(instance=self.object, tenant=self.request.tenant),
                    "update_url": reverse("funcionarios:produtos_update", args=[self.object.pk]),
                },
                request=self.request,
            )
            form_html = render_to_string(
                "components/_form.html",
                {
                    "form": FuncionarioProdutoForm(tenant=self.request.tenant),
                    "form_action": reverse("funcionarios:produtos_create"),
                    "form_hide_actions": True,
                    "form_id": "funcionario-produto-form",
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
                    "form_action": reverse("funcionarios:produtos_create"),
                    "form_hide_actions": True,
                    "form_id": "funcionario-produto-form",
                },
                request=self.request,
            )
            return JsonResponse({"ok": False, "form_html": form_html}, status=400)
        return super().form_invalid(form)


class FuncionarioProdutoUpdateView(BaseTenantUpdateView):
    model = FuncionarioProduto
    form_class = FuncionarioProdutoForm
    success_url_name = "funcionarios:produtos_list"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["tenant"] = self.request.tenant
        return kwargs

    def form_valid(self, form):
        response = super().form_valid(form)
        if self.request.headers.get("X-Requested-With") == "XMLHttpRequest":
            row_html = render_to_string(
                "funcionarios/_funcionario_produto_row.html",
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
                    "form_action": reverse("funcionarios:produtos_update", args=[self.get_object().pk]),
                },
                request=self.request,
            )
            return JsonResponse(
                {"ok": False, "form_html": form_html, "row_id": self.get_object().pk},
                status=400,
            )
        return super().form_invalid(form)


class FuncionarioProdutoToggleActiveView(PermissionRequiredMixin, View):
    permission_required = "funcionarios.change_funcionarioproduto"

    def post(self, request, pk):
        vinculo = FuncionarioProduto.objects.filter(pk=pk, company=request.tenant).first()
        if not vinculo:
            return JsonResponse({"ok": False}, status=404)
        vinculo.ativo = not vinculo.ativo
        vinculo.updated_by = request.user
        vinculo.save(update_fields=["ativo", "updated_by"])
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({"ok": True, "row_id": vinculo.pk, "ativo": vinculo.ativo})
        return HttpResponseRedirect(reverse("funcionarios:produtos_list"))


class FuncionarioProdutoDeleteView(PermissionRequiredMixin, View):
    permission_required = "funcionarios.delete_funcionarioproduto"

    def post(self, request, pk):
        vinculo = FuncionarioProduto.objects.filter(pk=pk, company=request.tenant).first()
        if not vinculo:
            return JsonResponse({"ok": False}, status=404)
        vinculo.delete()
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({"ok": True, "row_id": pk})
        return HttpResponseRedirect(reverse("funcionarios:produtos_list"))


class FuncionarioAnexoCreateView(BaseTenantCreateView):
    model = FuncionarioAnexo
    form_class = FuncionarioAnexoForm

    def get_success_url(self):
        return reverse("funcionarios:list")

    def form_valid(self, form):
        funcionario_id = self.request.POST.get("funcionario")
        if not funcionario_id:
            form.add_error(None, "Funcionario obrigatorio.")
            return self.form_invalid(form)
        funcionario = Funcionario.objects.filter(pk=funcionario_id, company=self.request.tenant).first()
        if not funcionario:
            form.add_error(None, "Funcionario invalido.")
            return self.form_invalid(form)
        form.instance.funcionario = funcionario
        response = super().form_valid(form)
        descricao = form.cleaned_data.get("descricao") or self.object.arquivo.name
        log_funcionario_event(
            funcionario,
            f"Anexo adicionado: {descricao}.",
            self.request,
        )
        if self.request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({"ok": True})
        return response

    def form_invalid(self, form):
        if self.request.headers.get("X-Requested-With") == "XMLHttpRequest":
            form_html = render_to_string(
                "components/_form.html",
                {"form": form, "form_action": reverse_lazy("funcionarios:anexos_create")},
                request=self.request,
            )
            return JsonResponse({"ok": False, "form_html": form_html}, status=400)
        return super().form_invalid(form)


class FuncionarioAnexoListView(View):
    def get(self, request, pk):
        funcionario = get_object_or_404(Funcionario, pk=pk, company=request.tenant)
        anexos = funcionario.anexos.all()
        rows_html = render_to_string(
            "funcionarios/_anexo_rows.html",
            {"anexos": anexos},
            request=request,
        )
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({"ok": True, "rows_html": rows_html})
        return render(request, "funcionarios/list.html")


# Afastamento

class AfastamentoListView(BaseTenantListView):
    model = Afastamento
    template_name = "funcionarios/afastamentos_list.html"
    form_class = AfastamentoForm
    title = "Afastamentos"
    headers = [
        "Data Inicio",
        "Data Fim",
        "Qtde. Dias Afastado",
        "Motivo de Afastamento",
        "Nome do Arquivo",
    ]
    row_fields = ["data_inicio", "data_fim", "dias_afastado", "motivo", "nome_arquivo"]
    create_url_name = "funcionarios:afastamentos_create"
    update_url_name = "funcionarios:afastamentos_update"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["create_form"] = AfastamentoForm(tenant=self.request.tenant)
        context["edit_rows"] = [
            {
                "object": obj,
                "form": AfastamentoForm(instance=obj, tenant=self.request.tenant),
                "update_url": reverse_lazy(self.update_url_name, args=[obj.pk]),
            }
            for obj in context["object_list"]
        ]
        return context


class AfastamentoCreateView(BaseTenantCreateView):
    model = Afastamento
    form_class = AfastamentoForm

    def get_initial(self):
        initial = super().get_initial()
        funcionario_id = self.request.GET.get("funcionario")
        if funcionario_id:
            initial["funcionario"] = funcionario_id
        return initial

    def get_success_url(self):
        return reverse("funcionarios:detail", args=[self.object.funcionario_id])

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["tenant"] = self.request.tenant
        return kwargs

    def form_valid(self, form):
        response = super().form_valid(form)
        descricao = (
            f"Afastamento criado: {self.object.data_inicio} a {self.object.data_fim}"
        )
        if self.object.motivo:
            descricao = f"{descricao} ({self.object.motivo})."
        else:
            descricao = f"{descricao}."
        log_funcionario_event(self.object.funcionario, descricao, self.request)
        if self.request.headers.get("X-Requested-With") == "XMLHttpRequest":
            row_html = render_to_string(
                "funcionarios/_afastamento_row.html",
                {"afastamento": self.object},
                request=self.request,
            )
            form_html = render_to_string(
                "components/_form.html",
                {
                    "form": AfastamentoForm(
                        initial={"funcionario": self.object.funcionario},
                        tenant=self.request.tenant,
                    ),
                    "form_action": reverse_lazy("funcionarios:afastamentos_create"),
                },
                request=self.request,
            )
            return JsonResponse(
                {"ok": True, "action": "create", "row_html": row_html, "form_html": form_html}
            )
        return response

    def form_invalid(self, form):
        if self.request.headers.get("X-Requested-With") == "XMLHttpRequest":
            form_html = render_to_string(
                "components/_form.html",
                {"form": form, "form_action": reverse_lazy("funcionarios:afastamentos_create")},
                request=self.request,
            )
            return JsonResponse({"ok": False, "form_html": form_html}, status=400)
        return super().form_invalid(form)


class AfastamentoUpdateView(BaseTenantUpdateView):
    model = Afastamento
    form_class = AfastamentoForm

    def get_success_url(self):
        return reverse("funcionarios:detail", args=[self.object.funcionario_id])

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["tenant"] = self.request.tenant
        return kwargs

    def form_valid(self, form):
        response = super().form_valid(form)
        descricao = (
            f"Afastamento atualizado: {self.object.data_inicio} a {self.object.data_fim}"
        )
        if self.object.motivo:
            descricao = f"{descricao} ({self.object.motivo})."
        else:
            descricao = f"{descricao}."
        log_funcionario_event(self.object.funcionario, descricao, self.request)
        if self.request.headers.get("X-Requested-With") == "XMLHttpRequest":
            row_html = render_to_string(
                "funcionarios/_afastamento_row.html",
                {"afastamento": self.object},
                request=self.request,
            )
            return JsonResponse(
                {
                    "ok": True,
                    "action": "update",
                    "row_html": row_html,
                    "row_id": self.object.pk,
                }
            )
        return response

    def form_invalid(self, form):
        if self.request.headers.get("X-Requested-With") == "XMLHttpRequest":
            form_html = render_to_string(
                "components/_form.html",
                {
                    "form": form,
                    "form_action": reverse_lazy("funcionarios:afastamentos_update", args=[self.get_object().pk]),
                },
                request=self.request,
            )
            return JsonResponse(
                {"ok": False, "form_html": form_html, "row_id": self.get_object().pk},
                status=400,
            )
        self.object = self.get_object()
        funcionario = self.object.funcionario
        context = {
            "object": funcionario,
            "afastamento_form": AfastamentoForm(
                initial={"funcionario": funcionario},
                tenant=self.request.tenant,
            ),
            "afastamentos_create_url": reverse_lazy("funcionarios:afastamentos_create"),
            "afastamento_edit_rows": [
                {
                    "object": afastamento,
                    "form": (
                        form
                        if afastamento.pk == self.object.pk
                        else AfastamentoForm(instance=afastamento, tenant=self.request.tenant)
                    ),
                    "update_url": reverse_lazy("funcionarios:afastamentos_update", args=[afastamento.pk]),
                }
                for afastamento in funcionario.afastamentos.all()
            ],
            "afastamento_edit_errors_id": self.object.pk,
        }
        return render(self.request, "funcionarios/detail.html", context)


class RiscoListView(BaseTenantListView):
    model = Risco
    template_name = "funcionarios/riscos_list.html"
    form_class = RiscoForm
    title = "Riscos"
    headers = ["Nome", "Nivel", "Status"]
    row_fields = ["nome", "nivel", "ativo"]
    create_url_name = "funcionarios:riscos_create"
    update_url_name = "funcionarios:riscos_update"


class RiscoCreateView(BaseTenantCreateView):
    model = Risco
    form_class = RiscoForm

    def get_success_url(self):
        return reverse("funcionarios:riscos_list")

    def form_valid(self, form):
        response = super().form_valid(form)
        if self.request.headers.get("X-Requested-With") == "XMLHttpRequest":
            show_delete = self.request.POST.get("show_delete") == "1"
            row_html = render_to_string(
                "funcionarios/_risco_row.html",
                {"risco": self.object, "show_delete": show_delete},
                request=self.request,
            )
            form_html = render_to_string(
                "components/_form.html",
                {
                    "form": RiscoForm(),
                    "form_action": reverse_lazy("funcionarios:riscos_create"),
                },
                request=self.request,
            )
            edit_modal_html = render_to_string(
                "funcionarios/_risco_edit_modal.html",
                {
                    "risco": self.object,
                    "form": RiscoForm(instance=self.object),
                    "update_url": reverse_lazy("funcionarios:riscos_update", args=[self.object.pk]),
                    "show_delete": show_delete,
                },
                request=self.request,
            )
            return JsonResponse(
                {
                    "ok": True,
                    "action": "create",
                    "row_html": row_html,
                    "form_html": form_html,
                    "edit_modal_html": edit_modal_html,
                    "row_id": self.object.pk,
                }
            )
        return response

    def form_invalid(self, form):
        if self.request.headers.get("X-Requested-With") == "XMLHttpRequest":
            form_html = render_to_string(
                "components/_form.html",
                {"form": form, "form_action": reverse_lazy("funcionarios:riscos_create")},
                request=self.request,
            )
            return JsonResponse({"ok": False, "form_html": form_html}, status=400)
        return super().form_invalid(form)


class RiscoUpdateView(BaseTenantUpdateView):
    model = Risco
    form_class = RiscoForm

    def get_success_url(self):
        return reverse("funcionarios:riscos_list")

    def form_valid(self, form):
        response = super().form_valid(form)
        if self.request.headers.get("X-Requested-With") == "XMLHttpRequest":
            funcionario_id = self.request.POST.get("funcionario")
            funcionario = None
            if funcionario_id:
                funcionario = Funcionario.objects.filter(
                    pk=funcionario_id, company=self.request.tenant
                ).first()
            show_delete = self.request.POST.get("show_delete") == "1"
            row_html = render_to_string(
                "funcionarios/_risco_row.html",
                {
                    "risco": self.object,
                    "funcionario": funcionario,
                    "show_unassign": bool(funcionario),
                    "show_delete": show_delete,
                },
                request=self.request,
            )
            return JsonResponse(
                {
                    "ok": True,
                    "action": "update",
                    "row_html": row_html,
                    "row_id": self.object.pk,
                }
            )
        return response

    def form_invalid(self, form):
        if self.request.headers.get("X-Requested-With") == "XMLHttpRequest":
            form_html = render_to_string(
                "components/_form.html",
                {
                    "form": form,
                    "form_action": reverse_lazy("funcionarios:riscos_update", args=[self.get_object().pk]),
                },
                request=self.request,
            )
            return JsonResponse({"ok": False, "form_html": form_html, "row_id": self.get_object().pk}, status=400)
        return super().form_invalid(form)


class RiscoAssignView(View):
    def post(self, request, pk):
        funcionario = get_object_or_404(Funcionario, pk=pk, company=request.tenant)
        form = RiscoAssignForm(request.POST, tenant=request.tenant, funcionario=funcionario)
        if form.is_valid():
            atuais_ids = set(funcionario.riscos.values_list("pk", flat=True))
            novos_ids = {risco.pk for risco in form.cleaned_data["riscos"]}
            adicionados_ids = novos_ids - atuais_ids
            removidos_ids = atuais_ids - novos_ids
            funcionario.riscos.set(novos_ids)
            for risco in Risco.objects.filter(pk__in=adicionados_ids):
                log_funcionario_event(
                    funcionario,
                    f"Risco atribuido: {risco.nome}.",
                    request,
                )
            for risco in Risco.objects.filter(pk__in=removidos_ids):
                log_funcionario_event(
                    funcionario,
                    f"Risco removido: {risco.nome}.",
                    request,
                )
            riscos = funcionario.riscos.all()
            rows_html = render_to_string(
                "funcionarios/_risco_rows.html",
                {"riscos": riscos, "funcionario": funcionario, "show_unassign": True},
                request=request,
            )
            modals_html = "".join(
                render_to_string(
                    "funcionarios/_risco_edit_modal.html",
                    {
                        "risco": risco,
                        "form": RiscoForm(instance=risco),
                        "update_url": reverse_lazy("funcionarios:riscos_update", args=[risco.pk]),
                        "funcionario": funcionario,
                    },
                    request=request,
                )
                for risco in riscos
            )
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return JsonResponse({"ok": True, "rows_html": rows_html, "modals_html": modals_html})
            return render(request, "funcionarios/detail.html", {"object": funcionario})

        form_html = render_to_string(
            "components/_form.html",
            {"form": form, "form_action": reverse_lazy("funcionarios:riscos_assign", args=[pk])},
            request=request,
        )
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({"ok": False, "form_html": form_html}, status=400)
        return render(request, "funcionarios/detail.html", {"object": funcionario, "form": form})


class RiscoUnassignView(View):
    def post(self, request, pk, risco_pk):
        funcionario = get_object_or_404(Funcionario, pk=pk, company=request.tenant)
        risco = get_object_or_404(Risco, pk=risco_pk, company=request.tenant)
        funcionario.riscos.remove(risco)
        log_funcionario_event(
            funcionario,
            f"Risco removido: {risco.nome}.",
            request,
        )
        riscos = funcionario.riscos.all()
        rows_html = render_to_string(
            "funcionarios/_risco_rows.html",
            {"riscos": riscos, "funcionario": funcionario, "show_unassign": True},
            request=request,
        )
        modals_html = "".join(
            render_to_string(
                "funcionarios/_risco_edit_modal.html",
                {
                    "risco": risco_item,
                    "form": RiscoForm(instance=risco_item),
                    "update_url": reverse_lazy("funcionarios:riscos_update", args=[risco_item.pk]),
                    "funcionario": funcionario,
                },
                request=request,
            )
            for risco_item in riscos
        )
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({"ok": True, "rows_html": rows_html, "modals_html": modals_html})
        return render(request, "funcionarios/detail.html", {"object": funcionario})


class RiscoDeleteView(PermissionRequiredMixin, View):
    permission_required = "funcionarios.delete_risco"

    def post(self, request, pk):
        risco = get_object_or_404(Risco, pk=pk, company=request.tenant)
        funcionarios = list(risco.funcionarios.all())
        risco.delete()
        for funcionario in funcionarios:
            log_funcionario_event(
                funcionario,
                f"Risco excluido: {risco.nome}.",
                request,
            )
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({"ok": True, "row_id": pk})
        return render(request, "funcionarios/riscos_list.html")


class FuncionarioHistoricoListView(View):
    def get(self, request, pk):
        funcionario = get_object_or_404(Funcionario, pk=pk, company=request.tenant)
        queryset = funcionario.historico.all()
        descricao = request.GET.get("descricao")
        data_inicio = request.GET.get("data_inicio")
        data_fim = request.GET.get("data_fim")
        if descricao:
            queryset = queryset.filter(descricao__icontains=descricao)
        if data_inicio:
            queryset = queryset.filter(created_at__date__gte=data_inicio)
        if data_fim:
            queryset = queryset.filter(created_at__date__lte=data_fim)
        paginator = Paginator(queryset, 10)
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
            "funcionarios/_historico_rows.html",
            {"historico": page_obj.object_list},
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
        return render(request, "funcionarios/list.html")


# Centro de Custo

class CentroCustoListView(BaseTenantListView):
    model = CentroCusto
    template_name = "centros_custo/list.html"
    form_class = CentroCustoForm
    title = "Centros de Custo"
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
    create_url_name = "funcionarios:centro_custo_create"
    update_url_name = "funcionarios:centro_custo_update"


class CentroCustoCreateView(BaseTenantCreateView):
    model = CentroCusto
    form_class = CentroCustoForm
    success_url_name = "funcionarios:centro_custo_list"

    def form_valid(self, form):
        nome = (form.cleaned_data.get("nome") or "").strip()
        if (
            nome
            and CentroCusto.objects.filter(company=self.request.tenant, nome__iexact=nome).exists()
        ):
            form.add_error("nome", "Centro de custo ja cadastrado.")
            return self.form_invalid(form)
        response = super().form_valid(form)
        if self.request.headers.get("X-Requested-With") == "XMLHttpRequest":
            row_html = render_to_string(
                "centros_custo/_centro_custo_row.html",
                {"centro_custo": self.object},
                request=self.request,
            )
            edit_modal_html = render_to_string(
                "centros_custo/_centro_custo_edit_modal.html",
                {
                    "centro_custo": self.object,
                    "form": CentroCustoForm(instance=self.object),
                    "update_url": reverse("funcionarios:centro_custo_update", args=[self.object.pk]),
                },
                request=self.request,
            )
            form_html = render_to_string(
                "components/_form.html",
                {"form": CentroCustoForm(), "form_action": reverse("funcionarios:centro_custo_create")},
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
                {"form": form, "form_action": reverse("funcionarios:centro_custo_create")},
                request=self.request,
            )
            return JsonResponse({"ok": False, "form_html": form_html}, status=400)
        return super().form_invalid(form)


class CentroCustoUpdateView(BaseTenantUpdateView):
    model = CentroCusto
    form_class = CentroCustoForm
    success_url_name = "funcionarios:centro_custo_list"

    def form_valid(self, form):
        nome = (form.cleaned_data.get("nome") or "").strip()
        if (
            nome
            and CentroCusto.objects.filter(company=self.request.tenant, nome__iexact=nome)
            .exclude(pk=form.instance.pk)
            .exists()
        ):
            form.add_error("nome", "Centro de custo ja cadastrado.")
            return self.form_invalid(form)
        response = super().form_valid(form)
        if self.request.headers.get("X-Requested-With") == "XMLHttpRequest":
            row_html = render_to_string(
                "centros_custo/_centro_custo_row.html",
                {"centro_custo": self.object},
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
                    "form_action": reverse("funcionarios:centro_custo_update", args=[self.get_object().pk]),
                },
                request=self.request,
            )
            return JsonResponse(
                {"ok": False, "form_html": form_html, "row_id": self.get_object().pk},
                status=400,
            )
        return super().form_invalid(form)


class CentroCustoToggleActiveView(PermissionRequiredMixin, View):
    permission_required = "funcionarios.change_centrocusto"

    def post(self, request, pk):
        centro_custo = CentroCusto.objects.filter(pk=pk, company=request.tenant).first()
        if not centro_custo:
            return JsonResponse({"ok": False}, status=404)
        funcionarios = list(
            Funcionario.objects.filter(company=request.tenant, centro_custo=centro_custo)
            .values("id", "nome")
            .distinct()
        )
        if funcionarios:
            return JsonResponse(
                {"ok": False, "blocked": True, "funcionarios": funcionarios, "row_id": centro_custo.pk},
                status=400,
            )
        centro_custo.ativo = not centro_custo.ativo
        centro_custo.updated_by = request.user
        centro_custo.save(update_fields=["ativo", "updated_by"])
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            row_html = render_to_string(
                "centros_custo/_centro_custo_row.html",
                {"centro_custo": centro_custo},
                request=request,
            )
            return JsonResponse({"ok": True, "row_id": centro_custo.pk, "row_html": row_html})
        return HttpResponseRedirect(reverse("funcionarios:centro_custo_list"))


class CentroCustoDeleteView(PermissionRequiredMixin, View):
    permission_required = "funcionarios.delete_centrocusto"

    def post(self, request, pk):
        centro_custo = CentroCusto.objects.filter(pk=pk, company=request.tenant).first()
        if not centro_custo:
            return JsonResponse({"ok": False}, status=404)
        funcionarios = list(
            Funcionario.objects.filter(company=request.tenant, centro_custo=centro_custo)
            .values("id", "nome")
            .distinct()
        )
        if funcionarios:
            return JsonResponse(
                {"ok": False, "blocked": True, "funcionarios": funcionarios, "row_id": centro_custo.pk},
                status=400,
            )
        centro_custo.delete()
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({"ok": True, "row_id": pk})
        return HttpResponseRedirect(reverse("funcionarios:centro_custo_list"))


class CentroCustoUsoView(PermissionRequiredMixin, View):
    permission_required = "funcionarios.view_centrocusto"

    def get(self, request, pk):
        centro_custo = CentroCusto.objects.filter(pk=pk, company=request.tenant).first()
        if not centro_custo:
            return JsonResponse({"ok": False}, status=404)
        funcionarios = list(
            Funcionario.objects.filter(company=request.tenant, centro_custo=centro_custo)
            .values("id", "nome")
            .distinct()
        )
        return JsonResponse({"ok": True, "funcionarios": funcionarios})


class GHEListView(BaseTenantListView):
    model = GHE
    template_name = "ghes/list.html"
    form_class = GHEForm
    title = "GHE"
    headers = ["Codigo", "Descricao", "Responsavel", "Ativo"]
    row_fields = ["codigo", "descricao", "responsavel", "ativo"]
    filter_definitions = [
        {"name": "codigo", "label": "Codigo", "lookup": "icontains", "type": "text"},
        {"name": "descricao", "label": "Descricao", "lookup": "icontains", "type": "text"},
        {
            "name": "ativo",
            "label": "Ativo",
            "lookup": "exact_bool",
            "type": "select",
            "options": [("", "Todos"), ("1", "Ativo"), ("0", "Inativo")],
        },
    ]
    create_url_name = "funcionarios:ghe_create"
    update_url_name = "funcionarios:ghe_update"


class GHECreateView(BaseTenantCreateView):
    model = GHE
    form_class = GHEForm
    success_url_name = "funcionarios:ghe_list"

    def form_valid(self, form):
        codigo = (form.cleaned_data.get("codigo") or "").strip()
        if codigo and GHE.objects.filter(company=self.request.tenant, codigo__iexact=codigo).exists():
            form.add_error("codigo", "Codigo ja cadastrado.")
            return self.form_invalid(form)
        response = super().form_valid(form)
        if self.request.headers.get("X-Requested-With") == "XMLHttpRequest":
            row_html = render_to_string(
                "ghes/_ghe_row.html",
                {"ghe": self.object},
                request=self.request,
            )
            edit_modal_html = render_to_string(
                "ghes/_ghe_edit_modal.html",
                {
                    "ghe": self.object,
                    "form": GHEForm(instance=self.object),
                    "update_url": reverse("funcionarios:ghe_update", args=[self.object.pk]),
                },
                request=self.request,
            )
            form_html = render_to_string(
                "components/_form.html",
                {"form": GHEForm(), "form_action": reverse("funcionarios:ghe_create")},
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
                {"form": form, "form_action": reverse("funcionarios:ghe_create")},
                request=self.request,
            )
            return JsonResponse({"ok": False, "form_html": form_html}, status=400)
        return super().form_invalid(form)


class GHEUpdateView(BaseTenantUpdateView):
    model = GHE
    form_class = GHEForm
    success_url_name = "funcionarios:ghe_list"

    def form_valid(self, form):
        codigo = (form.cleaned_data.get("codigo") or "").strip()
        if (
            codigo
            and GHE.objects.filter(company=self.request.tenant, codigo__iexact=codigo)
            .exclude(pk=form.instance.pk)
            .exists()
        ):
            form.add_error("codigo", "Codigo ja cadastrado.")
            return self.form_invalid(form)
        response = super().form_valid(form)
        if self.request.headers.get("X-Requested-With") == "XMLHttpRequest":
            row_html = render_to_string(
                "ghes/_ghe_row.html",
                {"ghe": self.object},
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
                    "form_action": reverse("funcionarios:ghe_update", args=[self.get_object().pk]),
                },
                request=self.request,
            )
            return JsonResponse(
                {"ok": False, "form_html": form_html, "row_id": self.get_object().pk},
                status=400,
            )
        return super().form_invalid(form)


class GHEToggleActiveView(PermissionRequiredMixin, View):
    permission_required = "funcionarios.change_ghe"

    def post(self, request, pk):
        ghe = GHE.objects.filter(pk=pk, company=request.tenant).first()
        if not ghe:
            return JsonResponse({"ok": False}, status=404)
        funcionarios = list(
            Funcionario.objects.filter(company=request.tenant, ghe=ghe)
            .values("id", "nome")
            .distinct()
        )
        if funcionarios:
            return JsonResponse(
                {"ok": False, "blocked": True, "funcionarios": funcionarios, "row_id": ghe.pk},
                status=400,
            )
        ghe.ativo = not ghe.ativo
        ghe.updated_by = request.user
        ghe.save(update_fields=["ativo", "updated_by"])
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            row_html = render_to_string(
                "ghes/_ghe_row.html",
                {"ghe": ghe},
                request=request,
            )
            return JsonResponse({"ok": True, "row_id": ghe.pk, "row_html": row_html})
        return HttpResponseRedirect(reverse("funcionarios:ghe_list"))


class GHEDeleteView(PermissionRequiredMixin, View):
    permission_required = "funcionarios.delete_ghe"

    def post(self, request, pk):
        ghe = GHE.objects.filter(pk=pk, company=request.tenant).first()
        if not ghe:
            return JsonResponse({"ok": False}, status=404)
        funcionarios = list(
            Funcionario.objects.filter(company=request.tenant, ghe=ghe)
            .values("id", "nome")
            .distinct()
        )
        if funcionarios:
            return JsonResponse(
                {"ok": False, "blocked": True, "funcionarios": funcionarios, "row_id": ghe.pk},
                status=400,
            )
        ghe.delete()
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({"ok": True, "row_id": pk})
        return HttpResponseRedirect(reverse("funcionarios:ghe_list"))


class GHEUsoView(PermissionRequiredMixin, View):
    permission_required = "funcionarios.view_ghe"

    def get(self, request, pk):
        ghe = GHE.objects.filter(pk=pk, company=request.tenant).first()
        if not ghe:
            return JsonResponse({"ok": False}, status=404)
        funcionarios = list(
            Funcionario.objects.filter(company=request.tenant, ghe=ghe)
            .values("id", "nome")
            .distinct()
        )
        return JsonResponse({"ok": True, "funcionarios": funcionarios})


class TurnoListView(BaseTenantListView):
    model = Turno
    template_name = "turnos/list.html"
    form_class = TurnoForm
    title = "Turnos"
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
    create_url_name = "funcionarios:turnos_create"
    update_url_name = "funcionarios:turnos_update"


class TurnoCreateView(BaseTenantCreateView):
    model = Turno
    form_class = TurnoForm
    success_url_name = "funcionarios:turnos_list"

    def form_valid(self, form):
        nome = (form.cleaned_data.get("nome") or "").strip()
        if nome and Turno.objects.filter(company=self.request.tenant, nome__iexact=nome).exists():
            form.add_error("nome", "Turno ja cadastrado.")
            return self.form_invalid(form)
        response = super().form_valid(form)
        if self.request.headers.get("X-Requested-With") == "XMLHttpRequest":
            row_html = render_to_string(
                "turnos/_turno_row.html",
                {"turno": self.object},
                request=self.request,
            )
            edit_modal_html = render_to_string(
                "turnos/_turno_edit_modal.html",
                {
                    "turno": self.object,
                    "form": TurnoForm(instance=self.object),
                    "update_url": reverse("funcionarios:turnos_update", args=[self.object.pk]),
                },
                request=self.request,
            )
            form_html = render_to_string(
                "components/_form.html",
                {"form": TurnoForm(), "form_action": reverse("funcionarios:turnos_create")},
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
                {"form": form, "form_action": reverse("funcionarios:turnos_create")},
                request=self.request,
            )
            return JsonResponse({"ok": False, "form_html": form_html}, status=400)
        return super().form_invalid(form)


class TurnoUpdateView(BaseTenantUpdateView):
    model = Turno
    form_class = TurnoForm
    success_url_name = "funcionarios:turnos_list"

    def form_valid(self, form):
        nome = (form.cleaned_data.get("nome") or "").strip()
        if (
            nome
            and Turno.objects.filter(company=self.request.tenant, nome__iexact=nome)
            .exclude(pk=form.instance.pk)
            .exists()
        ):
            form.add_error("nome", "Turno ja cadastrado.")
            return self.form_invalid(form)
        response = super().form_valid(form)
        if self.request.headers.get("X-Requested-With") == "XMLHttpRequest":
            row_html = render_to_string(
                "turnos/_turno_row.html",
                {"turno": self.object},
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
                    "form_action": reverse("funcionarios:turnos_update", args=[self.get_object().pk]),
                },
                request=self.request,
            )
            return JsonResponse(
                {"ok": False, "form_html": form_html, "row_id": self.get_object().pk},
                status=400,
            )
        return super().form_invalid(form)


class TurnoToggleActiveView(PermissionRequiredMixin, View):
    permission_required = "funcionarios.change_turno"

    def post(self, request, pk):
        turno = Turno.objects.filter(pk=pk, company=request.tenant).first()
        if not turno:
            return JsonResponse({"ok": False}, status=404)
        turno.ativo = not turno.ativo
        turno.updated_by = request.user
        turno.save(update_fields=["ativo", "updated_by"])
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            row_html = render_to_string(
                "turnos/_turno_row.html",
                {"turno": turno},
                request=request,
            )
            return JsonResponse({"ok": True, "row_id": turno.pk, "row_html": row_html})
        return HttpResponseRedirect(reverse("funcionarios:turnos_list"))


class TurnoDeleteView(PermissionRequiredMixin, View):
    permission_required = "funcionarios.delete_turno"

    def post(self, request, pk):
        turno = Turno.objects.filter(pk=pk, company=request.tenant).first()
        if not turno:
            return JsonResponse({"ok": False}, status=404)
        turno.delete()
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({"ok": True, "row_id": pk})
        return HttpResponseRedirect(reverse("funcionarios:turnos_list"))


class MotivoAfastamentoListView(BaseTenantListView):
    model = MotivoAfastamento
    template_name = "motivos_afastamento/list.html"
    form_class = MotivoAfastamentoForm
    title = "Motivos de Afastamento"
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
    create_url_name = "funcionarios:motivos_afastamento_create"
    update_url_name = "funcionarios:motivos_afastamento_update"


class MotivoAfastamentoCreateView(BaseTenantCreateView):
    model = MotivoAfastamento
    form_class = MotivoAfastamentoForm
    success_url_name = "funcionarios:motivos_afastamento_list"

    def form_valid(self, form):
        nome = (form.cleaned_data.get("nome") or "").strip()
        if (
            nome
            and MotivoAfastamento.objects.filter(company=self.request.tenant, nome__iexact=nome).exists()
        ):
            form.add_error("nome", "Motivo ja cadastrado.")
            return self.form_invalid(form)
        response = super().form_valid(form)
        if self.request.headers.get("X-Requested-With") == "XMLHttpRequest":
            row_html = render_to_string(
                "motivos_afastamento/_motivo_afastamento_row.html",
                {"motivo": self.object},
                request=self.request,
            )
            edit_modal_html = render_to_string(
                "motivos_afastamento/_motivo_afastamento_edit_modal.html",
                {
                    "motivo": self.object,
                    "form": MotivoAfastamentoForm(instance=self.object),
                    "update_url": reverse("funcionarios:motivos_afastamento_update", args=[self.object.pk]),
                },
                request=self.request,
            )
            form_html = render_to_string(
                "components/_form.html",
                {
                    "form": MotivoAfastamentoForm(),
                    "form_action": reverse("funcionarios:motivos_afastamento_create"),
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
                {"form": form, "form_action": reverse("funcionarios:motivos_afastamento_create")},
                request=self.request,
            )
            return JsonResponse({"ok": False, "form_html": form_html}, status=400)
        return super().form_invalid(form)


class MotivoAfastamentoUpdateView(BaseTenantUpdateView):
    model = MotivoAfastamento
    form_class = MotivoAfastamentoForm
    success_url_name = "funcionarios:motivos_afastamento_list"

    def form_valid(self, form):
        nome = (form.cleaned_data.get("nome") or "").strip()
        if (
            nome
            and MotivoAfastamento.objects.filter(company=self.request.tenant, nome__iexact=nome)
            .exclude(pk=form.instance.pk)
            .exists()
        ):
            form.add_error("nome", "Motivo ja cadastrado.")
            return self.form_invalid(form)
        response = super().form_valid(form)
        if self.request.headers.get("X-Requested-With") == "XMLHttpRequest":
            row_html = render_to_string(
                "motivos_afastamento/_motivo_afastamento_row.html",
                {"motivo": self.object},
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
                    "form_action": reverse(
                        "funcionarios:motivos_afastamento_update", args=[self.get_object().pk]
                    ),
                },
                request=self.request,
            )
            return JsonResponse(
                {"ok": False, "form_html": form_html, "row_id": self.get_object().pk},
                status=400,
            )
        return super().form_invalid(form)


class MotivoAfastamentoToggleActiveView(PermissionRequiredMixin, View):
    permission_required = "funcionarios.change_motivoafastamento"

    def post(self, request, pk):
        motivo = MotivoAfastamento.objects.filter(pk=pk, company=request.tenant).first()
        if not motivo:
            return JsonResponse({"ok": False}, status=404)
        motivo.ativo = not motivo.ativo
        motivo.updated_by = request.user
        motivo.save(update_fields=["ativo", "updated_by"])
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            row_html = render_to_string(
                "motivos_afastamento/_motivo_afastamento_row.html",
                {"motivo": motivo},
                request=request,
            )
            return JsonResponse({"ok": True, "row_id": motivo.pk, "row_html": row_html})
        return HttpResponseRedirect(reverse("funcionarios:motivos_afastamento_list"))


class MotivoAfastamentoDeleteView(PermissionRequiredMixin, View):
    permission_required = "funcionarios.delete_motivoafastamento"

    def post(self, request, pk):
        motivo = MotivoAfastamento.objects.filter(pk=pk, company=request.tenant).first()
        if not motivo:
            return JsonResponse({"ok": False}, status=404)
        motivo.delete()
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({"ok": True, "row_id": pk})
        return HttpResponseRedirect(reverse("funcionarios:motivos_afastamento_list"))


class PlantaListView(BaseTenantListView):
    model = Planta
    template_name = "plantas/list.html"
    form_class = PlantaForm
    title = "Plantas"
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
    create_url_name = "funcionarios:plantas_create"
    update_url_name = "funcionarios:plantas_update"


class PlantaCreateView(BaseTenantCreateView):
    model = Planta
    form_class = PlantaForm
    success_url_name = "funcionarios:plantas_list"

    def form_valid(self, form):
        nome = (form.cleaned_data.get("nome") or "").strip()
        if nome and Planta.objects.filter(company=self.request.tenant, nome__iexact=nome).exists():
            form.add_error("nome", "Planta ja cadastrada.")
            return self.form_invalid(form)
        response = super().form_valid(form)
        if self.request.headers.get("X-Requested-With") == "XMLHttpRequest":
            row_html = render_to_string(
                "plantas/_planta_row.html",
                {"planta": self.object},
                request=self.request,
            )
            edit_modal_html = render_to_string(
                "plantas/_planta_edit_modal.html",
                {
                    "planta": self.object,
                    "form": PlantaForm(instance=self.object),
                    "update_url": reverse("funcionarios:plantas_update", args=[self.object.pk]),
                },
                request=self.request,
            )
            form_html = render_to_string(
                "components/_form.html",
                {"form": PlantaForm(), "form_action": reverse("funcionarios:plantas_create")},
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
                {"form": form, "form_action": reverse("funcionarios:plantas_create")},
                request=self.request,
            )
            return JsonResponse({"ok": False, "form_html": form_html}, status=400)
        return super().form_invalid(form)


class PlantaUpdateView(BaseTenantUpdateView):
    model = Planta
    form_class = PlantaForm
    success_url_name = "funcionarios:plantas_list"

    def form_valid(self, form):
        nome = (form.cleaned_data.get("nome") or "").strip()
        if (
            nome
            and Planta.objects.filter(company=self.request.tenant, nome__iexact=nome)
            .exclude(pk=form.instance.pk)
            .exists()
        ):
            form.add_error("nome", "Planta ja cadastrada.")
            return self.form_invalid(form)
        response = super().form_valid(form)
        if self.request.headers.get("X-Requested-With") == "XMLHttpRequest":
            row_html = render_to_string(
                "plantas/_planta_row.html",
                {"planta": self.object},
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
                {"form": form, "form_action": reverse("funcionarios:plantas_update", args=[self.get_object().pk])},
                request=self.request,
            )
            return JsonResponse(
                {"ok": False, "form_html": form_html, "row_id": self.get_object().pk},
                status=400,
            )
        return super().form_invalid(form)


class PlantaToggleActiveView(PermissionRequiredMixin, View):
    permission_required = "funcionarios.change_planta"

    def post(self, request, pk):
        planta = Planta.objects.filter(pk=pk, company=request.tenant).first()
        if not planta:
            return JsonResponse({"ok": False}, status=404)
        planta.ativo = not planta.ativo
        planta.updated_by = request.user
        planta.save(update_fields=["ativo", "updated_by"])
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            row_html = render_to_string(
                "plantas/_planta_row.html",
                {"planta": planta},
                request=request,
            )
            return JsonResponse({"ok": True, "row_id": planta.pk, "row_html": row_html})
        return HttpResponseRedirect(reverse("funcionarios:plantas_list"))


class PlantaDeleteView(PermissionRequiredMixin, View):
    permission_required = "funcionarios.delete_planta"

    def post(self, request, pk):
        planta = Planta.objects.filter(pk=pk, company=request.tenant).first()
        if not planta:
            return JsonResponse({"ok": False}, status=404)
        planta.delete()
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({"ok": True, "row_id": pk})
        return HttpResponseRedirect(reverse("funcionarios:plantas_list"))
