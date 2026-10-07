"""
Patrón Observer (observador 2 de 2): AUDITORÍA.

Cada vez que una cita cambia, agenda/models.py "publica" la señal
cita_cambiada. Esta función está "suscrita" a esa señal y guarda el cambio
en el registro de auditoría. La cita no sabe que existe la auditoría:
solo avisa que cambió.
"""
from django.dispatch import receiver

from agenda.senales import cita_cambiada

from .models import RegistroAuditoria


@receiver(cita_cambiada)
def auditar_cambio_de_cita(sender, cita, accion, actor, **kwargs):
    RegistroAuditoria.objects.create(
        usuario=actor,
        correo=actor.email,
        accion=f"CITA_{accion.upper()}",
        detalle=f"Cita N° {cita.id}",
    )
