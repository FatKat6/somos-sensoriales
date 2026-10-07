"""Funciones para crear datos de prueba rápidamente."""
from datetime import timedelta

from django.utils import timezone

from agenda.models import BloqueHorario
from usuarios.models import Usuario

CLAVE = "ClaveSegura2026!"


def crear_usuario(email, rol, **datos):
    return Usuario.objects.create_user(
        username=email, email=email, password=CLAVE, rol=rol,
        first_name=datos.pop("first_name", "Nombre"), last_name="Prueba", **datos
    )


def crear_paciente(email="paciente@correo.cl"):
    return crear_usuario(email, Usuario.PACIENTE, rut="11111111-1")


def crear_especialista(email="especialista@centro.cl"):
    return crear_usuario(email, Usuario.ESPECIALISTA, especialidad="Psicología")


def crear_bloque(especialista, horas_desde_ahora=48):
    inicio = timezone.now() + timedelta(hours=horas_desde_ahora)
    return BloqueHorario.objects.create(
        especialista=especialista, inicio=inicio, fin=inicio + timedelta(minutes=45)
    )
