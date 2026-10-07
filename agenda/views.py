"""
Vistas (controladores) de la agenda.

Cada vista: 1) revisa que la persona tenga sesión y el rol correcto,
2) busca los datos SOLO entre los que le pertenecen (evita que alguien vea
citas ajenas cambiando el número en la URL), 3) llama a la regla de negocio
del modelo y 4) muestra la plantilla con un mensaje.
"""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from usuarios.models import Usuario
from usuarios.permisos import verificar_rol

from .forms import BloqueForm, MotivoForm, SolicitudForm
from .models import BloqueHorario, Cita, ErrorCita


@login_required
def inicio(request):
    """Envía a cada persona a su pantalla principal según su rol."""
    if request.user.rol == Usuario.ESPECIALISTA:
        return redirect("agenda:mi_agenda")
    if request.user.rol == Usuario.ADMINISTRADOR:
        return redirect("admin:index")
    return redirect("agenda:mis_citas")


def salud(request):
    """Render (y el monitoreo del SLA) consulta esta URL para saber si el sitio funciona."""
    return JsonResponse({"estado": "ok"})


# ====================================================================
# PACIENTE
# ====================================================================
@login_required
def especialistas(request):
    verificar_rol(request.user, Usuario.PACIENTE)
    lista = Usuario.objects.filter(rol=Usuario.ESPECIALISTA, is_active=True)
    return render(request, "agenda/especialistas.html", {"especialistas": lista})


@login_required
def horarios(request, especialista_id):
    """Muestra los bloques libres de un especialista y permite pedir uno."""
    verificar_rol(request.user, Usuario.PACIENTE)
    especialista = get_object_or_404(
        Usuario, id=especialista_id, rol=Usuario.ESPECIALISTA, is_active=True
    )

    if request.method == "POST":
        form = SolicitudForm(request.POST)
        if form.is_valid():
            try:
                Cita.solicitar(
                    request.user, form.cleaned_data["bloque_id"], form.cleaned_data["motivo"]
                )
                messages.success(request, "Solicitud enviada. Te avisaremos cuando la confirmen.")
                return redirect("agenda:mis_citas")
            except ErrorCita as error:
                messages.error(request, str(error))

    bloques = BloqueHorario.objects.filter(
        especialista=especialista, disponible=True, inicio__gt=timezone.now()
    )
    return render(
        request,
        "agenda/horarios.html",
        {"especialista": especialista, "bloques": bloques, "form": SolicitudForm()},
    )


@login_required
def mis_citas(request):
    """RF-10: el paciente ve solo sus citas."""
    verificar_rol(request.user, Usuario.PACIENTE)
    citas = Cita.objects.filter(paciente=request.user).order_by("-bloque__inicio")
    return render(request, "agenda/mis_citas.html", {"citas": citas})


# ====================================================================
# ESPECIALISTA
# ====================================================================
@login_required
def mi_agenda(request):
    """RF-10: el especialista ve solo las citas de sus bloques."""
    verificar_rol(request.user, Usuario.ESPECIALISTA)
    hoy = timezone.localtime().replace(hour=0, minute=0, second=0, microsecond=0)
    citas = Cita.objects.filter(
        bloque__especialista=request.user, bloque__inicio__gte=hoy
    ).order_by("bloque__inicio")
    pendientes = citas.filter(estado=Cita.SOLICITADA).count()
    return render(request, "agenda/mi_agenda.html", {"citas": citas, "pendientes": pendientes})


@login_required
def disponibilidad(request):
    """RF-04: publicar bloques y ver los próximos."""
    verificar_rol(request.user, Usuario.ESPECIALISTA)
    form = BloqueForm(request.POST or None)
    form.instance.especialista = request.user
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Bloque publicado.")
        return redirect("agenda:disponibilidad")

    bloques = BloqueHorario.objects.filter(
        especialista=request.user, inicio__gte=timezone.now()
    )
    return render(request, "agenda/disponibilidad.html", {"form": form, "bloques": bloques})


@require_POST
@login_required
def eliminar_bloque(request, bloque_id):
    verificar_rol(request.user, Usuario.ESPECIALISTA)
    bloque = get_object_or_404(BloqueHorario, id=bloque_id, especialista=request.user)
    if bloque.citas.exists():
        messages.error(request, "No puedes eliminar un bloque que tiene citas.")
    else:
        bloque.delete()
        messages.success(request, "Bloque eliminado.")
    return redirect("agenda:disponibilidad")


@require_POST
@login_required
def confirmar(request, cita_id):
    verificar_rol(request.user, Usuario.ESPECIALISTA)
    cita = get_object_or_404(Cita, id=cita_id, bloque__especialista=request.user)
    try:
        cita.confirmar(request.user)
        messages.success(request, "Cita confirmada.")
    except ErrorCita as error:
        messages.error(request, str(error))
    return redirect("agenda:mi_agenda")


@require_POST
@login_required
def rechazar(request, cita_id):
    verificar_rol(request.user, Usuario.ESPECIALISTA)
    cita = get_object_or_404(Cita, id=cita_id, bloque__especialista=request.user)
    form = MotivoForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Debes indicar el motivo del rechazo.")
        return redirect("agenda:mi_agenda")
    try:
        cita.rechazar(request.user, form.cleaned_data["motivo"])
        messages.success(request, "Solicitud rechazada.")
    except ErrorCita as error:
        messages.error(request, str(error))
    return redirect("agenda:mi_agenda")


@login_required
def reagendar(request, cita_id):
    """RF-08: el especialista mueve la cita a otro bloque libre suyo."""
    verificar_rol(request.user, Usuario.ESPECIALISTA)
    cita = get_object_or_404(Cita, id=cita_id, bloque__especialista=request.user)
    if request.method == "POST":
        bloque_id = request.POST.get("bloque_id", "")
        # DEF-01: si llegaba un texto (ej. "abc") el sistema mostraba error 500.
        # Ahora revisamos que sea un número antes de usarlo.
        if not bloque_id.isdigit():
            messages.error(request, "Elige un horario válido.")
            return redirect("agenda:reagendar", cita_id=cita.id)
        try:
            cita.reagendar(request.user, int(bloque_id))
            messages.success(request, "Cita reagendada. Se avisó al paciente.")
            return redirect("agenda:mi_agenda")
        except ErrorCita as error:
            messages.error(request, str(error))

    libres = BloqueHorario.objects.filter(
        especialista=request.user, disponible=True, inicio__gt=timezone.now()
    )
    return render(request, "agenda/reagendar.html", {"cita": cita, "bloques": libres})


# ====================================================================
# PACIENTE O ESPECIALISTA
# ====================================================================
@require_POST
@login_required
def cancelar(request, cita_id):
    """RF-06 (paciente, con 24 h) y RF-07 (especialista, siempre)."""
    if request.user.rol == Usuario.PACIENTE:
        cita = get_object_or_404(Cita, id=cita_id, paciente=request.user)
        volver_a = "agenda:mis_citas"
    else:
        verificar_rol(request.user, Usuario.ESPECIALISTA)
        cita = get_object_or_404(Cita, id=cita_id, bloque__especialista=request.user)
        volver_a = "agenda:mi_agenda"

    form = MotivoForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Debes indicar el motivo de la cancelación.")
        return redirect(volver_a)
    try:
        cita.cancelar(request.user, form.cleaned_data["motivo"])
        messages.success(request, "Cita cancelada. El horario quedó libre.")
    except ErrorCita as error:
        messages.error(request, str(error))
    return redirect(volver_a)
