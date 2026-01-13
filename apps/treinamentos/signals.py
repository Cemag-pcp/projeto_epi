from django.db.models import Q
from django.db.models.signals import m2m_changed, post_save
from django.dispatch import receiver

from apps.funcionarios.models import Funcionario, FuncionarioProduto
from .models import Treinamento, TreinamentoPendencia, Turma


def _create_pendencias(funcionario, treinamentos):
    if not funcionario or not treinamentos:
        return
    pending = [
        TreinamentoPendencia(
            company=funcionario.company,
            funcionario=funcionario,
            treinamento=treinamento,
        )
        for treinamento in treinamentos
    ]
    TreinamentoPendencia.objects.bulk_create(pending, ignore_conflicts=True)


def _match_funcionarios_for_treinamento(treinamento):
    if not treinamento or not treinamento.company_id:
        return Funcionario.objects.none()
    filtros = Q()
    cargo_ids = list(treinamento.requisitos_cargos.values_list("id", flat=True))
    setor_ids = list(treinamento.requisitos_setores.values_list("id", flat=True))
    tipo_ids = list(treinamento.requisitos_tipos_funcionario.values_list("id", flat=True))
    if cargo_ids:
        filtros |= Q(cargo_id__in=cargo_ids)
    if setor_ids:
        filtros |= Q(setor_id__in=setor_ids)
    if tipo_ids:
        filtros |= Q(tipo_id__in=tipo_ids)
    funcionarios = Funcionario.objects.filter(company=treinamento.company, ativo=True)
    if filtros:
        funcionarios = funcionarios.filter(filtros)
    epi_ids = list(treinamento.requisitos_epis.values_list("id", flat=True))
    if epi_ids:
        funcionarios_epi = Funcionario.objects.filter(
            company=treinamento.company,
            produtos_disponiveis__ativo=True,
            produtos_disponiveis__produto_fornecedor__produto_id__in=epi_ids,
        )
        if filtros:
            funcionarios = funcionarios.filter(pk__in=funcionarios_epi.values("id"))
        else:
            funcionarios = funcionarios_epi
    return funcionarios.distinct()


@receiver(post_save, sender=Funcionario)
def gerar_pendencias_funcionario(sender, instance, **kwargs):
    if not instance or not instance.company_id:
        return
    filtros = Q()
    if instance.cargo_id:
        filtros |= Q(requisitos_cargos=instance.cargo_id)
    if instance.setor_id:
        filtros |= Q(requisitos_setores=instance.setor_id)
    if instance.tipo_id:
        filtros |= Q(requisitos_tipos_funcionario=instance.tipo_id)
    if not filtros:
        return
    treinamentos = list(
        Treinamento.objects.filter(company=instance.company, ativo=True, obrigatorio=True)
        .filter(filtros)
        .distinct()
    )
    _create_pendencias(instance, treinamentos)


@receiver(post_save, sender=FuncionarioProduto)
def gerar_pendencias_epi(sender, instance, **kwargs):
    if not instance or not instance.company_id or not instance.ativo:
        return
    produto_id = getattr(instance.produto_fornecedor, "produto_id", None)
    if not produto_id:
        return
    treinamentos = list(
        Treinamento.objects.filter(company=instance.company, ativo=True, obrigatorio=True)
        .filter(requisitos_epis=produto_id)
        .distinct()
    )
    _create_pendencias(instance.funcionario, treinamentos)


@receiver(post_save, sender=Treinamento)
def gerar_pendencias_treinamento(sender, instance, **kwargs):
    if not instance or not instance.company_id:
        return
    if not instance.ativo or not instance.obrigatorio:
        return
    funcionarios = list(_match_funcionarios_for_treinamento(instance))
    for funcionario in funcionarios:
        _create_pendencias(funcionario, [instance])


@receiver(m2m_changed, sender=Turma.participantes.through)
def gerar_pendencias_turma(sender, instance, action, pk_set, **kwargs):
    if action != "post_add" or not pk_set:
        return
    if not instance or not instance.company_id or not instance.treinamento_id:
        return
    funcionario_ids = list(pk_set)
    existentes = set(
        TreinamentoPendencia.objects.filter(
            treinamento=instance.treinamento,
            funcionario_id__in=funcionario_ids,
        ).values_list("funcionario_id", flat=True)
    )
    novos_ids = [fid for fid in funcionario_ids if fid not in existentes]
    if novos_ids:
        pendencias = [
            TreinamentoPendencia(
                company=instance.company,
                funcionario_id=func_id,
                treinamento=instance.treinamento,
                status="agendado",
            )
            for func_id in novos_ids
        ]
        TreinamentoPendencia.objects.bulk_create(pendencias, ignore_conflicts=True)
    TreinamentoPendencia.objects.filter(
        treinamento=instance.treinamento,
        funcionario_id__in=funcionario_ids,
    ).update(status="agendado")
