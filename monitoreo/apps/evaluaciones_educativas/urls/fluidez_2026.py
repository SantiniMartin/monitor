from django.urls import path
from apps.evaluaciones_educativas.views import fluidez_2026

app_name = 'fluidez_2026' 

urlpatterns = [
	#path('',fluidez_2026.inicio, name= 'inicio'),
    path('carga_alumno/<str:fid_actual>/<uuid:grado_public_id>',fluidez_2026.carga_alumno, name= 'carga_alumno'),
    path('editar_alumno/<uuid:alumno_public_id>/<str:fid_actual>/',fluidez_2026.editar_alumno, name= 'editar_alumno'),
	path('carga_evaluacion/<uuid:alumno_public_id>/<str:fid_actual>/',fluidez_2026.carga_evaluacion, name= 'carga_evaluacion'),
	path('editar_evaluacion/<uuid:alumno_public_id>/<str:fid_actual>/',fluidez_2026.editar_evaluacion, name= 'editar_evaluacion'),
    # path('',fluidez_2026.grado, name='grados'),
	path('<str:fid_actual>/',fluidez_2026.lista, name='lista'),
    path('',fluidez_2026.lista, name='lista'),
    path('lista_examen',fluidez_2026.lista_examen, name='lista_examen'),
    path('lista_examen/<str:fid_actual>/',fluidez_2026.lista_examen, name='lista_examen'),
    path('actualizar_seccion/<uuid:alumno_public_id>/', fluidez_2026.actualizar_seccion, name='actualizar_seccion'),
    # path('lista_grado/<str:grado>',fluidez_2026.lista_grado, name='lista_grado'),
	# path('asistencia/<uuid:alumno_public_id>/',fluidez_2026.asistencia, name='asistencia'),
	#path('editar_asistencia/<uuid:alumno_public_id>/',fluidez_2026.editar_asistencia, name='editar_asistencia'),
    path('borrar_registro_alumno/<uuid:alumno_public_id>/<str:fid_actual>/',fluidez_2026.borrar_registro_alumno, name='borrar_registro_alumno'),
	path('descargar_excel/<uuid:grado_public_id>/',fluidez_2026.descargar_excel, name='excel'),
    path('completar_carga/<uuid:grado_public_id>/',fluidez_2026.completar_carga, name='completar_carga'),
    # path('analisis_evaluacion/',fluidez_2026.analisis_evaluaciones_noviembre_2025, name='analisis_evaluacion'),
    # path('analisis_completo_evaluacion_noviembre_2025/',fluidez_2026.analisis_evaluaciones_ministros_noviembre_2025, name='analisis_completo_evaluacion_noviembre_2025'),
    # path('analisis_evaluacion_noviembre_2025/',fluidez_2026.analisis_evaluaciones_regional_noviembre_2025, name='analisis_evaluacion_noviembre_2025'),
    # path('analisis_evaluaciones_mayo_2025/',fluidez_2026.analisis_evaluaciones_mayo_2025, name='analisis_evaluacion_mayo_2025')
	# path('monitoreo/',fluidez_2025.monitoreo, name='monitoreo'),
	
]