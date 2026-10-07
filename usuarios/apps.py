from django.apps import AppConfig


class UsuariosConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "usuarios"
    verbose_name = "Usuarios y auditoría"

    def ready(self):
        # Al iniciar Django se "suscribe" el observador de auditoría
        # a la señal cita_cambiada (patrón Observer, ver receptores.py).
        from . import receptores  # noqa: F401
