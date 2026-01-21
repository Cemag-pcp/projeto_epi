"# projeto_epi" 

criar tenant:
- from apps.tenants.models import Company, Domain
- company = Company.objects.create(schema_name="cliente1", name="Cliente 1")
- Domain.objects.create(domain="cliente1.localhost", tenant=company, is_primary=True)


criar usuario no tenant:
- python manage.py create_tenant_superuser -s cliente1 --username admin --email admin@cliente1.local

criar e atualizar banco de ca:
- python automacao_caepi.py --insert
