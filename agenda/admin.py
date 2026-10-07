from django.contrib import admin

from .models import BloqueHorario, CentroTerapeutico, Cita


@admin.register(CentroTerapeutico)
class CentroAdmin(admin.ModelAdmin):
    list_display = ["nombre", "horas_minimas_cancelacion", "duracion_bloque"]

    def has_add_permission(self, request):
        # Singleton: si ya existe el centro, no se puede agregar otro
        return not CentroTerapeutico.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(BloqueHorario)
class BloqueAdmin(admin.ModelAdmin):
    list_display = ["inicio", "especialista", "disponible"]
    list_filter = ["especialista", "disponible"]


@admin.register(Cita)
class CitaAdmin(admin.ModelAdmin):
    """El administrador NO ve el motivo de consulta (RNF-05, privacidad)."""

    list_display = ["id", "paciente", "bloque", "estado"]
    list_filter = ["estado"]
    exclude = ["motivo_consulta"]
    readonly_fields = ["paciente", "bloque", "estado", "motivo_respuesta"]
