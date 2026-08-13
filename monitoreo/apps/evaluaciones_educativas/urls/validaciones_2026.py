from django.urls import path
from apps.evaluaciones_educativas.views import validaciones_2026

app_name = "validaciones_2026"

urlpatterns = [
    # PASO 0: Seleccionar región (landing page)
    path('', validaciones_2026.seleccionar_region, name='lista'),

    # PASO 1: Lista de establecimientos de una región (tarjetas)
    path(
        'region/<str:region>/establecimientos/',
        validaciones_2026.lista_establecimientos,
        name='lista_establecimientos',
    ),

    # PASO 1 → ACCIÓN: Marcar participación del establecimiento (POST/JSON)
    path(
        'establecimiento/<str:cueanexo>/participacion/',
        validaciones_2026.set_participacion,
        name='set_participacion',
    ),

    # PASO 1 → MODAL: Asignar cabecera al establecimiento (POST/JSON)
    path(
        'establecimiento/<str:cueanexo>/cabecera/',
        validaciones_2026.set_cabecera_establecimiento,
        name='set_cabecera_establecimiento',
    ),

    # PASO 3: Lista de secciones de un establecimiento
    path(
        'establecimiento/<str:cueanexo>/secciones/',
        validaciones_2026.lista_secciones,
        name='lista_secciones',
    ),

    # ACCIONES sobre secciones:

    # Aprobar sección (OK, matrícula confirmada)
    path(
        'aprobar/<uuid:seccion_public_id>/',
        validaciones_2026.aprobar_seccion,
        name='aprobar_seccion',
    ),

    # Marcar sección como "Sin matrícula"
    path(
        'sin_matricula/<uuid:seccion_public_id>/',
        validaciones_2026.marcar_sin_matricula,
        name='marcar_sin_matricula',
    ),

    # Modificar matrícula con justificación
    path(
        'modificar/<uuid:seccion_public_id>/',
        validaciones_2026.modificar_seccion,
        name='modificar_seccion',
    ),

    # Restablecer sección a PENDIENTE (botón Editar)
    path(
        'editar/<uuid:seccion_public_id>/',
        validaciones_2026.editar_seccion,
        name='editar_seccion',
    ),
]
