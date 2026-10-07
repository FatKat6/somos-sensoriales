import re

from django import forms
from django.contrib.auth.forms import UserCreationForm

from .models import Usuario


def rut_valido(rut):
    """
    Revisa que el RUT tenga el formato 12345678-5 y que el dígito
    verificador sea correcto (algoritmo módulo 11).
    """
    if not re.fullmatch(r"\d{7,8}-[\dkK]", rut):
        return False
    numero, dv = rut.split("-")
    suma = 0
    multiplicador = 2
    for digito in reversed(numero):
        suma += int(digito) * multiplicador
        multiplicador = 2 if multiplicador == 7 else multiplicador + 1
    resultado = 11 - (suma % 11)
    if resultado == 11:
        esperado = "0"
    elif resultado == 10:
        esperado = "K"
    else:
        esperado = str(resultado)
    return dv.upper() == esperado


def agregar_clases_bootstrap(formulario):
    """Pone la clase de Bootstrap correcta a cada campo del formulario."""
    for campo in formulario.fields.values():
        if isinstance(campo.widget, forms.CheckboxInput):
            campo.widget.attrs["class"] = "form-check-input"
        else:
            campo.widget.attrs["class"] = "form-control"


class RegistroForm(UserCreationForm):
    """Registro de pacientes (RF-09). Usa la validación de contraseña de Django."""

    first_name = forms.CharField(label="Nombre", max_length=60)
    last_name = forms.CharField(label="Apellido", max_length=60)
    rut = forms.CharField(label="RUT (sin puntos y con guion)", max_length=12)
    nombre_tutor = forms.CharField(
        label="Nombre del tutor (solo si el paciente es menor de edad)",
        max_length=120,
        required=False,
    )
    acepta_datos = forms.BooleanField(
        label=(
            "Acepto que el centro use mis datos personales solo para gestionar "
            "mis citas (Ley 19.628 y Ley 21.719)."
        ),
        required=True,
    )

    class Meta:
        model = Usuario
        fields = ["first_name", "last_name", "email", "telefono", "rut", "nombre_tutor"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["email"].required = True
        agregar_clases_bootstrap(self)

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if Usuario.objects.filter(email=email).exists():
            raise forms.ValidationError("Ya existe una cuenta con ese correo.")
        return email

    def clean_rut(self):
        rut = self.cleaned_data["rut"].replace(".", "").strip().upper()
        if not rut_valido(rut):
            raise forms.ValidationError("RUT inválido.")
        return rut

    def clean_telefono(self):
        telefono = self.cleaned_data.get("telefono", "")
        if telefono and not re.fullmatch(r"\+?\d{8,12}", telefono):
            raise forms.ValidationError("Teléfono inválido (solo números, de 8 a 12).")
        return telefono


class LoginForm(forms.Form):
    email = forms.EmailField(label="Correo electrónico")
    password = forms.CharField(label="Contraseña", widget=forms.PasswordInput)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        agregar_clases_bootstrap(self)
