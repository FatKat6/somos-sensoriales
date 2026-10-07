"""
Modelos de la agenda: CentroTerapeutico, BloqueHorario y Cita.

Las reglas de negocio de la cita (confirmar, rechazar, cancelar, reagendar)
están como métodos del modelo Cita. Así las vistas quedan cortas y las
reglas se pueden probar fácilmente.
"""
from datetime import timedelta

from django.conf import settings
from django.db import models, transaction
from django.utils import timezone

from .senales import cita_cambiada


class ErrorCita(Exception):
    """Error de una regla de negocio. Su mensaje se muestra al usuario."""


class CentroTerapeutico(models.Model):
    """
    Patrón Singleton: el centro tiene UNA sola configuración.
    save() siempre guarda con id = 1, así nunca existe una segunda fila,
    y obtener() siempre devuelve esa misma fila.
    """

    nombre = models.CharField(max_length=100, default="Aquí Somos Sensoriales")
    horas_minimas_cancelacion = models.PositiveSmallIntegerField(default=24)
    duracion_bloque = models.PositiveSmallIntegerField("duración del bloque (minutos)", default=45)

    class Meta:
        verbose_name = "centro terapéutico"
        verbose_name_plural = "centro terapéutico"

    def __str__(self):
        return self.nombre

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def obtener(cls):
        centro, creado = cls.objects.get_or_create(pk=1)
        return centro


class BloqueHorario(models.Model):
    """Horario de 45 minutos que publica un especialista (RF-04)."""

    especialista = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="bloques"
    )
    inicio = models.DateTimeField()
    fin = models.DateTimeField()
    disponible = models.BooleanField(default=True)

    class Meta:
        ordering = ["inicio"]
        verbose_name = "bloque horario"
        verbose_name_plural = "bloques horarios"

    def __str__(self):
        return f"{timezone.localtime(self.inicio):%d-%m-%Y %H:%M} - {self.especialista}"


class Cita(models.Model):
    SOLICITADA = "SOLICITADA"
    CONFIRMADA = "CONFIRMADA"
    RECHAZADA = "RECHAZADA"
    CANCELADA = "CANCELADA"
    ESTADOS = [
        (SOLICITADA, "Solicitada"),
        (CONFIRMADA, "Confirmada"),
        (RECHAZADA, "Rechazada"),
        (CANCELADA, "Cancelada"),
    ]

    paciente = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="citas"
    )
    bloque = models.ForeignKey(BloqueHorario, on_delete=models.PROTECT, related_name="citas")
    estado = models.CharField(max_length=10, choices=ESTADOS, default=SOLICITADA)
    motivo_consulta = models.CharField(max_length=300, blank=True)
    motivo_respuesta = models.CharField("motivo de rechazo o cancelación", max_length=300, blank=True)
    creada = models.DateTimeField(auto_now_add=True)
    actualizada = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["bloque__inicio"]

    def __str__(self):
        return f"Cita {self.id} - {self.paciente} - {self.estado}"

    # ------------------------------------------------------------ ayudas
    def esta_activa(self):
        return self.estado in [self.SOLICITADA, self.CONFIRMADA]

    def horas_que_faltan(self):
        return (self.bloque.inicio - timezone.now()) / timedelta(hours=1)

    def _guardar_y_avisar(self, accion, actor):
        """Guarda la cita y publica la señal para los observadores."""
        self.save()
        cita_cambiada.send(sender=Cita, cita=self, accion=accion, actor=actor)

    def _liberar_bloque(self):
        self.bloque.disponible = True
        self.bloque.save()

    # ------------------------------------------------------------ reglas
    @classmethod
    def solicitar(cls, paciente, bloque_id, motivo=""):
        """
        El paciente pide una hora (RF-02) sin que se pueda reservar dos veces (RF-03).

        update() marca el bloque como NO disponible solo si todavía estaba
        disponible, y devuelve cuántas filas cambió. Si dos pacientes piden el
        mismo bloque al mismo tiempo, la base de datos hace el cambio una sola
        vez: el primero recibe 1 y el segundo recibe 0 (y ve un mensaje de error).
        """
        with transaction.atomic():  # si algo falla, se deshace todo
            tomados = BloqueHorario.objects.filter(
                id=bloque_id, disponible=True, inicio__gt=timezone.now()
            ).update(disponible=False)
            if tomados == 0:
                raise ErrorCita("Ese horario ya no está disponible. Elige otro.")
            cita = cls.objects.create(
                paciente=paciente, bloque_id=bloque_id, motivo_consulta=motivo
            )
        cita_cambiada.send(sender=Cita, cita=cita, accion="solicitada", actor=paciente)
        return cita

    def confirmar(self, especialista):
        """RF-05"""
        if self.estado != self.SOLICITADA:
            raise ErrorCita("Solo se pueden confirmar citas solicitadas.")
        self.estado = self.CONFIRMADA
        self._guardar_y_avisar("confirmada", especialista)

    def rechazar(self, especialista, motivo):
        """RF-05: el rechazo siempre lleva motivo y deja libre el horario."""
        if self.estado != self.SOLICITADA:
            raise ErrorCita("Solo se pueden rechazar citas solicitadas.")
        self.estado = self.RECHAZADA
        self.motivo_respuesta = motivo
        self._liberar_bloque()
        self._guardar_y_avisar("rechazada", especialista)

    def cancelar(self, actor, motivo, revisar_24_horas=True):
        """
        RF-06: el paciente cancela con 24 horas o más de anticipación.
        RF-07: el especialista puede cancelar siempre (caso excepcional).
        """
        if not self.esta_activa():
            raise ErrorCita("Esta cita ya no está activa.")
        es_paciente = actor == self.paciente
        minimo = CentroTerapeutico.obtener().horas_minimas_cancelacion
        if es_paciente and revisar_24_horas and self.horas_que_faltan() < minimo:
            raise ErrorCita(
                f"Solo puedes cancelar con {minimo} horas de anticipación. "
                "Para casos excepcionales, habla con tu especialista."
            )
        self.estado = self.CANCELADA
        self.motivo_respuesta = motivo
        self._liberar_bloque()
        self._guardar_y_avisar("cancelada", actor)

    def reagendar(self, especialista, nuevo_bloque_id):
        """RF-08: mover la cita a otro bloque libre del mismo especialista."""
        if not self.esta_activa():
            raise ErrorCita("Solo se pueden reagendar citas activas.")
        with transaction.atomic():
            tomados = BloqueHorario.objects.filter(
                id=nuevo_bloque_id,
                especialista=especialista,
                disponible=True,
                inicio__gt=timezone.now(),
            ).update(disponible=False)
            if tomados == 0:
                raise ErrorCita("El nuevo horario no está disponible.")
            self._liberar_bloque()
            self.bloque = BloqueHorario.objects.get(id=nuevo_bloque_id)
            self.save()
        cita_cambiada.send(sender=Cita, cita=self, accion="reagendada", actor=especialista)
