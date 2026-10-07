"""
Patrón Factory (versión simple).

Hay dos formas de avisar: dentro de la aplicación y por correo. Cada una es
una clase con el mismo método enviar(). La función crear_aviso() recibe el
nombre del canal y "fabrica" el objeto correcto. Quien la usa no necesita
saber cómo se envía cada aviso.

Si mañana el centro quiere avisos por WhatsApp, basta con crear la clase
AvisoWhatsApp y agregarla al diccionario CANALES, sin tocar el resto.
"""
from django.core.mail import send_mail

from .models import Notificacion


class AvisoApp:
    def enviar(self, usuario, texto):
        Notificacion.objects.create(usuario=usuario, mensaje=texto)


class AvisoCorreo:
    def enviar(self, usuario, texto):
        send_mail(
            subject="Somos Sensoriales: cambio en tu cita",
            message=texto,
            from_email=None,  # usa DEFAULT_FROM_EMAIL de settings.py
            recipient_list=[usuario.email],
        )


CANALES = {
    "app": AvisoApp,
    "correo": AvisoCorreo,
}


def crear_aviso(canal):
    if canal not in CANALES:
        raise ValueError(f"Canal de aviso desconocido: {canal}")
    return CANALES[canal]()
