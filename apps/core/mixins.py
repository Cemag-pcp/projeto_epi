class TenantQuerysetMixin:
    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.filter(company=self.request.tenant)


class TenantFormMixin:
    def form_valid(self, form):
        if getattr(form.instance, "company_id", None) is None:
            form.instance.company = self.request.tenant
        if getattr(form.instance, "created_by_id", None) is None:
            form.instance.created_by = self.request.user
        form.instance.updated_by = self.request.user
        return super().form_valid(form)
