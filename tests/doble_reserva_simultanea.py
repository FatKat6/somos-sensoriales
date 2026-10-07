"""
Prueba de doble reserva con solicitudes simultáneas (RF-03 / CA-01).

1) Registra 10 pacientes nuevos.
2) Los 10 piden EL MISMO horario exactamente al mismo tiempo (10 hilos).
3) Revisa cuántos lo consiguieron: debe ser solo 1.

Uso:  python tests/doble_reserva_simultanea.py https://127.0.0.1:8444
"""
import random
import re
import sys
import threading

import requests
import urllib3

urllib3.disable_warnings()
BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"
PACIENTES = 10


def rut_al_azar():
    """Genera un RUT válido (calcula el dígito verificador con módulo 11)."""
    numero = str(random.randint(10_000_000, 25_000_000))
    suma, multiplicador = 0, 2
    for digito in reversed(numero):
        suma += int(digito) * multiplicador
        multiplicador = 2 if multiplicador == 7 else multiplicador + 1
    dv = {11: "0", 10: "K"}.get(11 - suma % 11, str(11 - suma % 11))
    return f"{numero}-{dv}"


def token(sesion, url):
    pagina = sesion.get(BASE + url)
    return re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', pagina.text).group(1), pagina.text


def registrar_paciente(numero):
    sesion = requests.Session()
    sesion.trust_env = False
    sesion.verify = False
    csrf, _ = token(sesion, "/cuentas/registro/")
    clave = "ClaveDePrueba#2026"
    sesion.post(BASE + "/cuentas/registro/", headers={"Referer": BASE + "/cuentas/registro/"}, data={
        "csrfmiddlewaretoken": csrf, "first_name": "Paciente", "last_name": f"Prueba {numero}",
        "email": f"simultaneo{numero}.{random.randint(1000, 9999)}@correo.cl", "telefono": "",
        "rut": rut_al_azar(), "nombre_tutor": "", "password1": clave, "password2": clave,
        "acepta_datos": "on",
    })
    return sesion


sesiones = [registrar_paciente(n) for n in range(PACIENTES)]

# Buscamos el primer horario libre del primer especialista
_, lista = token(sesiones[0], "/agenda/especialistas/")
url_horarios = re.search(r'href="(/agenda/especialistas/\d+/)"', lista).group(1)
csrf, pagina = token(sesiones[0], url_horarios)
bloque_id = re.search(r'name="bloque_id" value="(\d+)"', pagina).group(1)
print(f"Los {PACIENTES} pacientes pedirán el bloque {bloque_id} al mismo tiempo...")

resultados = []
partida = threading.Barrier(PACIENTES)  # todos esperan aquí y parten juntos


def pedir_hora(sesion):
    csrf, _ = token(sesion, url_horarios)
    partida.wait()
    respuesta = sesion.post(BASE + url_horarios, data={"csrfmiddlewaretoken": csrf, "bloque_id": bloque_id, "motivo": ""},
                            headers={"Referer": BASE + url_horarios})
    resultados.append("Solicitud enviada" in respuesta.text)


hilos = [threading.Thread(target=pedir_hora, args=(s,)) for s in sesiones]
for hilo in hilos:
    hilo.start()
for hilo in hilos:
    hilo.join()

exitos = resultados.count(True)
print(f"Solicitudes aceptadas: {exitos}  |  rechazadas con mensaje: {resultados.count(False)}")
print("RF-03:", "CUMPLE (una sola cita)" if exitos == 1 else "NO CUMPLE")
