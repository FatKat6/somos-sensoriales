"""
Configuración del proyecto Somos Sensoriales.

Usamos UN solo archivo de configuración. Lo que cambia entre entornos
(desarrollo, pruebas y producción) se lee desde variables de entorno:

    - En nuestro computador (desarrollo) no definimos nada: DEBUG queda activo
      y se usa SQLite.
    - En GitHub Actions (pruebas) tampoco: Django crea una base de datos
      temporal para las pruebas.
    - En Render (producción) definimos PRODUCCION=True, DJANGO_SECRET_KEY y
      DATABASE_URL (PostgreSQL). Ver render.yaml.

Así nunca escribimos claves ni contraseñas en el código (OWASP A02 / A05).
"""
import os
from pathlib import Path

import dj_database_url
from csp.constants import NONE, SELF
from django.core.management.utils import get_random_secret_key

BASE_DIR = Path(__file__).resolve().parent.parent

# --------------------------------------------------------------------------
# Entorno
# --------------------------------------------------------------------------
# Render define sola la variable RENDER=true, así que aunque olvidemos poner
# PRODUCCION=True, en Render el sistema igual queda en modo producción.
PRODUCCION = os.environ.get("PRODUCCION") == "True" or os.environ.get("RENDER") == "true"
DEBUG = not PRODUCCION

# La clave secreta firma las sesiones. En producción es obligatoria y viene
# de Render; en desarrollo se genera una al azar cada vez que se inicia.
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY") or get_random_secret_key()
if PRODUCCION and not os.environ.get("DJANGO_SECRET_KEY"):
    raise RuntimeError("Falta la variable de entorno DJANGO_SECRET_KEY")

ALLOWED_HOSTS = ["localhost", "127.0.0.1"]
if os.environ.get("RENDER_EXTERNAL_HOSTNAME"):  # Render la define sola
    ALLOWED_HOSTS.append(os.environ["RENDER_EXTERNAL_HOSTNAME"])
CSRF_TRUSTED_ORIGINS = [f"https://{host}" for host in ALLOWED_HOSTS]

# --------------------------------------------------------------------------
# Aplicaciones
# --------------------------------------------------------------------------
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "csp",  # cabecera Content-Security-Policy (DEF-02)
    # Nuestras apps
    "usuarios",
    "agenda",
    "notificaciones",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",  # sirve CSS/JS en Render
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",  # protege formularios (CSRF)
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "csp.middleware.CSPMiddleware",  # DEF-02
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# --------------------------------------------------------------------------
# Base de datos: SQLite en desarrollo, PostgreSQL en Render (DATABASE_URL)
# --------------------------------------------------------------------------
DATABASES = {
    "default": dj_database_url.config(
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
        conn_max_age=600,
    )
}

# --------------------------------------------------------------------------
# Usuarios, contraseñas y sesiones
# --------------------------------------------------------------------------
AUTH_USER_MODEL = "usuarios.Usuario"

# Contraseñas de al menos 10 caracteres, no comunes y no solo números (RNF-02)
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 10},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
# Django guarda las contraseñas con PBKDF2-SHA256 (nunca en texto plano).

LOGIN_URL = "usuarios:login"
LOGIN_REDIRECT_URL = "inicio"

# La sesión se cierra sola tras 30 minutos sin uso (RNF-03)
SESSION_COOKIE_AGE = 30 * 60
SESSION_SAVE_EVERY_REQUEST = True
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

# DEF-03 (OWASP ZAP): la cookie CSRF no tenía HttpOnly. Nuestro sitio no usa
# JavaScript que la lea, así que la marcamos para que el navegador la oculte.
CSRF_COOKIE_HTTPONLY = True

# --------------------------------------------------------------------------
# DEF-02 (OWASP ZAP): faltaba la cabecera Content-Security-Policy (CSP).
# Le dice al navegador que solo cargue CSS, JavaScript e imágenes de nuestro
# propio sitio. Si alguien logra inyectar un <script>, el navegador no lo ejecuta.
# Por eso Bootstrap está guardado dentro del proyecto y no se carga desde un CDN.
# --------------------------------------------------------------------------
CONTENT_SECURITY_POLICY = {
    "DIRECTIVES": {
        "default-src": [SELF],
        "img-src": [SELF, "data:"],  # Bootstrap usa iconos SVG en formato data:
        "object-src": [NONE],
        "base-uri": [SELF],
        "form-action": [SELF],
        "frame-ancestors": [NONE],  # nadie puede mostrar el sitio dentro de un iframe
    }
}

# --------------------------------------------------------------------------
# Idioma, zona horaria y archivos estáticos
# --------------------------------------------------------------------------
LANGUAGE_CODE = "es-cl"
TIME_ZONE = "America/Santiago"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# En el prototipo los correos se muestran en la consola (y en los logs de
# Render). Para usarlo con el centro hay que configurar un servidor SMTP.
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
DEFAULT_FROM_EMAIL = "no-responder@somossensoriales.cl"

# DEF-04: con DEBUG desactivado, los errores 500 no aparecían en el registro
# del servidor (ni en los logs de Render). Ahora se muestran en la consola.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"consola": {"class": "logging.StreamHandler"}},
    "loggers": {"django.request": {"handlers": ["consola"], "level": "ERROR"}},
}

# --------------------------------------------------------------------------
# Seguridad en producción (checklist de despliegue de Django)
# --------------------------------------------------------------------------
if PRODUCCION:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_SSL_REDIRECT = True  # todo por HTTPS
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000  # el navegador recuerda usar HTTPS por 1 año
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    STORAGES = {
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
    }
