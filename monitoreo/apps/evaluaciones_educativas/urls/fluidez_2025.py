from django.urls import path
from apps.evaluaciones_educativas.views import fluidez_2025

app_name = 'fluidez_2025' 

urlpatterns = [
	path('carga_alumno/<uuid:grado_public_id>',fluidez_2025.carga_alumno, name= 'carga_alumno'),
    path('editar_alumno/<uuid:alumno_public_id>/',fluidez_2025.editar_alumno, name= 'editar_alumno'),
	path('carga_evaluacion/<uuid:alumno_public_id>/',fluidez_2025.carga_evaluacion, name= 'carga_evaluacion'),
	path('editar_evaluacion/<uuid:alumno_public_id>/',fluidez_2025.editar_evaluacion, name= 'editar_evaluacion'),
    path('',fluidez_2025.grado, name='grados'),
	path('lista/<uuid:grado_public_id>/',fluidez_2025.lista, name='lista'),
    path('lista_grado/<str:grado>',fluidez_2025.lista_grado, name='lista_grado'),
	path('asistencia/<uuid:alumno_public_id>/',fluidez_2025.asistencia, name='asistencia'),
	path('editar_asistencia/<uuid:alumno_public_id>/',fluidez_2025.editar_asistencia, name='editar_asistencia'),
    path('borrar_registro_alumno/<uuid:alumno_public_id>/',fluidez_2025.borrar_registro_alumno, name='borrar_registro_alumno'),
	path('descargar_excel/<uuid:grado_public_id>/',fluidez_2025.descargar_excel, name='excel'),
    path('analisis_evaluacion/',fluidez_2025.analisis_evaluaciones_noviembre_2025, name='analisis_evaluacion'),
    path('analisis_completo_evaluacion_noviembre_2025/',fluidez_2025.analisis_evaluaciones_ministros_noviembre_2025, name='analisis_completo_evaluacion_noviembre_2025'),
    path('analisis_evaluacion_noviembre_2025/',fluidez_2025.analisis_evaluaciones_regional_noviembre_2025, name='analisis_evaluacion_noviembre_2025'),
    path('analisis_evaluaciones_mayo_2025/',fluidez_2025.analisis_evaluaciones_mayo_2025, name='analisis_evaluacion_mayo_2025')
	# path('monitoreo/',fluidez_2025.monitoreo, name='monitoreo'),
	
]