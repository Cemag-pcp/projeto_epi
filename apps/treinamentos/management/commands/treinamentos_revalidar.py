from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import connection
from django_tenants.utils import schema_context

from apps.tenants.models import Company
from apps.treinamentos.models import TreinamentoAlerta, TreinamentoCertificado, TreinamentoPendencia


class Command(BaseCommand):
    help = "Gera alertas de vencimento (30/15/7 dias) e reabre pendencias expiradas."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Simula sem gravar no banco.")

    def handle(self, *args, **options):
        dry_run = options.get("dry_run", False)
        today = timezone.localdate()
        alert_days = {30, 15, 7}
        max_days = max(alert_days)

        for tenant in Company.objects.all():
            with schema_context(tenant.schema_name):
                self._process_tenant(tenant, today, alert_days, max_days, dry_run)

        self.stdout.write(self.style.SUCCESS("Revalidacao concluida."))

    def _process_tenant(self, tenant, today, alert_days, max_days, dry_run):
        required_tables = {
            "treinamentos_treinamentocertificado",
            "treinamentos_treinamentopendencia",
            "treinamentos_treinamentoalerta",
        }
        existing_tables = set(connection.introspection.table_names())
        if not required_tables.issubset(existing_tables):
            self.stdout.write(
                self.style.WARNING(
                    f"[{tenant.schema_name}] tabelas de treinamentos ausentes, pulei."
                )
            )
            return
        certificados_qs = TreinamentoCertificado.objects.filter(
            validade_ate__isnull=False,
            validade_ate__gte=today,
            validade_ate__lte=today + timedelta(days=max_days),
        ).select_related("funcionario", "treinamento")

        for cert in certificados_qs:
            dias = (cert.validade_ate - today).days
            if dias not in alert_days:
                continue
            if TreinamentoAlerta.objects.filter(
                certificado=cert,
                dias_para_vencer=dias,
            ).exists():
                continue
            if dry_run:
                continue
            TreinamentoAlerta.objects.create(
                company=tenant,
                certificado=cert,
                funcionario=cert.funcionario,
                treinamento=cert.treinamento,
                dias_para_vencer=dias,
            )

        expirados_qs = TreinamentoCertificado.objects.filter(
            validade_ate__isnull=False,
            validade_ate__lt=today,
        ).select_related("funcionario", "treinamento")

        for cert in expirados_qs:
            pendencia = TreinamentoPendencia.objects.filter(
                funcionario=cert.funcionario,
                treinamento=cert.treinamento,
            ).first()
            if pendencia:
                if pendencia.status != "pendente":
                    if dry_run:
                        continue
                    pendencia.status = "pendente"
                    pendencia.updated_by = None
                    pendencia.save(update_fields=["status", "updated_by", "updated_at"])
                continue
            if dry_run:
                continue
            TreinamentoPendencia.objects.create(
                company=tenant,
                funcionario=cert.funcionario,
                treinamento=cert.treinamento,
                status="pendente",
            )
