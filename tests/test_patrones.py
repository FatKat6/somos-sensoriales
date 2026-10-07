"""Pruebas de los patrones de diseño: Singleton, Factory y Observer."""
from django.core import mail
from django.test import TestCase

from agenda.models import CentroTerapeutico, Cita
from notificaciones.avisos import AvisoApp, AvisoCorreo, crear_aviso
from notificaciones.models import Notificacion
from usuarios.models import RegistroAuditoria

from .datos import crear_bloque, crear_especialista, crear_paciente


class SingletonTest(TestCase):
    def test_siempre_existe_un_solo_centro(self):
        primero = CentroTerapeutico.obtener()
        CentroTerapeutico(nombre="Otro centro").save()  # intenta crear otro
        self.assertEqual(CentroTerapeutico.objects.count(), 1)
        self.assertEqual(CentroTerapeutico.obtener().pk, primero.pk)


class FactoryTest(TestCase):
    def test_crea_el_aviso_segun_el_canal(self):
        self.assertIsInstance(crear_aviso("app"), AvisoApp)
        self.assertIsInstance(crear_aviso("correo"), AvisoCorreo)

    def test_canal_desconocido(self):
        with self.assertRaises(ValueError):
            crear_aviso("paloma")


class ObserverTest(TestCase):
    def setUp(self):
        self.paciente = crear_paciente()
        self.especialista = crear_especialista()
        self.cita = Cita.solicitar(self.paciente, crear_bloque(self.especialista).id, "Ansiedad")

    def test_al_solicitar_se_avisa_al_especialista(self):
        self.assertTrue(Notificacion.objects.filter(usuario=self.especialista).exists())
        self.assertEqual(mail.outbox[0].to, [self.especialista.email])

    def test_al_confirmar_se_avisa_al_paciente(self):
        self.cita.confirmar(self.especialista)
        aviso = Notificacion.objects.filter(usuario=self.paciente).first()
        self.assertIn("confirmada", aviso.mensaje)

    def test_el_aviso_no_incluye_el_motivo_de_consulta(self):
        """RNF-05: los correos no deben contener el motivo de consulta."""
        self.assertNotIn("Ansiedad", mail.outbox[0].body)

    def test_cada_cambio_queda_en_la_auditoria(self):
        self.cita.confirmar(self.especialista)
        acciones = list(RegistroAuditoria.objects.values_list("accion", flat=True))
        self.assertIn("CITA_SOLICITADA", acciones)
        self.assertIn("CITA_CONFIRMADA", acciones)
