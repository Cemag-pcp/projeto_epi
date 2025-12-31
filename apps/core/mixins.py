class TenantQuerysetMixin:
    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.filter(company=self.request.tenant)


class TenantFormMixin:
    def form_valid(self, form):
        if getattr(form.instance, "company_id", None) is None:
            form.instance.company = self.request.tenant
        return super().form_valid(form)
