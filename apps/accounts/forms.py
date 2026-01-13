from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.db.models import Q

from apps.core.forms import BootstrapModelForm
from apps.funcionarios.models import Funcionario, Planta
from apps.setores.models import Setor
from .models import UserProfile


class UserProfileForm(BootstrapModelForm):
    username = forms.CharField(label="Usuario")
    email = forms.EmailField(label="Email", required=False)
    password = forms.CharField(label="Senha", widget=forms.PasswordInput, required=False)
    group = forms.ModelChoiceField(label="Grupo de permissao", queryset=Group.objects.none())

    class Meta:
        model = UserProfile
        fields = ["funcionario", "setor", "planta"]

    def __init__(self, *args, tenant=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.tenant = tenant
        self._configure_fields()
        self._load_initial_user_data()
        self._filter_querysets()

    def _configure_fields(self):
        is_create = self.instance.pk is None
        self.fields["password"].required = is_create
        if not is_create:
            self.fields["password"].help_text = "Deixe em branco para manter a senha atual."

    def _load_initial_user_data(self):
        user = getattr(self.instance, "user", None)
        if user:
            self.fields["username"].initial = user.username
            self.fields["email"].initial = user.email
            group = user.groups.first()
            if group:
                self.fields["group"].initial = group.pk

    def _filter_querysets(self):
        if self.tenant is None:
            return
        self.fields["group"].queryset = Group.objects.order_by("name")
        funcionarios = Funcionario.objects.filter(company=self.tenant, ativo=True)
        current_id = getattr(self.instance.funcionario, "pk", None) if self.instance.pk else None
        if current_id:
            funcionarios = funcionarios.filter(Q(acesso__isnull=True) | Q(pk=current_id))
        else:
            funcionarios = funcionarios.filter(acesso__isnull=True)
        self.fields["funcionario"].queryset = funcionarios.order_by("nome")
        self.fields["setor"].queryset = Setor.objects.filter(company=self.tenant, ativo=True).order_by("nome")
        self.fields["planta"].queryset = Planta.objects.filter(company=self.tenant, ativo=True).order_by("nome")

    def clean_username(self):
        username = (self.cleaned_data.get("username") or "").strip()
        if not username:
            raise forms.ValidationError("Informe o usuario.")
        user_model = get_user_model()
        queryset = user_model.objects.filter(username__iexact=username)
        if getattr(self.instance, "user_id", None):
            queryset = queryset.exclude(pk=self.instance.user_id)
        if queryset.exists():
            raise forms.ValidationError("Usuario ja cadastrado.")
        return username

    def clean_funcionario(self):
        funcionario = self.cleaned_data.get("funcionario")
        if not funcionario:
            raise forms.ValidationError("Selecione o funcionario.")
        queryset = UserProfile.objects.filter(funcionario=funcionario)
        if self.instance.pk:
            queryset = queryset.exclude(pk=self.instance.pk)
        if queryset.exists():
            raise forms.ValidationError("Funcionario ja vinculado a um usuario.")
        return funcionario

    def clean_setor(self):
        setor = self.cleaned_data.get("setor")
        if not setor:
            raise forms.ValidationError("Selecione o setor.")
        return setor

    def clean_planta(self):
        planta = self.cleaned_data.get("planta")
        if not planta:
            raise forms.ValidationError("Selecione a planta.")
        return planta

    def save(self, commit=True):
        profile = super().save(commit=False)
        user_model = get_user_model()
        user = profile.user if getattr(profile, "user_id", None) else user_model()
        user.username = self.cleaned_data["username"]
        user.email = (self.cleaned_data.get("email") or "").strip()
        password = self.cleaned_data.get("password")
        if password:
            user.set_password(password)
        if commit:
            user.save()
            profile.user = user
            profile.save()
            group = self.cleaned_data.get("group")
            if group:
                user.groups.set([group])
        return profile


class GroupForm(BootstrapModelForm):
    permissions = forms.ModelMultipleChoiceField(
        label="Permissoes",
        required=False,
        queryset=Permission.objects.none(),
        widget=forms.SelectMultiple(attrs={"size": "10"}),
    )

    class Meta:
        model = Group
        fields = ["name", "permissions"]
        labels = {"name": "Nome"}

    def __init__(self, *args, tenant=None, **kwargs):
        super().__init__(*args, **kwargs)
        permissions = Permission.objects.select_related("content_type").order_by(
            "content_type__app_label",
            "codename",
        )
        if tenant is not None and not getattr(tenant, "estoque_enabled", True):
            permissions = permissions.exclude(content_type__app_label="estoque")
        self.fields["permissions"].queryset = permissions
