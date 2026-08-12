from django.urls import path
from apps.evaluaciones_educativas.views import validaciones_2026

app_name = "validaciones_2026"

urlpatterns = [
    # Vista principal: lista de secciones para validar
    path('', validaciones_2026.lista_validacion, name='lista'),

    # Aprobar sección + guardar matrícula (con o sin cambio)
    path(
        'aprobar/<uuid:seccion_public_id>/',
        validaciones_2026.aprobar_seccion,
        name='aprobar_seccion',
    ),

    # Marcar sección como "No existe" (✖)
    path(
        'no_existe/<uuid:seccion_public_id>/',
        validaciones_2026.marcar_no_existe,
        name='marcar_no_existe',
    ),

    # Restablecer sección a PENDIENTE (botón ✏ Editar)
    path(
        'editar/<uuid:seccion_public_id>/',
        validaciones_2026.editar_seccion,
        name='editar_seccion',
    ),

    # Asignar cabecera a sección (pantalla final, tras validar todas)
    path(
        'cabecera/<uuid:seccion_public_id>/',
        validaciones_2026.asignar_cabecera,
        name='asignar_cabecera',
    ),
]
