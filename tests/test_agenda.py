"""Pruebas de las reglas de la agenda (RF-02 a RF-08)."""
from datetime import timedelta
from io import StringIO

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from agenda.models import BloqueHorario, Cita, ErrorCita

from .datos import crear_bloque, crear_especialista, crear_paciente


class SolicitarCitaTest(TestCase):
    def setUp(self):
        self.paciente = crear_paciente()
        self.especialista = crear_especialista()
        self.bloque = crear_bloque(self.especialista)

    def test_solicitar_cita_ocupa_el_bloque(self):
        cita = Cita.solicitar(self.paciente, self.bloque.id, "Evaluación")
        self.bloque.refresh_from_db()
        self.assertEqual(cita.estado, Cita.SOLICITADA)
        self.assertFalse(self.bloque.disponible)

    def test_no_permite_doble_reserva(self):
        """RF-03 / CA-01: el segundo paciente debe elegir otro horario."""
        Cita.solicitar(self.paciente, self.bloque.id)
        otro = crear_paciente("otro@correo.cl")
        with self.assertRaises(ErrorCita):
            Cita.solicitar(otro, self.bloque.id)
        self.assertEqual(Cita.objects.count(), 1)

    def test_no_permite_bloque_pasado(self):
        pasado = crear_bloque(self.especialista, horas_desde_ahora=-2)
        with self.assertRaises(ErrorCita):
            Cita.solicitar(self.paciente, pasado.id)

    def test_solicitar_desde_la_pagina(self):
        self.client.force_login(self.paciente)
        url = reverse("agenda:horarios", args=[self.especialista.id])
        respuesta = self.client.post(url, {"bloque_id": self.bloque.id, "motivo": ""})
        self.assertRedirects(respuesta, reverse("agenda:mis_citas"))
        self.assertEqual(Cita.objects.count(), 1)


class ResponderCitaTest(TestCase):
    def setUp(self):
        self.paciente = crear_paciente()
        self.especialista = crear_especialista()
        self.bloque = crear_bloque(self.especialista)
        self.cita = Cita.solicitar(self.paciente, self.bloque.id)
        self.client.force_login(self.especialista)

    def test_confirmar(self):
        self.client.post(reverse("agenda:confirmar", args=[self.cita.id]))
        self.cita.refresh_from_db()
        self.assertEqual(self.cita.estado, Cita.CONFIRMADA)

    def test_rechazar_libera_el_bloque(self):
        self.client.post(reverse("agenda:rechazar", args=[self.cita.id]), {"motivo": "Sin cupo"})
        self.cita.refresh_from_db()
        self.bloque.refresh_from_db()
        self.assertEqual(self.cita.estado, Cita.RECHAZADA)
        self.assertTrue(self.bloque.disponible)

    def test_rechazar_sin_motivo_no_cambia(self):
        self.client.post(reverse("agenda:rechazar", args=[self.cita.id]), {"motivo": ""})
        self.cita.refresh_from_db()
        self.assertEqual(self.cita.estado, Cita.SOLICITADA)

    def test_no_se_confirma_una_cita_cancelada(self):
        self.cita.cancelar(self.especialista, "Licencia")
        with self.assertRaises(ErrorCita):
            self.cita.confirmar(self.especialista)


class CancelarCitaTest(TestCase):
    def setUp(self):
        self.paciente = crear_paciente()
        self.especialista = crear_especialista()

    def test_paciente_cancela_con_mas_de_24_horas(self):
        cita = Cita.solicitar(self.paciente, crear_bloque(self.especialista, 48).id)
        self.client.force_login(self.paciente)
        self.client.post(reverse("agenda:cancelar", args=[cita.id]), {"motivo": "Viaje"})
        cita.refresh_from_db()
        self.assertEqual(cita.estado, Cita.CANCELADA)
        self.assertTrue(cita.bloque.disponible)

    def test_paciente_no_cancela_con_menos_de_24_horas(self):
        cita = Cita.solicitar(self.paciente, crear_bloque(self.especialista, 10).id)
        self.client.force_login(self.paciente)
        respuesta = self.client.post(
            reverse("agenda:cancelar", args=[cita.id]), {"motivo": "Viaje"}, follow=True
        )
        self.assertContains(respuesta, "24 horas")
        cita.refresh_from_db()
        self.assertEqual(cita.estado, Cita.SOLICITADA)

    def test_especialista_cancela_con_menos_de_24_horas(self):
        cita = Cita.solicitar(self.paciente, crear_bloque(self.especialista, 10).id)
        self.client.force_login(self.especialista)
        self.client.post(reverse("agenda:cancelar", args=[cita.id]), {"motivo": "Emergencia"})
        cita.refresh_from_db()
        self.assertEqual(cita.estado, Cita.CANCELADA)


