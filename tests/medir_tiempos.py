"""
Medición de tiempos de respuesta (RNF-01 / CA-04).

Simula 10 personas usando el sistema al mismo tiempo: cada una abre las
pantallas principales 20 veces. Al final muestra el promedio y el percentil 95.

Uso:  python tests/medir_tiempos.py https://127.0.0.1:8444
(el servidor debe tener los datos de ejemplo de "cargar_demo")
"""
import os
import re
import statistics
import sys
import time
from concurrent.futures import ThreadPoolExecutor

import requests
import urllib3

urllib3.disable_warnings()  # el entorno local usa un certificado propio
BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"
USUARIOS = 10
REPETICIONES = 20


def iniciar_sesion():
    sesion = requests.Session()
    sesion.trust_env = False
    sesion.verify = False
    pagina = sesion.get(f"{BASE}/cuentas/login/")
    token = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', pagina.text).group(1)
    sesion.post(
        f"{BASE}/cuentas/login/",
        data={"email": "ana.garcia@correo.cl", "password": os.environ.get("DEMO_PASSWORD", "Sensorial2026!"), "csrfmiddlewaretoken": token},
        headers={"Referer": f"{BASE}/cuentas/login/"},
    )
    return sesion


def usuario_simulado(numero):
    sesion = iniciar_sesion()
    especialistas = sesion.get(f"{BASE}/agenda/especialistas/").text
    url_horarios = re.search(r'href="(/agenda/especialistas/\d+/)"', especialistas).group(1)
    tiempos = []
    for _ in range(REPETICIONES):
        for url in ["/agenda/mis-citas/", "/agenda/especialistas/", url_horarios, "/avisos/"]:
            inicio = time.perf_counter()
            respuesta = sesion.get(BASE + url)
            tiempos.append(((time.perf_counter() - inicio) * 1000, respuesta.status_code, url))
    return tiempos


with ThreadPoolExecutor(max_workers=USUARIOS) as grupo:
    todos = [t for lista in grupo.map(usuario_simulado, range(USUARIOS)) for t in lista]

milisegundos = sorted(t[0] for t in todos)
errores = sum(1 for t in todos if t[1] != 200)
p95 = milisegundos[int(len(milisegundos) * 0.95) - 1]
print(f"Peticiones: {len(todos)}  |  Usuarios simultáneos: {USUARIOS}  |  Errores: {errores}")
print(f"Promedio: {statistics.mean(milisegundos):.0f} ms  |  Percentil 95: {p95:.0f} ms  |  Máximo: {max(milisegundos):.0f} ms")
for url in sorted({t[2] for t in todos}):
    valores = sorted(t[0] for t in todos if t[2] == url)
    print(f"  {url:<28} promedio {statistics.mean(valores):5.0f} ms   p95 {valores[int(len(valores) * 0.95) - 1]:5.0f} ms")
print("RNF-01:", "CUMPLE" if p95 < 1000 and errores == 0 else "NO CUMPLE", "(meta: percentil 95 menor a 1.000 ms)")
