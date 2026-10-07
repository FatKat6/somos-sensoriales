"""Rutas principales del sitio. Cada app tiene además su propio urls.py."""
from django.contrib import admin
from django.urls import include, path

from agenda import views as agenda_views

urlpatterns = [
    path("", agenda_views.inicio, name="inicio"),
    path("salud/", agenda_views.salud, name="salud"),
    path("admin/", admin.site.urls),
    path("cuentas/", include("usuarios.urls")),
    path("agenda/", include("agenda.urls")),
    path("avisos/", include("notificaciones.urls")),
]

# Vista propia para el error 403: además de mostrar la página,
# deja registrado el intento de acceso en la auditoría.
handler403 = "usuarios.views.acceso_denegado"
