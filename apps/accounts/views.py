from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.auth.models import Group
from django.http import JsonResponse, HttpResponseRedirect
from django.template.loader import render_to_string
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import CreateView, ListView, UpdateView

from apps.core.views import BaseTenantCreateView, BaseTenantListView, BaseTenantUpdateView
from .forms import GroupForm, UserProfileForm
from .models import UserProfile


class UserProfileListView(BaseTenantListView):
    model = UserProfile
    template_name = "accounts/list.html"
    form_class = UserProfileForm
    title = "Usuarios"
    headers = ["Usuario", "Funcionario", "Setor", "Planta", "Grupo", "Status"]
    filter_definitions = [
        {"name": "user__username", "label": "Usuario", "lookup": "icontains", "type": "text"},
        {"name": "funcionario__nome", "label": "Funcionario", "lookup": "icontains", "type": "text"},
        {"name": "setor__nome", "label": "Setor", "lookup": "icontains", "type": "text"},
    ]
    create_url_name = "accounts:create"
    update_url_name = "accounts:update"

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .select_related("user", "funcionario", "setor", "planta")
            .prefetch_related("user__groups")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.form_class:
            if context.get("can_add"):
                context["create_form"] = self.form_class(tenant=self.request.tenant)
            else:
                context["create_form"] = None
            if context.get("can_change"):
                context["edit_rows"] = [
                    {
                        "object": obj,
                        "form": self.form_class(instance=obj, tenant=self.request.tenant),
                        "update_url": reverse_lazy(self.update_url_name, args=[obj.pk]),
                    }
                    for obj in context.get("object_list", [])
                ]
            else:
                context["edit_rows"] = []
        return context


class UserProfileCreateView(BaseTenantCreateView):
    model = UserProfile
    form_class = UserProfileForm
    template_name = "accounts/form.html"
    success_url_name = "accounts:list"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["tenant"] = self.request.tenant
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["cancel_url"] = reverse_lazy("accounts:list")
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        if self.request.headers.get("X-Requested-With") == "XMLHttpRequest":
            row_html = render_to_string(
                "accounts/_user_row.html",
                {"profile": self.object},
                request=self.request,
            )
            edit_modal_html = render_to_string(
                "accounts/_user_edit_modal.html",
                {
                    "profile": self.object,
                    "form": UserProfileForm(instance=self.object, tenant=self.request.tenant),
                    "update_url": reverse("accounts:update", args=[self.object.pk]),
                },
                request=self.request,
            )
            form_html = render_to_string(
                "components/_form.html",
                {"form": UserProfileForm(tenant=self.request.tenant), "form_action": reverse("accounts:create")},
                request=self.request,
            )
            return JsonResponse(
                {
                    "ok": True,
                    "action": "create",
                    "row_id": self.object.pk,
                    "row_html": row_html,
                    "edit_modal_html": edit_modal_html,
                    "form_html": form_html,
                }
            )
        return response

    def form_invalid(self, form):
        if self.request.headers.get("X-Requested-With") == "XMLHttpRequest":
            form_html = render_to_string(
                "components/_form.html",
                {"form": form, "form_action": reverse("accounts:create")},
                request=self.request,
            )
            return JsonResponse({"ok": False, "form_html": form_html}, status=400)
        return super().form_invalid(form)


class UserProfileUpdateView(BaseTenantUpdateView):
    model = UserProfile
    form_class = UserProfileForm
    template_name = "accounts/form.html"
    success_url_name = "accounts:list"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["tenant"] = self.request.tenant
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["cancel_url"] = reverse_lazy("accounts:list")
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        if self.request.headers.get("X-Requested-With") == "XMLHttpRequest":
            row_html = render_to_string(
                "accounts/_user_row.html",
                {"profile": self.object},
                request=self.request,
            )
            return JsonResponse(
                {
                    "ok": True,
                    "action": "update",
                    "row_id": self.object.pk,
                    "row_html": row_html,
                }
            )
        return response

    def form_invalid(self, form):
        if self.request.headers.get("X-Requested-With") == "XMLHttpRequest":
            form_html = render_to_string(
                "components/_form.html",
                {
                    "form": form,
                    "form_action": reverse("accounts:update", args=[self.get_object().pk]),
                },
                request=self.request,
            )
            return JsonResponse(
                {"ok": False, "form_html": form_html, "row_id": self.get_object().pk},
                status=400,
            )
        return super().form_invalid(form)


class UserProfileToggleActiveView(PermissionRequiredMixin, View):
    permission_required = "accounts.change_userprofile"

    def post(self, request, pk):
        profile = UserProfile.objects.filter(pk=pk, company=request.tenant).select_related("user").first()
        if not profile:
            return JsonResponse({"ok": False}, status=404)
        if profile.user_id == request.user.id:
            return JsonResponse(
                {"ok": False, "blocked": True, "message": "Nao e possivel desativar o proprio usuario."},
                status=400,
            )
        profile.user.is_active = not profile.user.is_active
        profile.user.save(update_fields=["is_active"])
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            row_html = render_to_string(
                "accounts/_user_row.html",
                {"profile": profile},
                request=request,
            )
            return JsonResponse({"ok": True, "row_id": profile.pk, "row_html": row_html})
        return HttpResponseRedirect(reverse("accounts:list"))


class UserProfileDeleteView(PermissionRequiredMixin, View):
    permission_required = "accounts.delete_userprofile"

    def post(self, request, pk):
        profile = UserProfile.objects.filter(pk=pk, company=request.tenant).select_related("user").first()
        if not profile:
            return JsonResponse({"ok": False}, status=404)
        if profile.user_id == request.user.id:
            return JsonResponse(
                {"ok": False, "blocked": True, "message": "Nao e possivel excluir o proprio usuario."},
                status=400,
            )
        user = profile.user
        user.delete()
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({"ok": True, "row_id": pk})
        return HttpResponseRedirect(reverse("accounts:list"))


