from django.urls import path
from apps.evaluaciones_educativas.views import omr_lector

app_name = 'omr_lector'

urlpatterns = [
    # 1. Selección de alumno
    path('', omr_lector.seleccionar_alumno, name='seleccionar_alumno'),

    # 2. Lector OMR para un alumno específico
    path('lector/<uuid:alumno_public_id>/', omr_lector.lector_omr, name='lector_omr'),

    # 3. Guardar resultado OMR (POST JSON)
    path('guardar/<uuid:alumno_public_id>/', omr_lector.guardar_lectura, name='guardar_lectura'),

    # 4. Historial de lecturas
    path('historial/', omr_lector.lista_lecturas, name='lista_lecturas'),

    # 5. Detalle de una lectura
    path('historial/<uuid:public_id>/', omr_lector.detalle_lectura, name='detalle_lectura'),

    # 6. Procesar imagen OMR con OpenCV backend (no requiere OpenCV.js en el browser)
    path('procesar-imagen/', omr_lector.procesar_imagen_omr, name='procesar_imagen_omr'),
]
