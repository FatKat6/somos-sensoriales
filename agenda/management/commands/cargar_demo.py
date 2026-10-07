"""
Carga datos de ejemplo para probar y presentar el prototipo.
Uso:  python manage.py cargar_demo
"""
import os
from datetime import datetime, timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from agenda.models import BloqueHorario, CentroTerapeutico
from usuarios.models import Usuario


class Command(BaseCommand):
    help = "Crea usuarios y horarios de ejemplo"

    def crear_usuario(self, email, clave, **datos):
        usuario, creado = Usuario.objects.get_or_create(
            email=email, defaults={"username": email, **datos}
        )
        if creado:
            usuario.set_password(clave)
            usuario.save()
        return usuario

    def handle(self, *args, **options):
        # La clave de demostración se lee de una variable de entorno
        clave = os.environ.get("DEMO_PASSWORD", "Sensorial2026!")
        CentroTerapeutico.obtener()

        self.crear_usuario(
            "admin@somossensoriales.cl", clave, first_name="Admin",
            rol=Usuario.ADMINISTRADOR, is_staff=True, is_superuser=True,
        )
        sofia = self.crear_usuario(
            "sofia.ramirez@somossensoriales.cl", clave, first_name="Sofía",
            last_name="Ramírez", rol=Usuario.ESPECIALISTA, especialidad="Terapia ocupacional",
        )
        self.crear_usuario(
            "ana.garcia@correo.cl", clave, first_name="Ana", last_name="García",
            rol=Usuario.PACIENTE, rut="11111111-1", fecha_consentimiento=timezone.now(),
        )

        # Bloques de 45 minutos para los próximos 5 días
        manana = timezone.localdate() + timedelta(days=1)
        for dia in range(5):
            fecha = manana + timedelta(days=dia)
            for hora in [9, 10, 11, 15]:
                inicio = timezone.make_aware(datetime(fecha.year, fecha.month, fecha.day, hora))
                BloqueHorario.objects.get_or_create(
                    especialista=sofia,
                    inicio=inicio,
                    defaults={"fin": inicio + timedelta(minutes=45)},
                )
        self.stdout.write(self.style.SUCCESS("Datos de ejemplo cargados."))