class GroupListView(PermissionRequiredMixin, LoginRequiredMixin, ListView):
    model = Group
    template_name = "accounts/groups_list.html"
    paginate_by = 20
    form_class = GroupForm
    title = "Grupos de permissao"
    headers = ["Nome", "Permissoes"]
    filter_definitions = [
        {"name": "name", "label": "Nome", "lookup": "icontains", "type": "text"},
    ]
    create_url_name = "accounts:groups_create"
    update_url_name = "accounts:groups_update"
    permission_required = "auth.view_group"

    def get_queryset(self):
        queryset = super().get_queryset().order_by("name")
        for definition in self.filter_definitions:
            name = definition["name"]
            lookup = definition.get("lookup", "icontains")
            value = self.request.GET.get(name)
            if value in (None, ""):
                continue
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
        if not self.request.user.has_perm("auth.add_group"):
            return ""
        return reverse_lazy(self.create_url_name)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = self.title
        context["headers"] = self.headers
        context["filters"] = self.get_filters_context()
        context["create_url"] = self.get_create_url()
        if self.form_class:
            if self.request.user.has_perm("auth.add_group"):
                context["create_form"] = self.form_class(tenant=self.request.tenant)
            else:
                context["create_form"] = None
            if self.request.user.has_perm("auth.change_group"):
                context["edit_rows"] = [
                    {
                        "object": obj,
                        "form": self.form_class(instance=obj, tenant=self.request.tenant),
                        "update_url": reverse_lazy(self.update_url_name, args=[obj.pk]),
                    }
                    for obj in context.get("object_list", [])
                ]
            else:
                context["edit_rows"] = []
        return context


class GroupCreateView(PermissionRequiredMixin, LoginRequiredMixin, CreateView):
    model = Group
    form_class = GroupForm
    template_name = "accounts/group_form.html"
    permission_required = "auth.add_group"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["tenant"] = self.request.tenant
        return kwargs

    def get_success_url(self):
        return reverse_lazy("accounts:groups_list")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["cancel_url"] = reverse_lazy("accounts:groups_list")
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        if self.request.headers.get("X-Requested-With") == "XMLHttpRequest":
            row_html = render_to_string(
                "accounts/_group_row.html",
                {"group": self.object},
                request=self.request,
            )
            edit_modal_html = render_to_string(
                "accounts/_group_edit_modal.html",
                {
                    "group": self.object,
                    "form": GroupForm(instance=self.object, tenant=self.request.tenant),
                    "update_url": reverse("accounts:groups_update", args=[self.object.pk]),
                },
                request=self.request,
            )
            form_html = render_to_string(
                "components/_form.html",
                {
                    "form": GroupForm(tenant=self.request.tenant),
                    "form_action": reverse("accounts:groups_create"),
                },
                request=self.request,
            )
            return JsonResponse(
                {
                    "ok": True,
                    "action": "create",
                    "row_id": self.object.pk,
                    "row_html": row_html,
                    "edit_modal_html": edit_modal_html,
                    "form_html": form_html,
                }
            )
        return response

    def form_invalid(self, form):
        if self.request.headers.get("X-Requested-With") == "XMLHttpRequest":
            form_html = render_to_string(
                "components/_form.html",
                {"form": form, "form_action": reverse("accounts:groups_create")},
                request=self.request,
            )
            return JsonResponse({"ok": False, "form_html": form_html}, status=400)
        return super().form_invalid(form)


class GroupUpdateView(PermissionRequiredMixin, LoginRequiredMixin, UpdateView):
    model = Group
    form_class = GroupForm
    template_name = "accounts/group_form.html"
    permission_required = "auth.change_group"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["tenant"] = self.request.tenant
        return kwargs

    def get_success_url(self):
        return reverse_lazy("accounts:groups_list")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["cancel_url"] = reverse_lazy("accounts:groups_list")
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        if self.request.headers.get("X-Requested-With") == "XMLHttpRequest":
            row_html = render_to_string(
                "accounts/_group_row.html",
                {"group": self.object},
                request=self.request,
            )
            return JsonResponse(
                {
                    "ok": True,
                    "action": "update",
                    "row_id": self.object.pk,
                    "row_html": row_html,
                }
            )
        return response

    def form_invalid(self, form):
        if self.request.headers.get("X-Requested-With") == "XMLHttpRequest":
            form_html = render_to_string(
                "components/_form.html",
                {
                    "form": form,
                    "form_action": reverse("accounts:groups_update", args=[self.get_object().pk]),
                },
                request=self.request,
            )
            return JsonResponse(
                {"ok": False, "form_html": form_html, "row_id": self.get_object().pk},
                status=400,
            )
        return super().form_invalid(form)


class GroupDeleteView(PermissionRequiredMixin, LoginRequiredMixin, View):
    permission_required = "auth.delete_group"
    def post(self, request, pk):
        group = Group.objects.filter(pk=pk).first()
        if not group:
            return JsonResponse({"ok": False}, status=404)
        if group.user_set.exists():
            return JsonResponse(
                {
                    "ok": False,
                    "blocked": True,
                    "message": "Nao e possivel excluir enquanto houver usuarios vinculados.",
                },
                status=400,
            )
        group.delete()
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({"ok": True, "row_id": pk})
        return HttpResponseRedirect(reverse("accounts:groups_list"))
