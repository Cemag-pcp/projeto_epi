class TenantQuerysetMixin:
    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.filter(company=self.request.tenant)


class TenantFormMixin:
    def form_valid(self, form):
        from django.contrib import messages

        if getattr(form.instance, "company_id", None) is None:
            form.instance.company = self.request.tenant
        if getattr(form.instance, "created_by_id", None) is None:
            form.instance.created_by = self.request.user
        form.instance.updated_by = self.request.user

        is_ajax = self.request.headers.get("X-Requested-With") == "XMLHttpRequest"
        is_create = getattr(form.instance, "pk", None) is None
        response = super().form_valid(form)
        if not is_ajax:
            messages.success(
                self.request,
                "Criado com sucesso." if is_create else "Atualizado com sucesso.",
            )
        return response
