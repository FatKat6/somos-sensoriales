"""
Pruebas de seguridad (OWASP Top 10 e ISO 27002).
A01 control de acceso · A02 contraseñas · A03 inyección · A07 autenticación · auditoría
"""
from django.contrib import admin
from django.test import Client, TestCase
from django.urls import reverse

from agenda.models import Cita
from usuarios.models import RegistroAuditoria, Usuario

from .datos import CLAVE, crear_bloque, crear_especialista, crear_paciente


class ControlDeAccesoTest(TestCase):
    """OWASP A01: cada persona solo puede hacer lo que su rol permite."""

    def setUp(self):
        self.paciente = crear_paciente()
        self.especialista = crear_especialista()
        self.cita = Cita.solicitar(self.paciente, crear_bloque(self.especialista).id)

    def test_sin_sesion_redirige_al_login(self):
        respuesta = self.client.get(reverse("agenda:mis_citas"))
        self.assertRedirects(respuesta, reverse("usuarios:login") + "?next=/agenda/mis-citas/")

    def test_paciente_no_entra_a_la_agenda_del_especialista(self):
        self.client.force_login(self.paciente)
        respuesta = self.client.get(reverse("agenda:mi_agenda"))
        self.assertEqual(respuesta.status_code, 403)
        self.assertTrue(RegistroAuditoria.objects.filter(accion="ACCESO_DENEGADO").exists())

    def test_paciente_no_puede_confirmar(self):
        self.client.force_login(self.paciente)
        respuesta = self.client.post(reverse("agenda:confirmar", args=[self.cita.id]))
        self.assertEqual(respuesta.status_code, 403)

    def test_paciente_no_cancela_cita_ajena(self):
        """Cambiar el número de la URL no sirve para tocar citas de otra persona."""
        intruso = crear_paciente("intruso@correo.cl")
        self.client.force_login(intruso)
        respuesta = self.client.post(
            reverse("agenda:cancelar", args=[self.cita.id]), {"motivo": "x"}
        )
        self.assertEqual(respuesta.status_code, 404)
        self.cita.refresh_from_db()
        self.assertEqual(self.cita.estado, Cita.SOLICITADA)

    def test_especialista_no_confirma_cita_de_otro_especialista(self):
        self.client.force_login(crear_especialista("otra@centro.cl"))
        respuesta = self.client.post(reverse("agenda:confirmar", args=[self.cita.id]))
        self.assertEqual(respuesta.status_code, 404)

    def test_paciente_no_entra_al_panel_admin(self):
        self.client.force_login(self.paciente)
        respuesta = self.client.get("/admin/")
        self.assertNotEqual(respuesta.status_code, 200)


class ContrasenasYFormulariosTest(TestCase):
    def test_sesion_se_cierra_tras_30_minutos_sin_uso(self):
        """RNF-03 / CA-06"""
        from django.conf import settings

        self.assertEqual(settings.SESSION_COOKIE_AGE, 30 * 60)
        self.assertTrue(settings.SESSION_SAVE_EVERY_REQUEST)

    def test_contrasena_guardada_con_hash(self):
        """OWASP A02: la contraseña nunca se guarda en texto plano."""
        usuario = crear_paciente()
        self.assertTrue(usuario.password.startswith("pbkdf2_sha256$"))
        self.assertNotIn(CLAVE, usuario.password)

    def test_formularios_exigen_token_csrf(self):
        cliente = Client(enforce_csrf_checks=True)
        respuesta = cliente.post(reverse("usuarios:login"), {"email": "a@a.cl", "password": "x"})
        self.assertEqual(respuesta.status_code, 403)

    def test_texto_peligroso_se_muestra_como_texto(self):
        """OWASP A03 (inyección/XSS): Django escapa el HTML en las plantillas."""
        paciente = crear_paciente()
        especialista = crear_especialista()
        Cita.solicitar(paciente, crear_bloque(especialista).id, "<script>alert(1)</script>")
        self.client.force_login(especialista)
        respuesta = self.client.get(reverse("agenda:mi_agenda"))
        self.assertNotContains(respuesta, "<script>alert(1)</script>")
        self.assertContains(respuesta, "&lt;script&gt;")

    def test_inyeccion_sql_en_login_no_funciona(self):
        """OWASP A03: el ORM de Django usa consultas parametrizadas."""
        crear_paciente()
        respuesta = self.client.post(
            reverse("usuarios:login"), {"email": "' OR '1'='1@a.cl", "password": "' OR '1'='1"}
        )
        self.assertNotIn("_auth_user_id", self.client.session)
        self.assertEqual(respuesta.status_code, 200)


class CabecerasDeSeguridadTest(TestCase):
    """Pruebas de regresión de los hallazgos de OWASP ZAP (DEF-02 y DEF-03)."""

    def test_respuesta_incluye_content_security_policy(self):
        respuesta = self.client.get(reverse("usuarios:login"))
        self.assertIn("default-src 'self'", respuesta["Content-Security-Policy"])
        self.assertIn("frame-ancestors 'none'", respuesta["Content-Security-Policy"])

    def test_cookie_csrf_es_httponly(self):
        respuesta = self.client.get(reverse("usuarios:login"))
        self.assertTrue(respuesta.cookies["csrftoken"]["httponly"])

    def test_error_500_usa_pagina_propia(self):
        """DEF-04"""
        from django.template.loader import render_to_string

        self.assertIn("Ocurrió un error", render_to_string("500.html"))


class PrivacidadYAuditoriaTest(TestCase):
    def test_admin_no_ve_motivo_de_consulta(self):
        """RNF-05: el formulario de citas del admin no incluye el motivo."""
        from agenda.admin import CitaAdmin

        self.assertIn("motivo_consulta", CitaAdmin.exclude)

    def test_auditoria_no_se_puede_editar_ni_borrar(self):
        """RF-14 / Ley 21.459"""
        modelo_admin = admin.site._registry[RegistroAuditoria]
        self.assertFalse(modelo_admin.has_change_permission(None))
        self.assertFalse(modelo_admin.has_delete_permission(None))
        self.assertFalse(modelo_admin.has_add_permission(None))

    def test_login_fallido_queda_registrado(self):
        self.client.post(reverse("usuarios:login"), {"email": "x@correo.cl", "password": "malo"})
        registro = RegistroAuditoria.objects.get(accion="LOGIN_FALLIDO")
        self.assertEqual(registro.correo, "x@correo.cl")
        self.assertEqual(registro.ip, "127.0.0.1")

    def test_admin_puede_desactivar_cuentas(self):
        """RF-12"""
        jefe = Usuario.objects.create_superuser("admin", "admin@centro.cl", CLAVE)
        paciente = crear_paciente()
        self.client.force_login(jefe)
        respuesta = self.client.get(f"/admin/usuarios/usuario/{paciente.id}/change/")
        self.assertEqual(respuesta.status_code, 200)
