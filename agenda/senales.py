"""
Patrón Observer: la señal (evento) que se "publica" cada vez que una cita cambia.

Usamos las señales (signals) que ya trae Django. Quien publica es el modelo
Cita (agenda/models.py). Quienes escuchan ("observadores") son:
    - notificaciones/receptores.py -> avisa a la otra persona
    - usuarios/receptores.py       -> guarda el cambio en la auditoría

Datos que viajan con la señal: cita, accion (texto) y actor (quién hizo el cambio).
"""
from django.dispatch import Signal

cita_cambiada = Signal()