class ReagendarTest(TestCase):
    def setUp(self):
        self.especialista = crear_especialista()
        self.bloque1 = crear_bloque(self.especialista, 48)
        self.bloque2 = crear_bloque(self.especialista, 72)
        self.cita = Cita.solicitar(crear_paciente(), self.bloque1.id)
        self.client.force_login(self.especialista)

    def test_reagendar_mueve_la_cita_y_libera_el_bloque_anterior(self):
        url = reverse("agenda:reagendar", args=[self.cita.id])
        self.client.post(url, {"bloque_id": self.bloque2.id})
        self.cita.refresh_from_db()
        self.bloque1.refresh_from_db()
        self.assertEqual(self.cita.bloque, self.bloque2)
        self.assertTrue(self.bloque1.disponible)

    def test_no_reagenda_a_bloque_ocupado(self):
        Cita.solicitar(crear_paciente("otro@correo.cl"), self.bloque2.id)
        with self.assertRaises(ErrorCita):
            self.cita.reagendar(self.especialista, self.bloque2.id)

    def test_bloque_invalido_no_produce_error_500(self):
        """Prueba de regresión del defecto DEF-01."""
        url = reverse("agenda:reagendar", args=[self.cita.id])
        respuesta = self.client.post(url, {"bloque_id": "abc"}, follow=True)
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "Elige un horario válido")

    def test_pagina_reagendar_muestra_bloques_libres(self):
        respuesta = self.client.get(reverse("agenda:reagendar", args=[self.cita.id]))
        self.assertContains(respuesta, "Mover la cita")


class DisponibilidadTest(TestCase):
    def setUp(self):
        self.especialista = crear_especialista()
        self.client.force_login(self.especialista)
        self.url = reverse("agenda:disponibilidad")

    def publicar(self, inicio):
        return self.client.post(self.url, {"inicio": inicio.strftime("%Y-%m-%dT%H:%M")})

    def test_publicar_bloque_de_45_minutos(self):
        inicio = timezone.localtime() + timedelta(days=2)
        self.publicar(inicio)
        bloque = BloqueHorario.objects.get()
        self.assertEqual(bloque.fin - bloque.inicio, timedelta(minutes=45))

    def test_no_publica_en_el_pasado(self):
        respuesta = self.publicar(timezone.localtime() - timedelta(days=1))
        self.assertContains(respuesta, "pasado")
        self.assertFalse(BloqueHorario.objects.exists())

    def test_no_publica_bloques_que_se_cruzan(self):
        inicio = timezone.localtime() + timedelta(days=2)
        self.publicar(inicio)
        respuesta = self.publicar(inicio + timedelta(minutes=20))
        self.assertContains(respuesta, "se cruza")
        self.assertEqual(BloqueHorario.objects.count(), 1)

    def test_eliminar_bloque_libre(self):
        bloque = crear_bloque(self.especialista)
        self.client.post(reverse("agenda:eliminar_bloque", args=[bloque.id]))
        self.assertFalse(BloqueHorario.objects.exists())

    def test_no_elimina_bloque_con_cita(self):
        bloque = crear_bloque(self.especialista)
        Cita.solicitar(crear_paciente(), bloque.id)
        self.client.post(reverse("agenda:eliminar_bloque", args=[bloque.id]))
        self.assertTrue(BloqueHorario.objects.exists())


class PantallasTest(TestCase):
    """Cada rol ve sus pantallas principales."""

    def test_paciente_ve_sus_pantallas(self):
        especialista = crear_especialista()
        crear_bloque(especialista)
        self.client.force_login(crear_paciente())
        for url in [
            reverse("agenda:mis_citas"),
            reverse("agenda:especialistas"),
            reverse("agenda:horarios", args=[especialista.id]),
            reverse("notificaciones:lista"),
            reverse("usuarios:mi_cuenta"),
        ]:
            self.assertEqual(self.client.get(url).status_code, 200, url)

    def test_especialista_ve_sus_pantallas(self):
        self.client.force_login(crear_especialista())
        for url in [reverse("agenda:mi_agenda"), reverse("agenda:disponibilidad")]:
            self.assertEqual(self.client.get(url).status_code, 200, url)

    def test_inicio_redirige_segun_rol(self):
        self.client.force_login(crear_especialista())
        self.assertRedirects(self.client.get(reverse("inicio")), reverse("agenda:mi_agenda"))

    def test_salud(self):
        self.assertJSONEqual(self.client.get(reverse("salud")).content, {"estado": "ok"})


class DatosDeEjemploTest(TestCase):
    def test_cargar_demo_crea_usuarios_y_bloques(self):
        from django.core.management import call_command

        call_command("cargar_demo", stdout=StringIO())
        self.assertEqual(BloqueHorario.objects.count(), 20)
