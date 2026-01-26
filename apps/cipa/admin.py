from django.contrib import admin

from .models import CipaCandidato, CipaEleicao, CipaVoto


@admin.register(CipaEleicao)
class CipaEleicaoAdmin(admin.ModelAdmin):
    list_display = ("nome", "escopo", "planta", "status", "votacao_inicio", "votacao_fim")
    list_filter = ("escopo", "status", "planta")
    search_fields = ("nome",)


@admin.register(CipaCandidato)
class CipaCandidatoAdmin(admin.ModelAdmin):
    list_display = ("eleicao", "funcionario", "numero", "status")
    list_filter = ("status", "eleicao")
    search_fields = ("funcionario__nome", "eleicao__nome")


@admin.register(CipaVoto)
class CipaVotoAdmin(admin.ModelAdmin):
    list_display = ("eleicao", "eleitor", "tipo", "candidato", "created_at")
    list_filter = ("tipo", "eleicao")
    search_fields = ("eleitor__nome", "candidato__funcionario__nome", "eleicao__nome")
