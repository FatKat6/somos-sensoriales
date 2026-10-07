"""
Prueba simple de rendimiento (RNF-01): las pantallas principales deben
responder en menos de 1 segundo, incluso con varias citas cargadas.
"""
import time

from django.test import TestCase
from django.urls import reverse

from agenda.models import Cita

from .datos import crear_bloque, crear_especialista, crear_paciente


class TiempoDeRespuestaTest(TestCase):
    def test_mi_agenda_responde_en_menos_de_1_segundo(self):
        especialista = crear_especialista()
        for numero in range(30):
            paciente = crear_paciente(f"paciente{numero}@correo.cl")
            Cita.solicitar(paciente, crear_bloque(especialista, 48 + numero).id)

        self.client.force_login(especialista)
        inicio = time.perf_counter()
        respuesta = self.client.get(reverse("agenda:mi_agenda"))
        segundos = time.perf_counter() - inicio

        self.assertEqual(respuesta.status_code, 200)
        self.assertLess(segundos, 1.0)
