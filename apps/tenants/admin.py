from django.contrib import admin

from .models import Company, Domain


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ("name", "schema_name", "estoque_enabled", "on_trial", "paid_until")
    list_filter = ("estoque_enabled", "on_trial")
    search_fields = ("name", "schema_name")
    ordering = ("name",)
    fieldsets = (
        (None, {"fields": ("name", "schema_name")}),
        ("Acesso", {"fields": ("estoque_enabled",)}),
        ("Assinatura", {"fields": ("on_trial", "paid_until")}),
    )


@admin.register(Domain)
class DomainAdmin(admin.ModelAdmin):
    list_display = ("domain", "tenant", "is_primary")
    list_filter = ("is_primary",)
    search_fields = ("domain", "tenant__name", "tenant__schema_name")
