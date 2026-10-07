# Registro de defectos

Defectos encontrados durante las pruebas del prototipo, ordenados por la
prioridad con que se corrigieron. Cada corrección tiene una prueba automática
para que el defecto no vuelva a aparecer (prueba de regresión).

| ID | Detectado por | Severidad | Defecto | Corrección | Prueba de regresión |
|---|---|---|---|---|---|
| DEF-01 | Prueba manual con datos inválidos | Media | Al reagendar, si el campo `bloque_id` traía texto (ej. `abc`), la página respondía **error 500**. | `agenda/views.py`: se revisa que `bloque_id` sea un número antes de usarlo y se muestra "Elige un horario válido". | `ReagendarTest.test_bloque_invalido_no_produce_error_500` |
| DEF-02 | OWASP ZAP (escaneo 1) | Media | Faltaba la cabecera **Content-Security-Policy** en todas las páginas. | Librería `django-csp` con una política que solo permite archivos del propio sitio. Bootstrap se guarda dentro del proyecto (no CDN). | `CabecerasDeSeguridadTest.test_respuesta_incluye_content_security_policy` |
| DEF-03 | OWASP ZAP (escaneo 1) | Baja | La cookie `csrftoken` no tenía la marca **HttpOnly**. | `CSRF_COOKIE_HTTPONLY = True` en `config/settings.py`. | `CabecerasDeSeguridadTest.test_cookie_csrf_es_httponly` |
| DEF-04 | Revisión de los logs del servidor al reproducir DEF-01 | Baja | Con DEBUG apagado, los errores 500 **no quedaban registrados** en los logs y la página de error era la genérica en inglés. | Configuración `LOGGING` para `django.request` y plantilla `templates/500.html` en español. | `CabecerasDeSeguridadTest.test_error_500_usa_pagina_propia` |
| DEF-05 | Revisión cruzada de código | Baja | El mensaje "Demasiados intentos fallidos" solo aparecía con correos registrados, por lo que permitía adivinar qué correos tienen cuenta (enumeración de usuarios). | `usuarios/auditoria.py`: `demasiados_intentos()` cuenta los LOGIN_FALLIDO de los últimos 15 minutos por correo, exista o no la cuenta. Se quitaron los campos de bloqueo del modelo Usuario. | `LoginTest.test_bloqueo_no_revela_si_el_correo_existe` |

Estado: 5 defectos encontrados, 5 corregidos, 0 abiertos.
