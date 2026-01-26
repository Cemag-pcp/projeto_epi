from django import template
from django.http import QueryDict
from django.urls import reverse, NoReverseMatch

from apps.funcionarios.models import Planta

register = template.Library()


@register.filter
def get_attr(obj, attr_path):
    value = obj
    for part in attr_path.split("."):
        value = getattr(value, part, "")
        if callable(value):
            value = value()
    return value


@register.simple_tag
def nav_active(request, path_prefix):
    if request.path.startswith(path_prefix):
        return "active"
    return ""


@register.filter
def startswith(value, prefix):
    if value is None:
        return False
    return str(value).startswith(str(prefix))


@register.filter
def get_item(mapping, key):
    if isinstance(mapping, dict):
        return mapping.get(key)
    return None


@register.simple_tag(takes_context=True)
def querystring(context, **kwargs):
    """
    Builds a querystring preserving current request.GET, overriding with kwargs.
    Returns a string without the leading "?" so templates can do: "?{% querystring page=2 %}".
    """
    request = context.get("request")
    if request is not None and hasattr(request, "GET"):
        query = request.GET.copy()
    else:
        query = QueryDict("", mutable=True)

    for key, value in kwargs.items():
        if value in (None, ""):
            if key in query:
                del query[key]
        else:
            query[key] = str(value)

    return query.urlencode()


def _match_path(path, prefixes, exact=False):
    if not path:
        return False
    if exact:
        return path in prefixes
    return any(path.startswith(prefix) for prefix in prefixes)


def _pick_active_item(path, items):
    best_item = None
    best_len = -1
    for item in items:
        for prefix in item.get("prefixes", []):
            if path.startswith(prefix) and len(prefix) > best_len:
                best_item = item
                best_len = len(prefix)
    return best_item


