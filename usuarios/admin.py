from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import RegistroAuditoria, Usuario


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    """El administrador crea, edita y desactiva cuentas (RF-12)."""

    list_display = ["email", "first_name", "last_name", "rol", "especialidad", "is_active"]
    list_filter = ["rol", "is_active"]
    search_fields = ["email", "first_name", "last_name"]
    fieldsets = UserAdmin.fieldsets + (
        ("Datos del centro", {"fields": ["rol", "telefono", "rut", "nombre_tutor",
                                          "especialidad", "fecha_consentimiento"]}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("Datos del centro", {"fields": ["email", "first_name", "last_name", "rol", "especialidad"]}),
    )


@admin.register(RegistroAuditoria)
class RegistroAuditoriaAdmin(admin.ModelAdmin):
    """Solo lectura: nadie puede agregar, cambiar ni borrar registros."""

    list_display = ["fecha", "accion", "correo", "detalle", "ip"]
    list_filter = ["accion"]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
