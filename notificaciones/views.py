from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from .models import Notificacion


@login_required
def lista(request):
    """Muestra los avisos de la persona y los marca como leídos."""
    avisos = Notificacion.objects.filter(usuario=request.user)[:50]
    pagina = render(request, "notificaciones/lista.html", {"avisos": avisos})
    Notificacion.objects.filter(usuario=request.user, leida=False).update(leida=True)
    return pagina
