from datetime import timedelta

from django import forms
from django.utils import timezone

from .models import BloqueHorario, CentroTerapeutico


class BloqueForm(forms.ModelForm):
    """El especialista publica un bloque indicando solo la hora de inicio (RF-04)."""

    class Meta:
        model = BloqueHorario
        fields = ["inicio"]
        labels = {"inicio": "Fecha y hora de inicio"}
        widgets = {
            "inicio": forms.DateTimeInput(
                attrs={"type": "datetime-local", "class": "form-control"},
                format="%Y-%m-%dT%H:%M",
            )
        }

    def clean_inicio(self):
        inicio = self.cleaned_data["inicio"]
        if inicio <= timezone.now():
            raise forms.ValidationError("No puedes publicar horarios en el pasado.")

        # El fin se calcula con la duración configurada en el centro (45 min)
        duracion = CentroTerapeutico.obtener().duracion_bloque
        fin = inicio + timedelta(minutes=duracion)

        # No se permite que se cruce con otro bloque del mismo especialista
        se_cruza = BloqueHorario.objects.filter(
            especialista_id=self.instance.especialista_id,
            inicio__lt=fin,
            fin__gt=inicio,
        ).exists()
        if se_cruza:
            raise forms.ValidationError("Ese horario se cruza con otro bloque tuyo.")

        self.instance.fin = fin
        return inicio


class SolicitudForm(forms.Form):
    """El paciente elige un bloque y puede escribir el motivo de consulta (RF-02)."""

    bloque_id = forms.IntegerField(widget=forms.HiddenInput)
    motivo = forms.CharField(
        label="Motivo de consulta (opcional)",
        max_length=300,
        required=False,
        widget=forms.Textarea(attrs={"rows": 2, "class": "form-control"}),
    )


class MotivoForm(forms.Form):
    """Motivo obligatorio para rechazar o cancelar."""

    motivo = forms.CharField(max_length=300)
