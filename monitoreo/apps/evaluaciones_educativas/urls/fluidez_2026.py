from django.urls import path
from apps.evaluaciones_educativas.views import fluidez_2026

app_name = "fluidez_2026"

urlpatterns = [
    # #path('',fluidez_2026.inicio, name= 'inicio'),
    path('carga_alumno/<str:fid_actual>/<uuid:grado_public_id>',fluidez_2026.carga_alumno, name= 'carga_alumno'),
    path('editar_alumno/<uuid:alumno_public_id>/<str:fid_actual>/',fluidez_2026.editar_alumno, name= 'editar_alumno'),
    path('carga_evaluacion/<uuid:alumno_public_id>/<str:fid_actual>/',fluidez_2026.carga_evaluacion, name= 'carga_evaluacion'),
    path('editar_evaluacion/<uuid:alumno_public_id>/<str:fid_actual>/',fluidez_2026.editar_evaluacion, name= 'editar_evaluacion'),
    path('actualizar_seccion/<uuid:alumno_public_id>/', fluidez_2026.actualizar_seccion, name='actualizar_seccion'),
    path(
        "borrar_registro_alumno/<uuid:alumno_public_id>/<str:fid_actual>/",
        fluidez_2026.borrar_registro_alumno,
        name="borrar_registro_alumno",
    ),
    path('lista_examen',fluidez_2026.lista_examen, name='lista_examen'),
    path('lista_examen/<str:fid_actual>/',fluidez_2026.lista_examen, name='lista_examen_fid'),
    path("monitoreo/", fluidez_2026.monitoreo, name="monitoreo"),
    path(
        "descargar_excel_monitoreo/",
        fluidez_2026.descargar_excel_monitoreo,
        name="descargar_excel_monitoreo",
    ),
    path("monitoreo_alumno/", fluidez_2026.monitoreo_alumno, name="monitoreo_alumno"),
    path("monitoreo_regiones/", fluidez_2026.monitoreo_regiones, name="monitoreo_regiones"),
    path("descargar_excel_regiones/", fluidez_2026.descargar_excel_regiones, name="descargar_excel_regiones"),
    path("descarga_excel_datos/", fluidez_2026.pagina_descarga_excel, name="pagina_descarga_excel"),
    path("descargar_excel_datos/", fluidez_2026.descargar_excel_datos_alumnos, name="descargar_excel_datos_alumnos"),
    # path('analisis_evaluacion/',fluidez_2026.analisis_evaluaciones_noviembre_2025, name='analisis_evaluacion'),
    # path('analisis_completo_evaluacion_noviembre_2025/',fluidez_2026.analisis_evaluaciones_ministros_noviembre_2025, name='analisis_completo_evaluacion_noviembre_2025'),
    # path('analisis_evaluacion_noviembre_2025/',fluidez_2026.analisis_evaluaciones_regional_noviembre_2025, name='analisis_evaluacion_noviembre_2025'),
    # path('analisis_evaluaciones_mayo_2025/',fluidez_2026.analisis_evaluaciones_mayo_2025, name='analisis_evaluacion_mayo_2025')
    path('analisis_evaluacion/',fluidez_2026.analisis_evaluaciones_junio_2026, name='analisis_evaluacion'),
    path('analisis_evaluacion_regional/',fluidez_2026.analisis_evaluaciones_regional_junio_2026, name='analisis_evaluacion_regional'),
    path('analisis_evaluacion_ministros/',fluidez_2026.analisis_evaluaciones_ministros_junio_2026, name='analisis_evaluacion_ministros'),
    # Los paths con <str> genérico van al final para no interceptar paths específicos
    path('',fluidez_2026.lista, name='lista'),
    path('<str:fid_actual>/',fluidez_2026.lista, name='lista_fid'),
]
