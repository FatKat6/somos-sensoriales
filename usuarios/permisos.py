"""Control de acceso por rol (OWASP A01: Broken Access Control)."""
from django.core.exceptions import PermissionDenied


def verificar_rol(usuario, rol):
    """
    Si el usuario no tiene el rol indicado, se lanza PermissionDenied y Django
    responde con error 403 (acceso denegado). Se llama al inicio de cada vista.
    """
    if usuario.rol != rol:
        raise PermissionDenied
