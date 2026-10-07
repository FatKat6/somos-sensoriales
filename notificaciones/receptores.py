"""
Patrón Observer (observador 1 de 2): AVISOS.

Escucha la señal cita_cambiada y avisa a la OTRA persona involucrada:
si el paciente hizo el cambio, se avisa al especialista, y al revés.
El texto nunca incluye el motivo de consulta (RNF-05, privacidad).
"""
from django.dispatch import receiver
from django.utils import timezone

from agenda.senales import cita_cambiada

from .avisos import CANALES, crear_aviso


@receiver(cita_cambiada)
def avisar_cambio_de_cita(sender, cita, accion, actor, **kwargs):
    especialista = cita.bloque.especialista
    if actor == cita.paciente:
        destinatario = especialista
    else:
        destinatario = cita.paciente

    fecha = timezone.localtime(cita.bloque.inicio).strftime("%d-%m-%Y a las %H:%M")
    texto = f"La cita del {fecha} con {especialista} fue {accion}."

    # Se envía por todos los canales registrados en la fábrica (app y correo)
    for canal in CANALES:
        crear_aviso(canal).enviar(destinatario, texto)