@register.inclusion_tag("components/_sidebar_menu.html", takes_context=True)
def sidebar_menu(context):
    request = context.get("request")
    path = getattr(request, "path", "") or ""

    def _feature_enabled(feature):
        tenant = getattr(request, "tenant", None)
        if not tenant:
            return True
        if feature == "estoque":
            return getattr(tenant, "estoque_enabled", True)
        return True

    sections = [
        # Dashboard
        {
            "type": "link",
            "label": "Dashboard",
            "icon": "bi-speedometer2",
            "url_name": "ui-home",
            "prefixes": ["/"],
            "exact": True,
        },
        {
            "type": "link",
            "label": "Componentes",
            "icon": "bi-palette2",
            "url_name": "ui-components",
            "prefixes": ["/componentes/"],
            "exact": True,
        },
        {
            "type": "link",
            "label": "Relatorios",
            "icon": "bi-bar-chart",
            "url_name": "relatorios:list",
            "prefixes": ["/relatorios/"],
            "exact": False,
        },
        {
            "type": "group",
            "id": "treinamentosMenu",
            "label": "Treinamentos",
            "icon": "bi-journal-bookmark",
            "items": [
                {
                    "label": "Gerenciar agenda",
                    "icon": "bi-clipboard-check",
                    "url_name": "treinamentos:list",
                    "prefixes": ["/treinamentos/"],
                    "perm": "treinamentos.view_treinamento",
                },
                {
                    "label": "Instrutores",
                    "icon": "bi-person-video3",
                    "url_name": "treinamentos:instrutores_list",
                    "prefixes": ["/treinamentos/instrutores/"],
                    "perm": "treinamentos.view_instrutor",
                },
                {
                    "label": "Agenda",
                    "icon": "bi-calendar-event",
                    "url_name": "treinamentos:agenda",
                    "prefixes": ["/treinamentos/agenda/"],
                    "perm": "treinamentos.view_turma",
                },
            ],
        },
        # Funcionarios
        {
            "type": "group",
            "id": "funcionariosMenu",
            "label": "Funcionarios",
            "icon": "bi-people",
            "items": [
                {
                    "label": "Gerenciar funcionarios",
                    "icon": "bi-person",
                    "url_name": "funcionarios:list",
                    "prefixes": ["/funcionarios/"],
                    "perm": "funcionarios.view_funcionario",
                },
                {
                    "label": "Fichas de EPI",
                    "icon": "bi-file-earmark-text",
                    "url_name": "funcionarios:fichas_epi",
                    "prefixes": ["/funcionarios/fichas-epi/"],
                    "perm": "funcionarios.view_funcionario",
                },
                {
                    "label": "Advertencias",
                    "icon": "bi-exclamation-triangle",
                    "url_name": "funcionarios:advertencias_list",
                    "prefixes": ["/funcionarios/advertencias/"],
                    "perm": "funcionarios.view_advertencia",
                },
                {
                    "label": "Produtos por funcionario",
                    "icon": "bi-person-check",
                    "url_name": "funcionarios:produtos_list",
                    "prefixes": ["/funcionarios/produtos/"],
                    "perm": "funcionarios.view_funcionarioproduto",
                },
            ],
        },
        # Produtos
        {
            "type": "group",
            "id": "produtosMenu",
            "label": "Produtos",
            "icon": "bi-box-seam",
            "items": [
                {
                    "label": "Cadastro de produto",
                    "icon": "bi-box-seam",
                    "url_name": "produtos:list",
                    "prefixes": ["/produtos/"],
                    "perm": "produtos.view_produto",
                },
                {
                    "label": "Importar CA",
                    "icon": "bi-file-earmark-arrow-up",
                    "url_name": "produtos:ca_import",
                    "prefixes": ["/produtos/ca/"],
                    "perm": "produtos.view_produto",
                },
                {
                    "label": "Depositos",
                    "icon": "bi-building",
                    "url_name": "depositos:list",
                    "prefixes": ["/depositos/"],
                    "perm": "depositos.view_deposito",
                },
                {
                    "label": "Tipo de produto",
                    "icon": "bi-tags",
                    "url_name": "produtos:tipos_list",
                    "prefixes": ["/produtos/tipos/"],
                    "perm": "produtos.view_tipoproduto",
                },
                {
                    "label": "Familia de produto",
                    "icon": "bi-diagram-3",
                    "url_name": "produtos:familias_list",
                    "prefixes": ["/produtos/familias/"],
                    "perm": "produtos.view_familiaproduto",
                },
                {
                    "label": "Subfamilia de produto",
                    "icon": "bi-diagram-2",
                    "url_name": "produtos:subfamilias_list",
                    "prefixes": ["/produtos/subfamilias/"],
                    "perm": "produtos.view_subfamiliaproduto",
                },
                {
                    "label": "Local de retirada",
                    "icon": "bi-geo-alt",
                    "url_name": "produtos:locais_retirada_list",
                    "prefixes": ["/produtos/locais_retirada/"],
                    "perm": "produtos.view_localretirada",
                },
                {
                    "label": "Periodicidades",
                    "icon": "bi-calendar3",
                    "url_name": "produtos:periodicidades_list",
                    "prefixes": ["/produtos/periodicidades/"],
                    "perm": "produtos.view_periodicidade",
                },
                {
                    "label": "Unidades",
                    "icon": "bi-rulers",
                    "url_name": "produtos:unidades_list",
                    "prefixes": ["/produtos/unidades/"],
                    "perm": "produtos.view_unidadeproduto",
                },
                {
                    "label": "Localizacao de produto",
                    "icon": "bi-geo",
                    "url_name": "produtos:localizacoes_list",
                    "prefixes": ["/produtos/localizacoes/"],
                    "perm": "produtos.view_localizacaoproduto",
                },
            ],
        },
        # Outros cadastros
        {
            "type": "group",
            "id": "cadastrosMenu",
            "label": "Outros cadastros",
            "icon": "bi-folder2-open",
            "items": [
                {
                    "label": "Cargos",
                    "icon": "bi-briefcase",
                    "url_name": "cargos:list",
                    "prefixes": ["/cargos/"],
                    "perm": "cargos.view_cargo",
                },
                {
                    "label": "Setores",
                    "icon": "bi-diagram-3",
                    "url_name": "setores:list",
                    "prefixes": ["/setores/"],
                    "perm": "setores.view_setor",
                },
                {
                    "label": "Tipos de Funcionario",
                    "icon": "bi-person-badge",
                    "url_name": "tipos_funcionario:list",
                    "prefixes": ["/tipos_funcionario/"],
                    "perm": "tipos_funcionario.view_tipofuncionario",
                },
                {
                    "label": "Produtos por tipo",
                    "icon": "bi-basket",
                    "url_name": "tipos_funcionario:produtos_list",
                    "prefixes": ["/tipos_funcionario/produtos/"],
                    "perm": "tipos_funcionario.view_tipofuncionarioproduto",
                },
                {
                    "label": "Fornecedores",
                    "icon": "bi-truck",
                    "url_name": "fornecedores:list",
                    "prefixes": ["/fornecedores/"],
                    "perm": "fornecedores.view_fornecedor",
                },
                {
                    "label": "Grades",
                    "icon": "bi-list-ol",
                    "url_name": "produtos:grades_list",
                    "prefixes": ["/produtos/grades/"],
                    "perm": "produtos.view_gradeproduto",
                },
                {
                    "label": "Centro de Custo",
                    "icon": "bi-cash-stack",
                    "url_name": "funcionarios:centro_custo_list",
                    "prefixes": ["/centros_custo/"],
                    "perm": "funcionarios.view_centrocusto",
                },
                {
                    "label": "GHE",
                    "icon": "bi-shield-check",
                    "url_name": "funcionarios:ghe_list",
                    "prefixes": ["/ghes/"],
                    "perm": "funcionarios.view_ghe",
                },
                {
                    "label": "Riscos",
                    "icon": "bi-exclamation-triangle",
                    "url_name": "funcionarios:riscos_list",
                    "prefixes": ["/funcionarios/riscos/"],
                    "perm": "funcionarios.view_risco",
                },
                {
                    "label": "Turnos",
                    "icon": "bi-clock",
                    "url_name": "funcionarios:turnos_list",
                    "prefixes": ["/turnos/"],
                    "perm": "funcionarios.view_turno",
                },
                {
                    "label": "Motivos de afastamento",
                    "icon": "bi-clipboard-minus",
                    "url_name": "funcionarios:motivos_afastamento_list",
                    "prefixes": ["/motivos_afastamento/"],
                    "perm": "funcionarios.view_motivoafastamento",
                },
            ],
        },
        # Estoque
        {
            "type": "group",
            "id": "gestaoEstoque",
            "label": "Gestao de estoque",
            "icon": "bi-archive",
            "feature": "estoque",
            "items": [
                {
                    "label": "Movimentar produto",
                    "icon": "bi-arrow-left-right",
                    "url_name": "estoque:list",
                    "prefixes": ["/estoque/"],
                    "perm": "estoque.view_estoque",
                },
                {
                    "label": "Extrato de produto",
                    "icon": "bi-journal-text",
                    "url_name": "estoque:extrato",
                    "prefixes": ["/estoque/extrato/"],
                    "perm": "estoque.view_movimentacaoestoque",
                },
            ],
        },
        # Configurações
        {
            "type": "group",
            "id": "configuracoes",
            "label": "Configurações",
            "icon": "bi-gear",
            "items": [
                {
                    "label": "Grupos de permissao",
                    "icon": "bi-shield-lock",
                    "url_name": "accounts:groups_list",
                    "prefixes": ["/grupos/"],
                    "perm": "auth.view_group",
                },
                {
                    "label": "Usuarios",
                    "icon": "bi-person-lock",
                    "url_name": "accounts:list",
                    "prefixes": ["/usuarios/"],
                    "perm": "accounts.view_userprofile",
                },
                {
                    "label": "Plantas",
                    "icon": "bi-building",
                    "url_name": "funcionarios:plantas_list",
                    "prefixes": ["/plantas/"],
                    "perm": "funcionarios.view_planta",
                }
            ],
        },
        # Entregas
        {
            "type": "group",
            "id": "entregas",
            "label": "Entregas",
            "icon": "bi-box",
            "items": [
                {
                    "label": "Entregas",
                    "icon": "bi-box-arrow-up-right",
                    "url_name": "entregas:list",
                    "prefixes": ["/entregas/"],
                    "perm": "entregas.view_entrega",
                }
            ],
        },
        # Checklist
        {
            "type": "group",
            "id": "checklistMenu",
            "label": "Checklist",
            "icon": "bi-list-check",
            "items": [
                {
                    "label": "Checklists",
                    "icon": "bi-ui-checks",
                    "url_name": "checklist:list",
                    "prefixes": ["/checklists/"],
                },
            ],
        },
        # CIPA
        {
            "type": "group",
            "id": "cipaMenu",
            "label": "CIPA",
            "icon": "bi-people",
            "items": [
                {
                    "label": "Gerenciar",
                    "icon": "bi-clipboard-check",
                    "url_name": "cipa:list",
                    "prefixes": ["/cipa/"],
                },
            ],
        },
        # Acidente do trabalho
        {
            "type": "group",
            "id": "acidenteTrabalhoMenu",
            "label": "Acidente do trabalho",
            "icon": "bi-bandaid",
            "items": [
                {
                    "label": "Registros",
                    "icon": "bi-clipboard2-pulse",
                    "url_name": "acidentes:list",
                    "prefixes": ["/acidentes/"],
                },
            ],
        },
        {
            "type": "group",
            "id": "acessos",
            "label": "Acessos e EPI",
            "icon": "bi-shield-lock",
            "items": [
                {
                    "label": "Empresas parceiras",
                    "icon": "bi-building",
                    "url_name": "acessos:empresas_list",
                    "prefixes": ["/acessos/empresas/"],
                    "perm": "acessos.view_empresaparceira",
                },
                {
                    "label": "Terceiros",
                    "icon": "bi-people",
                    "url_name": "acessos:terceiros_list",
                    "prefixes": ["/acessos/terceiros/"],
                    "perm": "acessos.view_terceiro",
                },
                {
                    "label": "Consumo de terceiros",
                    "icon": "bi-box-seam",
                    "url_name": "acessos:consumos_list",
                    "prefixes": ["/acessos/consumos/"],
                    "perm": "acessos.view_consumoparceiro",
                },
            ],
        },
    ]

    def _can_view(item):
        perm = item.get("perm")
        if not perm:
            return True
        if not request or not getattr(request, "user", None) or not request.user.is_authenticated:
            return False
        return request.user.has_perm(perm)

    filtered_sections = []
    for section in sections:
        if not _feature_enabled(section.get("feature")):
            continue
        if section["type"] == "group":
            section["items"] = [item for item in section["items"] if _can_view(item)]
            if not section["items"]:
                continue
        filtered_sections.append(section)

    for section in filtered_sections:
        if section["type"] == "link":
            section["active"] = _match_path(path, section["prefixes"], section.get("exact", False))
        if section["type"] == "group":
            active_item = _pick_active_item(path, section["items"])
            expanded = False
            for item in section["items"]:
                item["active"] = item is active_item
                expanded = expanded or item["active"]
            section["expanded"] = expanded

    for section in filtered_sections:
        if "url_name" in section:
            try:
                section["url"] = reverse(section["url_name"])
            except NoReverseMatch:
                section["url"] = "#"
        if section["type"] == "group":
            for item in section["items"]:
                try:
                    item["url"] = reverse(item["url_name"])
                except NoReverseMatch:
                    item["url"] = "#"

    return {"sections": filtered_sections}


@register.inclusion_tag("components/_planta_select.html", takes_context=True)
def planta_select(context):
    request = context.get("request")
    if not request or not getattr(request, "tenant", None):
        return {"plantas": [], "selected_id": None, "next_url": "/"}
    plantas = Planta.objects.filter(company=request.tenant, ativo=True).order_by("nome")
    selected_id = request.session.get("planta_id")
    if selected_id and not plantas.filter(pk=selected_id).exists():
        selected_id = None
    if selected_id is None and plantas:
        selected_id = plantas.first().pk
    return {"plantas": plantas, "selected_id": selected_id, "next_url": request.get_full_path()}
