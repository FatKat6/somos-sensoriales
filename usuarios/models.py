"""
Modelos de la app usuarios: Usuario y RegistroAuditoria.
"""
from django.contrib.auth.models import AbstractUser
from django.db import models


class Usuario(AbstractUser):
    """
    Un solo modelo para los tres roles (paciente, especialista y administrador).
    El campo "rol" indica qué puede hacer cada persona.

    Heredamos de AbstractUser para aprovechar lo que ya trae Django:
    contraseñas guardadas con hash PBKDF2, sesiones, permisos y el panel admin.
    """

    PACIENTE = "PACIENTE"
    ESPECIALISTA = "ESPECIALISTA"
    ADMINISTRADOR = "ADMINISTRADOR"
    ROLES = [
        (PACIENTE, "Paciente / Tutor"),
        (ESPECIALISTA, "Especialista"),
        (ADMINISTRADOR, "Administrador"),
    ]

    email = models.EmailField("correo electrónico", unique=True)
    rol = models.CharField(max_length=15, choices=ROLES, default=PACIENTE)
    telefono = models.CharField("teléfono", max_length=15, blank=True)

    # Datos que solo usa el paciente
    rut = models.CharField("RUT", max_length=12, blank=True)
    nombre_tutor = models.CharField("nombre del tutor", max_length=120, blank=True)
    fecha_consentimiento = models.DateTimeField(
        "fecha en que aceptó el uso de sus datos", null=True, blank=True
    )

    # Dato que solo usa el especialista
    especialidad = models.CharField(max_length=80, blank=True)

    def __str__(self):
        return self.get_full_name() or self.email

    def eliminar_datos_personales(self):
        """
        Derecho de supresión (Ley 21.719, RF-13).
        Borramos los datos que identifican a la persona, pero dejamos la fila
        para que las citas pasadas sigan existiendo en la agenda del centro.
        """
        self.first_name = "Usuario"
        self.last_name = "eliminado"
        self.username = f"eliminado-{self.id}"
        self.email = f"eliminado-{self.id}@correo.invalid"  # dominio que no existe
        self.telefono = ""
        self.rut = ""
        self.nombre_tutor = ""
        self.is_active = False
        self.set_unusable_password()
        self.save()


class RegistroAuditoria(models.Model):
    """
    Registro de accesos y cambios (RF-14, Ley 21.459 de delitos informáticos).
    Solo se agregan filas: en el panel admin nadie puede editarlas ni borrarlas.
    """

    fecha = models.DateTimeField(auto_now_add=True)
    usuario = models.ForeignKey(
        Usuario, null=True, blank=True, on_delete=models.SET_NULL
    )
    correo = models.CharField(max_length=254, blank=True)
    accion = models.CharField(max_length=40)
    detalle = models.CharField(max_length=300, blank=True)
    ip = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        ordering = ["-fecha"]
        verbose_name = "registro de auditoría"
        verbose_name_plural = "registros de auditoría"

    def __str__(self):
        return f"{self.fecha:%d-%m-%Y %H:%M} {self.accion}"
