from django.conf import settings
from django.db import models


class Notificacion(models.Model):
    """Aviso que la persona ve dentro de la aplicación (RF-11)."""

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notificaciones"
    )
    mensaje = models.CharField(max_length=300)
    leida = models.BooleanField(default=False)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-fecha"]
        verbose_name = "aviso"
        verbose_name_plural = "avisos"

    def __str__(self):
        return self.mensaje
