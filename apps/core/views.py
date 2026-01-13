from django.http import HttpResponse
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from .mixins import TenantFormMixin, TenantQuerysetMixin


def home(request):
    return HttpResponse("Clarus API")


class BaseTenantListView(PermissionRequiredMixin, LoginRequiredMixin, TenantQuerysetMixin, ListView):
    template_name = "crud/list.html"
    paginate_by = 20
    form_class = None
    title = ""
    subtitle = ""
    headers = []
    row_fields = []
    filter_definitions = []
    create_url_name = ""
    update_url_name = ""

    def _get_model_permission(self, action):
        if not self.model:
            return None
        app_label = self.model._meta.app_label
        model_name = self.model._meta.model_name
        return f"{app_label}.{action}_{model_name}"

    def get_permission_required(self):
        perm = self._get_model_permission("view")
        return (perm,) if perm else ()

    def get_queryset(self):
        queryset = super().get_queryset()
        for definition in self.filter_definitions:
            name = definition["name"]
            lookup = definition.get("lookup", "icontains")
            value = self.request.GET.get(name)
            if value in (None, ""):
                continue
            if lookup == "exact_bool":
                value = value == "1"
                lookup = "exact"
            queryset = queryset.filter(**{f"{name}__{lookup}": value})
        return queryset

    def get_filters_context(self):
        filters = []
        for definition in self.filter_definitions:
            name = definition["name"]
            filters.append(
                {
                    "name": name,
                    "label": definition.get("label", name.title()),
                    "type": definition.get("type", "text"),
                    "options": definition.get("options", []),
                    "value": self.request.GET.get(name, ""),
                }
            )
        return filters

    def get_create_url(self):
        if not self.create_url_name:
            return ""
        perm = self._get_model_permission("add")
        if perm and not self.request.user.has_perm(perm):
            return ""
        return reverse_lazy(self.create_url_name)

    def _can_add(self):
        perm = self._get_model_permission("add")
        return True if not perm else self.request.user.has_perm(perm)

    def _can_change(self):
        perm = self._get_model_permission("change")
        return True if not perm else self.request.user.has_perm(perm)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["can_add"] = self._can_add()
        context["can_change"] = self._can_change()
        context["title"] = self.title
        context["subtitle"] = self.subtitle
        context["headers"] = self.headers
        context["row_fields"] = self.row_fields
        context["filters"] = self.get_filters_context()
        context["create_url"] = self.get_create_url()
        if self.form_class:
            if context["can_add"]:
                context["create_form"] = self.form_class()
            else:
                context["create_form"] = None
            if context["can_change"]:
                context["edit_rows"] = [
                    {
                        "object": obj,
                        "form": self.form_class(instance=obj),
                        "update_url": reverse_lazy(self.update_url_name, args=[obj.pk]),
                    }
                    for obj in context["object_list"]
                ]
            else:
                context["edit_rows"] = []
        return context


class BaseTenantCreateView(PermissionRequiredMixin, LoginRequiredMixin, TenantFormMixin, CreateView):
    template_name = "crud/form.html"
    success_url_name = ""

    def get_permission_required(self):
        if not self.model:
            return ()
        app_label = self.model._meta.app_label
        model_name = self.model._meta.model_name
        return (f"{app_label}.add_{model_name}",)

    def get_success_url(self):
        return reverse_lazy(self.success_url_name)


class BaseTenantUpdateView(PermissionRequiredMixin, LoginRequiredMixin, TenantFormMixin, UpdateView):
    template_name = "crud/form.html"
    success_url_name = ""

    def get_permission_required(self):
        if not self.model:
            return ()
        app_label = self.model._meta.app_label
        model_name = self.model._meta.model_name
        return (f"{app_label}.change_{model_name}",)

    def get_success_url(self):
        return reverse_lazy(self.success_url_name)


class BaseTenantDetailView(PermissionRequiredMixin, LoginRequiredMixin, TenantQuerysetMixin, DetailView):
    def get_permission_required(self):
        if not self.model:
            return ()
        app_label = self.model._meta.app_label
        model_name = self.model._meta.model_name
        return (f"{app_label}.view_{model_name}",)
