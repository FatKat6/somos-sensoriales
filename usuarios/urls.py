from django.urls import path

from . import views

app_name = "usuarios"

urlpatterns = [
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("registro/", views.registro_view, name="registro"),
    path("mi-cuenta/", views.mi_cuenta, name="mi_cuenta"),
    path("mi-cuenta/eliminar/", views.eliminar_cuenta, name="eliminar_cuenta"),
]
