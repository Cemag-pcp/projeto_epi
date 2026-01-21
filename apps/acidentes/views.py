import json
import re
from urllib.error import URLError, HTTPError
from urllib.request import urlopen

from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.http import Http404
from django.http import JsonResponse
from django.template.loader import render_to_string
from django.urls import reverse
from django.views import View

from apps.core.views import BaseTenantCreateView, BaseTenantListView, BaseTenantUpdateView

from .forms import AcidenteTrabalhoForm
from .models import AcidenteTrabalho


AMBIENTES_POR_TIPO_LOCAL = {
    "estabelecimento_brasil": [
        "Area administrativa",
        "Area operacional",
        "Area externa",
        "Outros",
    ],
    "estabelecimento_exterior": [
        "Area administrativa",
        "Area operacional",
        "Area externa",
        "Outros",
    ],
    "estabelecimento_terceiros": [
        "Area do contratante",
        "Area de terceiros",
        "Outros",
    ],
    "via_publica": [
        "Calcada",
        "Pista",
        "Canteiro",
        "Outros",
    ],
    "area_rural": [
        "Plantacao",
        "Pasto",
        "Galpao",
        "Outros",
    ],
    "embarcacao": [
        "Conves",
        "Casa de maquinas",
        "Cabine",
        "Outros",
    ],
    "outros": ["Outros"],
}


class AcidenteTrabalhoListView(BaseTenantListView):
    model = AcidenteTrabalho
    template_name = "acidentes/list.html"
    form_class = None
    paginate_by = 10
    title = "Acidente do trabalho"
    subtitle = "Registros e investigacao de acidentes."
    headers = ["Funcionario", "Data", "Tipo do local", "Cidade/UF"]
    row_fields = ["funcionario", "data_ocorrencia", "get_tipo_local_display", "cidade_uf"]
    filter_definitions = [
        {"name": "funcionario__nome", "label": "Funcionario", "lookup": "icontains", "type": "text"},
        {"name": "estado", "label": "Estado", "lookup": "exact", "type": "select", "options": AcidenteTrabalho.ESTADO_CHOICES},
        {"name": "tipo_local", "label": "Tipo do local", "lookup": "exact", "type": "select", "options": AcidenteTrabalho.TIPO_LOCAL_CHOICES},
    ]
    create_url_name = "acidentes:create"

    def get_queryset(self):
        qs = super().get_queryset().select_related("funcionario")
        planta_id = self.request.session.get("planta_id")
        if planta_id:
            qs = qs.filter(funcionario__planta_id=planta_id)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        planta_id = self.request.session.get("planta_id")
        can_add = self.request.user.has_perm("acidentes.add_acidentetrabalho")
        can_change = self.request.user.has_perm("acidentes.change_acidentetrabalho")
        context["can_add"] = can_add
        context["can_change"] = can_change
        context["create_url"] = reverse("acidentes:create") if can_add else ""
        context["create_form"] = (
            AcidenteTrabalhoForm(tenant=self.request.tenant, planta_id=planta_id) if can_add else None
        )
        context["edit_rows"] = []
        if can_change:
            context["edit_rows"] = [
                {
                    "object": obj,
                    "form": AcidenteTrabalhoForm(
                        instance=obj,
                        tenant=self.request.tenant,
                        planta_id=planta_id,
                    ),
                    "update_url": reverse("acidentes:update", args=[obj.pk]),
                }
                for obj in context.get("object_list", [])
            ]
        context["api_ambientes_url"] = reverse("acidentes:api_ambientes")
        context["api_cidades_url"] = reverse("acidentes:api_cidades")
        context["api_cep_url"] = reverse("acidentes:api_cep")
        return context


