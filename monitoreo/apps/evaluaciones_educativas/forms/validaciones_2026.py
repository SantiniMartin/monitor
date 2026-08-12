from django import forms
from apps.evaluaciones_educativas.models.validaciones_2026 import (
    ValCabecera,
    ValSeccion,
)



class JustificacionCambioMatriculaForm(forms.Form):
    """
    Formulario para justificar un cambio de matrícula.
    Se muestra en modal cuando el usuario modifica el valor de matrícula.
    """
    matricula_nueva = forms.IntegerField(
        label='Nueva matrícula',
        min_value=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ingresá la matrícula correcta',
            'id': 'id_matricula_nueva',
        })
    )
    justificacion = forms.CharField(
        label='Justificación del cambio',
        max_length=500,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Explicá por qué se modifica la matrícula...',
            'id': 'id_justificacion_matricula',
        })
    )


class JustificacionNoExisteForm(forms.Form):
    """
    Formulario para justificar por qué una sección/establecimiento ya no existe.
    Se muestra en modal cuando el usuario presiona ✖.
    """
    justificacion = forms.CharField(
        label='Justificación',
        max_length=500,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Explicá por qué esta sección/establecimiento ya no existe...',
            'id': 'id_justificacion_no_existe',
        })
    )


class SeleccionCabeceraForm(forms.Form):
    """
    Formulario para seleccionar una cabecera en la pantalla final de validación.
    Se muestra en modal cuando todas las secciones están procesadas.
    """
    cabecera = forms.ModelChoiceField(
        queryset=ValCabecera.objects.all(),
        label='Seleccionar Cabecera',
        empty_label='--- Seleccioná una cabecera ---',
        widget=forms.Select(attrs={
            'class': 'form-select',
            'id': 'id_cabecera',
        })
    )
