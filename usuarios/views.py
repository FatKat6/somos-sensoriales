from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from agenda.models import Cita

from .auditoria import demasiados_intentos, registrar
from .forms import LoginForm, RegistroForm
from .models import Usuario
from .permisos import verificar_rol


def login_view(request):
    """Inicio de sesión con correo y contraseña (RF-01)."""
    if request.user.is_authenticated:
        return redirect("inicio")

    form = LoginForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        email = form.cleaned_data["email"].lower()
        password = form.cleaned_data["password"]

        # 1) ¿Hubo 5 intentos fallidos con este correo en los últimos 15 minutos?
        if demasiados_intentos(email):
            registrar("LOGIN_BLOQUEADO", request, correo=email)
            messages.error(request, "Demasiados intentos fallidos. Intenta en 15 minutos.")
            return render(request, "usuarios/login.html", {"form": form})

        # 2) Django revisa la contraseña (compara el hash, no el texto)
        usuario = None
        cuenta = Usuario.objects.filter(email=email).first()
        if cuenta:
            usuario = authenticate(request, username=cuenta.username, password=password)

        if usuario is None:
            registrar("LOGIN_FALLIDO", request, correo=email)
            # Mismo mensaje exista o no el correo, para no dar pistas (OWASP A07)
            messages.error(request, "Correo o contraseña incorrectos.")
        else:
            login(request, usuario)
            registrar("LOGIN_OK", request, usuario=usuario)
            return redirect("inicio")

    return render(request, "usuarios/login.html", {"form": form})


@require_POST
def logout_view(request):
    if request.user.is_authenticated:
        registrar("LOGOUT", request)
    logout(request)
    return redirect("usuarios:login")


def registro_view(request):
    """Registro de pacientes con aceptación del uso de datos (RF-09)."""
    form = RegistroForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        usuario = form.save(commit=False)
        usuario.username = usuario.email  # usamos el correo como nombre de usuario
        usuario.rol = Usuario.PACIENTE
        usuario.fecha_consentimiento = timezone.now()
        usuario.save()
        registrar("CUENTA_CREADA", request, usuario=usuario)
        login(request, usuario)
        messages.success(request, "Cuenta creada. Ya puedes pedir horas.")
        return redirect("inicio")
    return render(request, "usuarios/registro.html", {"form": form})


@login_required
def mi_cuenta(request):
    return render(request, "usuarios/mi_cuenta.html")


@require_POST
@login_required
def eliminar_cuenta(request):
    """Elimina los datos personales del paciente (RF-13, Ley 21.719)."""
    verificar_rol(request.user, Usuario.PACIENTE)
    if request.POST.get("confirmacion") != "ELIMINAR":
        messages.error(request, "Escribe ELIMINAR para confirmar.")
        return redirect("usuarios:mi_cuenta")

    usuario = request.user
    # Primero se cancelan sus citas futuras para liberar esas horas
    citas_futuras = Cita.objects.filter(
        paciente=usuario,
        estado__in=[Cita.SOLICITADA, Cita.CONFIRMADA],
        bloque__inicio__gt=timezone.now(),
    )
    for cita in citas_futuras:
        cita.cancelar(usuario, "El paciente eliminó su cuenta", revisar_24_horas=False)

    # Las citas pasadas se conservan para la agenda del centro, pero sin el
    # motivo de consulta (dato sensible)
    Cita.objects.filter(paciente=usuario).update(motivo_consulta="")

    registrar("DATOS_ELIMINADOS", request, usuario=usuario)
    usuario.eliminar_datos_personales()
    logout(request)
    messages.success(request, "Tus datos personales fueron eliminados.")
    return redirect("usuarios:login")


def acceso_denegado(request, exception=None):
    """Página de error 403. También deja el intento en la auditoría."""
    registrar("ACCESO_DENEGADO", request, detalle=request.path)
    return render(request, "403.html", status=403)