class AcidenteTrabalhoCreateView(BaseTenantCreateView):
    model = AcidenteTrabalho
    form_class = AcidenteTrabalhoForm
    success_url_name = "acidentes:list"

    def get(self, request, *args, **kwargs):
        raise Http404

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["tenant"] = self.request.tenant
        kwargs["planta_id"] = self.request.session.get("planta_id")
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Novo acidente"
        context["form_cancel_url"] = reverse("acidentes:list")
        context["api_ambientes_url"] = reverse("acidentes:api_ambientes")
        context["api_cidades_url"] = reverse("acidentes:api_cidades")
        context["api_cep_url"] = reverse("acidentes:api_cep")
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        if self.request.headers.get("X-Requested-With") == "XMLHttpRequest":
            row_html = render_to_string(
                "acidentes/_acidente_row.html",
                {"acidente": self.object},
                request=self.request,
            )
            edit_modal_html = render_to_string(
                "acidentes/_acidente_edit_modal.html",
                {
                    "acidente": self.object,
                    "form": AcidenteTrabalhoForm(
                        instance=self.object,
                        tenant=self.request.tenant,
                        planta_id=self.request.session.get("planta_id"),
                    ),
                    "update_url": reverse("acidentes:update", args=[self.object.pk]),
                },
                request=self.request,
            )
            form_html = render_to_string(
                "acidentes/_acidente_form.html",
                {
                    "form": AcidenteTrabalhoForm(
                        tenant=self.request.tenant,
                        planta_id=self.request.session.get("planta_id"),
                    ),
                    "form_action": reverse("acidentes:create"),
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
                "acidentes/_acidente_form.html",
                {"form": form, "form_action": reverse("acidentes:create")},
                request=self.request,
            )
            return JsonResponse({"ok": False, "form_html": form_html}, status=400)
        return super().form_invalid(form)


class AcidenteTrabalhoUpdateView(BaseTenantUpdateView):
    model = AcidenteTrabalho
    form_class = AcidenteTrabalhoForm
    template_name = "acidentes/form.html"
    success_url_name = "acidentes:list"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["tenant"] = self.request.tenant
        kwargs["planta_id"] = self.request.session.get("planta_id")
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = f"Editar acidente #{self.object.pk}"
        context["form_cancel_url"] = reverse("acidentes:list")
        context["api_ambientes_url"] = reverse("acidentes:api_ambientes")
        context["api_cidades_url"] = reverse("acidentes:api_cidades")
        context["api_cep_url"] = reverse("acidentes:api_cep")
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        if self.request.headers.get("X-Requested-With") == "XMLHttpRequest":
            row_html = render_to_string(
                "acidentes/_acidente_row.html",
                {"acidente": self.object},
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
                "acidentes/_acidente_form.html",
                {"form": form, "form_action": reverse("acidentes:update", args=[self.get_object().pk])},
                request=self.request,
            )
            return JsonResponse({"ok": False, "form_html": form_html, "row_id": self.get_object().pk}, status=400)
        return super().form_invalid(form)


class AmbientesApiView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = "acidentes.view_acidentetrabalho"

    def get(self, request):
        tipo_local = (request.GET.get("tipo_local") or "").strip()
        ambientes = AMBIENTES_POR_TIPO_LOCAL.get(tipo_local, [])
        return JsonResponse(
            {
                "ok": True,
                "tipo_local": tipo_local,
                "ambientes": [{"value": item, "label": item} for item in ambientes],
            }
        )


class CidadesApiView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = "acidentes.view_acidentetrabalho"

    def get(self, request):
        uf = (request.GET.get("uf") or "").strip().upper()
        if not re.fullmatch(r"[A-Z]{2}", uf or ""):
            return JsonResponse({"ok": True, "uf": uf, "cidades": []})
        url = f"https://servicodados.ibge.gov.br/api/v1/localidades/estados/{uf}/municipios?orderBy=nome"
        try:
            with urlopen(url, timeout=4) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (URLError, HTTPError, TimeoutError, json.JSONDecodeError):
            return JsonResponse({"ok": False, "uf": uf, "cidades": []}, status=200)
        cidades = []
        for item in payload or []:
            nome = (item or {}).get("nome")
            if nome:
                cidades.append({"value": nome, "label": nome})
        return JsonResponse({"ok": True, "uf": uf, "cidades": cidades})


class CepLookupApiView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = "acidentes.view_acidentetrabalho"

    def get(self, request):
        cep = (request.GET.get("cep") or "").strip()
        cep_digits = re.sub(r"\\D+", "", cep)
        if len(cep_digits) != 8:
            return JsonResponse({"ok": False, "message": "CEP invalido."}, status=400)
        url = f"https://viacep.com.br/ws/{cep_digits}/json/"
        try:
            with urlopen(url, timeout=4) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (URLError, HTTPError, TimeoutError, json.JSONDecodeError):
            return JsonResponse({"ok": False, "message": "Falha ao consultar CEP."}, status=200)
        if payload.get("erro"):
            return JsonResponse({"ok": False, "message": "CEP nao encontrado."}, status=200)
        return JsonResponse(
            {
                "ok": True,
                "cep": payload.get("cep") or cep_digits,
                "uf": payload.get("uf") or "",
                "cidade": payload.get("localidade") or "",
                "bairro": payload.get("bairro") or "",
                "endereco": payload.get("logradouro") or "",
                "complemento": payload.get("complemento") or "",
            }
        )
