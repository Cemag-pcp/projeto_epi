from apps.fornecedores.models import Fornecedor
from apps.produtos.models import Produto, ProdutoFornecedor


DEFAULT_FORNECEDOR_PLACEHOLDER_NOME = "Sem fornecedor"


def ensure_produtofornecedor_placeholders(company):
    """
    Garante que produtos ativos sem fornecedor tenham um ProdutoFornecedor
    associado a um fornecedor "placeholder", para que aparecam em selects.
    """
    if company is None:
        return

    fornecedor_placeholder, _ = Fornecedor.objects.get_or_create(
        company=company,
        nome=DEFAULT_FORNECEDOR_PLACEHOLDER_NOME,
        defaults={"ativo": True},
    )
    if not fornecedor_placeholder.ativo:
        fornecedor_placeholder.ativo = True
        fornecedor_placeholder.save(update_fields=["ativo"])

    missing_produto_ids = list(
        Produto.objects.filter(company=company, ativo=True)
        .exclude(fornecedores_rel__company=company)
        .values_list("pk", flat=True)
    )
    if not missing_produto_ids:
        return

    ProdutoFornecedor.objects.bulk_create(
        [
            ProdutoFornecedor(
                company=company,
                produto_id=produto_id,
                fornecedor=fornecedor_placeholder,
            )
            for produto_id in missing_produto_ids
        ],
        ignore_conflicts=True,
    )

