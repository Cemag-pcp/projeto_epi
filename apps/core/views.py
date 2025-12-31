from django.http import HttpResponse
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from .mixins import TenantFormMixin, TenantQuerysetMixin


def home(request):
    return HttpResponse("Clarus API")


class BaseTenantListView(LoginRequiredMixin, TenantQuerysetMixin, ListView):
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
        return reverse_lazy(self.create_url_name) if self.create_url_name else ""

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = self.title
        context["subtitle"] = self.subtitle
        context["headers"] = self.headers
        context["row_fields"] = self.row_fields
        context["filters"] = self.get_filters_context()
        context["create_url"] = self.get_create_url()
        if self.form_class:
            context["create_form"] = self.form_class()
            context["edit_rows"] = [
                {
                    "object": obj,
                    "form": self.form_class(instance=obj),
                    "update_url": reverse_lazy(self.update_url_name, args=[obj.pk]),
                }
                for obj in context["object_list"]
            ]
        return context


class BaseTenantCreateView(LoginRequiredMixin, TenantFormMixin, CreateView):
    template_name = "crud/form.html"
    success_url_name = ""

    def get_success_url(self):
        return reverse_lazy(self.success_url_name)


class BaseTenantUpdateView(LoginRequiredMixin, TenantFormMixin, UpdateView):
    template_name = "crud/form.html"
    success_url_name = ""

    def get_success_url(self):
        return reverse_lazy(self.success_url_name)


class BaseTenantDetailView(LoginRequiredMixin, TenantQuerysetMixin, DetailView):
    pass
