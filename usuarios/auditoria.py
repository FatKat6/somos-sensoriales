"""Funciones de ayuda para la auditoría y el bloqueo por intentos fallidos."""
from datetime import timedelta

from django.utils import timezone

from .models import RegistroAuditoria

# Reglas del inicio de sesión (RF-01)
MAX_INTENTOS = 5
MINUTOS_BLOQUEO = 15


def registrar(accion, request=None, usuario=None, correo="", detalle=""):
    ip = None
    if request is not None:
        ip = request.META.get("REMOTE_ADDR")
        if usuario is None and request.user.is_authenticated:
            usuario = request.user
    RegistroAuditoria.objects.create(
        usuario=usuario,
        correo=correo or (usuario.email if usuario else ""),
        accion=accion,
        detalle=detalle[:300],
        ip=ip,
    )


def demasiados_intentos(correo):
    """
    True si hubo 5 o más intentos fallidos con ese correo en los últimos
    15 minutos. Se cuentan en la auditoría, así funciona igual exista o no
    la cuenta y no se revela qué correos están registrados (DEF-05).
    """
    hace_15_minutos = timezone.now() - timedelta(minutes=MINUTOS_BLOQUEO)
    fallidos = RegistroAuditoria.objects.filter(
        accion="LOGIN_FALLIDO", correo=correo, fecha__gte=hace_15_minutos
    ).count()
    return fallidos >= MAX_INTENTOS
