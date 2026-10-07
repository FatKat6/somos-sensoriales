"""Pruebas de registro, inicio de sesión y eliminación de datos (RF-01, RF-09, RF-13)."""
from django.test import TestCase
from django.urls import reverse

from agenda.models import Cita
from usuarios.forms import rut_valido
from usuarios.models import RegistroAuditoria, Usuario

from .datos import CLAVE, crear_bloque, crear_especialista, crear_paciente

DATOS_REGISTRO = {
    "first_name": "Ana",
    "last_name": "García",
    "email": "Ana@Correo.cl",
    "telefono": "912345678",
    "rut": "11.111.111-1",
    "nombre_tutor": "",
    "password1": CLAVE,
    "password2": CLAVE,
    "acepta_datos": "on",
}


class RutTest(TestCase):
    def test_rut_correcto(self):
        self.assertTrue(rut_valido("11111111-1"))
        self.assertTrue(rut_valido("12345678-5"))

    def test_rut_con_digito_k(self):
        self.assertTrue(rut_valido("10000013-K"))

    def test_rut_incorrecto(self):
        self.assertFalse(rut_valido("11111111-2"))
        self.assertFalse(rut_valido("abc"))


class RegistroTest(TestCase):
    def test_registro_correcto_guarda_consentimiento(self):
        respuesta = self.client.post(reverse("usuarios:registro"), DATOS_REGISTRO)
        self.assertRedirects(respuesta, reverse("inicio"), fetch_redirect_response=False)
        usuario = Usuario.objects.get(email="ana@correo.cl")
        self.assertEqual(usuario.rol, Usuario.PACIENTE)
        self.assertEqual(usuario.rut, "11111111-1")
        self.assertIsNotNone(usuario.fecha_consentimiento)

    def test_sin_aceptar_datos_no_crea_cuenta(self):
        datos = dict(DATOS_REGISTRO, acepta_datos="")
        self.client.post(reverse("usuarios:registro"), datos)
        self.assertFalse(Usuario.objects.exists())

    def test_rut_invalido_no_crea_cuenta(self):
        datos = dict(DATOS_REGISTRO, rut="11111111-2")
        respuesta = self.client.post(reverse("usuarios:registro"), datos)
        self.assertContains(respuesta, "RUT inválido")
        self.assertFalse(Usuario.objects.exists())

    def test_contrasena_corta_no_crea_cuenta(self):
        datos = dict(DATOS_REGISTRO, password1="abc12345", password2="abc12345")
        self.client.post(reverse("usuarios:registro"), datos)
        self.assertFalse(Usuario.objects.exists())

    def test_contrasena_comun_o_solo_numeros_no_crea_cuenta(self):
        for clave in ["password123", "1234567890"]:
            datos = dict(DATOS_REGISTRO, password1=clave, password2=clave)
            self.client.post(reverse("usuarios:registro"), datos)
        self.assertFalse(Usuario.objects.exists())

    def test_correo_repetido(self):
        crear_paciente("ana@correo.cl")
        respuesta = self.client.post(reverse("usuarios:registro"), DATOS_REGISTRO)
        self.assertContains(respuesta, "Ya existe una cuenta con ese correo")


class LoginTest(TestCase):
    def setUp(self):
        self.paciente = crear_paciente()
        self.url = reverse("usuarios:login")

    def entrar(self, clave):
        return self.client.post(self.url, {"email": "paciente@correo.cl", "password": clave})

    def test_login_correcto(self):
        respuesta = self.entrar(CLAVE)
        self.assertRedirects(respuesta, reverse("inicio"), fetch_redirect_response=False)
        self.assertTrue(RegistroAuditoria.objects.filter(accion="LOGIN_OK").exists())

    def test_mensaje_generico_si_falla(self):
        respuesta = self.entrar("otra-clave")
        self.assertContains(respuesta, "Correo o contraseña incorrectos.")
        respuesta = self.client.post(self.url, {"email": "noexiste@correo.cl", "password": "x"})
        self.assertContains(respuesta, "Correo o contraseña incorrectos.")

    def test_bloqueo_tras_5_intentos(self):
        for _ in range(5):
            self.entrar("otra-clave")
        # Aunque ahora ponga la clave correcta, la cuenta está bloqueada
        respuesta = self.entrar(CLAVE)
        self.assertContains(respuesta, "Demasiados intentos fallidos")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_bloqueo_no_revela_si_el_correo_existe(self):
        """DEF-05: un correo que no existe se bloquea igual que uno real."""
        for _ in range(5):
            self.client.post(self.url, {"email": "noexiste@correo.cl", "password": "x"})
        respuesta = self.client.post(self.url, {"email": "noexiste@correo.cl", "password": "x"})
        self.assertContains(respuesta, "Demasiados intentos fallidos")

    def test_cerrar_sesion_solo_por_post(self):
        self.client.force_login(self.paciente)
        self.assertEqual(self.client.get(reverse("usuarios:logout")).status_code, 405)

    def test_logout(self):
        self.client.force_login(self.paciente)
        self.client.post(reverse("usuarios:logout"))
        self.assertNotIn("_auth_user_id", self.client.session)


class EliminarDatosTest(TestCase):
    def test_eliminar_datos_cancela_citas_y_borra_datos(self):
        paciente = crear_paciente()
        bloque = crear_bloque(crear_especialista())
        cita = Cita.solicitar(paciente, bloque.id, "Motivo privado")
        self.client.force_login(paciente)

        self.client.post(reverse("usuarios:eliminar_cuenta"), {"confirmacion": "ELIMINAR"})

        paciente.refresh_from_db()
        cita.refresh_from_db()
        self.assertEqual(paciente.rut, "")
        self.assertFalse(paciente.is_active)
        self.assertNotIn("paciente@correo.cl", paciente.email)
        self.assertEqual(cita.estado, Cita.CANCELADA)
        self.assertEqual(cita.motivo_consulta, "")

    def test_sin_confirmacion_no_elimina(self):
        paciente = crear_paciente()
        self.client.force_login(paciente)
        self.client.post(reverse("usuarios:eliminar_cuenta"), {"confirmacion": "no"})
        paciente.refresh_from_db()
        self.assertTrue(paciente.is_active)
