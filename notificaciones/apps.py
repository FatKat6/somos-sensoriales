from django.apps import AppConfig


class NotificacionesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "notificaciones"
    verbose_name = "Avisos"

    def ready(self):
        # Suscribe el observador de avisos a la señal cita_cambiada.
        from . import receptores  # noqa: F401
