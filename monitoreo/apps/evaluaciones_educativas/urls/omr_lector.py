from django.urls import path
from apps.evaluaciones_educativas.views import omr_lector

app_name = 'omr_lector'

urlpatterns = [
    # 1. Selección de alumno
    path('', omr_lector.seleccionar_alumno, name='seleccionar_alumno'),

    # 2. Selección de materia para un alumno autorizado
    path(
        'alumno/<str:id_alumno>/materia/',
        omr_lector.seleccionar_materia,
        name='seleccionar_materia',
    ),

    # 3. Lector OMR para el alumno y la materia seleccionados
    path(
        'lector/<str:id_alumno>/<slug:materia>/',
        omr_lector.lector_omr,
        name='lector_omr',
    ),

    # 4. Guardar resultado OMR (POST JSON)
    path(
        'guardar/<str:id_alumno>/<slug:materia>/',
        omr_lector.guardar_lectura,
        name='guardar_lectura',
    ),

    # 5. Historial de lecturas
    path('historial/', omr_lector.lista_lecturas, name='lista_lecturas'),

    # 6. Detalle de una lectura
    path('historial/<uuid:public_id>/', omr_lector.detalle_lectura, name='detalle_lectura'),

    # 7. Procesar imagen OMR con OpenCV backend (no requiere OpenCV.js en el browser)
    path('procesar-imagen/', omr_lector.procesar_imagen_omr, name='procesar_imagen_omr'),
]
