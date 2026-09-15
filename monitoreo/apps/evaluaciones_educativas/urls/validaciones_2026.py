from django.urls import path
from apps.evaluaciones_educativas.views import validaciones_2026

app_name = "validaciones_2026"

urlpatterns = [
    path('monitoreo/', validaciones_2026.monitoreo, name='monitoreo'),
    path(
        'monitoreo/cabeceras/',
        validaciones_2026.monitoreo_cabeceras,
        name='monitoreo_cabeceras',
    ),

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

    # PASO 1 → Revertir establecimiento a sin validar (sin secciones al volver)
    path(
        'establecimiento/<str:cueanexo>/revertir_sin_secciones/',
        validaciones_2026.revertir_sin_secciones,
        name='revertir_sin_secciones',
    ),

    # PASO 1 → Marcar no participa cuando todas las secciones están deshabilitadas
    path(
        'establecimiento/<str:cueanexo>/no_participa_all_deshabilitadas/',
        validaciones_2026.marcar_no_participa_all_deshabilitadas,
        name='marcar_no_participa_all_deshabilitadas',
    ),

    # PASO 1 → Validación completa del establecimiento (toggle)
    path(
        'establecimiento/<str:cueanexo>/validacion_completa/',
        validaciones_2026.validar_establecimiento_completo,
        name='validar_establecimiento_completo',
    ),

    # PASO 2: Lista de secciones de un establecimiento
    path(
        'establecimiento/<str:cueanexo>/secciones/',
        validaciones_2026.lista_secciones,
        name='lista_secciones',
    ),

    # PASO 2 → Crear sección (POST/JSON)
    path(
        'establecimiento/<str:cueanexo>/crear_seccion/',
        validaciones_2026.crear_seccion,
        name='crear_seccion',
    ),

    # ACCIONES sobre secciones:

    # Validar sección → APROBADO (POST/JSON)
    path(
        'seccion/<uuid:seccion_public_id>/validar/',
        validaciones_2026.validar_seccion,
        name='validar_seccion',
    ),

    # Deshabilitar sección (POST/JSON)
    path(
        'seccion/<uuid:seccion_public_id>/deshabilitar/',
        validaciones_2026.deshabilitar_seccion,
        name='deshabilitar_seccion',
    ),

    # Aprobar sección con matrícula (compatibilidad, POST/JSON)
    path(
        'aprobar/<uuid:seccion_public_id>/',
        validaciones_2026.aprobar_seccion,
        name='aprobar_seccion',
    ),

    # Marcar sección como "Sin matrícula" (compatibilidad, POST/JSON)
    path(
        'sin_matricula/<uuid:seccion_public_id>/',
        validaciones_2026.marcar_sin_matricula,
        name='marcar_sin_matricula',
    ),

    # Modificar matrícula con justificación (POST/JSON)
    path(
        'modificar/<uuid:seccion_public_id>/',
        validaciones_2026.modificar_seccion,
        name='modificar_seccion',
    ),

    # Restablecer sección a PENDIENTE (POST/JSON)
    path(
        'editar/<uuid:seccion_public_id>/',
        validaciones_2026.editar_seccion,
        name='editar_seccion',
    ),

    # Página para descargar el excel
    path(
        'descargar-excel-pagina/',
        validaciones_2026.pagina_descarga_excel_validaciones_2026,
        name='pagina_descarga_excel',
    ),

    # Acción de descargar el excel (monitoreo completo)
    path(
        'descargar-excel/',
        validaciones_2026.descargar_excel_establecimientos_validaciones_2026,
        name='descargar_excel',
    ),

    # Acción de descargar el excel — Modelo Establecimiento
    path(
        'descargar-excel-establecimientos/',
        validaciones_2026.descargar_excel_modelo_establecimientos,
        name='descargar_excel_establecimientos',
    ),

    # Acción de descargar el excel — Modelo Sección
    path(
        'descargar-excel-secciones/',
        validaciones_2026.descargar_excel_modelo_secciones,
        name='descargar_excel_secciones',
    ),
]
