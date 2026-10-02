from django.db import models
# from .modelo_oficial import *

# #--------------------------------FLUIDEZ OCTUBRE 2026-----------------------------------


# class Fluidez_Lectora_Octubre_2026 (models.Model):
#     """
#     Evaluación de Fluidez Lectora - Octubre 2026.
#     Subtipo exclusivo de Evaluación (especialización).
#     Relación: 1:1 con Evaluación y 1:1 con AlumnoFluidez2026.
#     """
#     OPCIONES_EVALUACION = [
#         ('A', 'A'),
#         ('B', 'B'),
#         ('C', 'C'),
#         ('D', 'D'),
#         ('NORESPONDE', 'NoResponde'),
#     ]
#     OPCIONES_ASISTENCIA = [
#         ('PRESENTE', 'Presente'),
#         ('AUSENTE', 'Ausente'),
#     ]

#     evaluacion = models.OneToOneField(
#         Evaluacion,
#         on_delete=models.CASCADE,
#         primary_key=True,
#         related_name="fluidez_lectora_octubre_2026",
#     )
#     alumno = models.OneToOneField(
#         'AlumnoFluidez2026',
#         on_delete=models.CASCADE,
#         related_name="fluidez_lectora_octubre_2026",
#         null=True,
#         blank=True,
#     )
#     cantidad_palabras_leidas = models.IntegerField(default=0, null=True)
#     pregunta_1 = models.CharField(max_length=10, choices=OPCIONES_EVALUACION, blank=True, null=True)
#     pregunta_2 = models.CharField(max_length=10, choices=OPCIONES_EVALUACION, blank=True, null=True)
#     pregunta_3 = models.CharField(max_length=10, choices=OPCIONES_EVALUACION, blank=True, null=True)
#     pregunta_4 = models.CharField(max_length=10, choices=OPCIONES_EVALUACION, blank=True, null=True)
#     pregunta_5 = models.CharField(max_length=10, choices=OPCIONES_EVALUACION, blank=True, null=True)
#     pregunta_6 = models.CharField(max_length=10, choices=OPCIONES_EVALUACION, blank=True, null=True)
#     asistencia = models.CharField(choices=OPCIONES_ASISTENCIA, default='AUSENTE')
#     encargado_carga = models.CharField(max_length=9)

#     class Meta:
#         db_table = '"datos_oficiales"."fluidez_lectora_octubre_2026"'
#         verbose_name = "Fluidez Lectora Octubre 2026"
#         verbose_name_plural = "Fluidez Lectora Octubre 2026"

#     def __str__(self):
#         alumno_info = self.alumno.nombre if self.alumno else f"Eval #{self.evaluacion_id}"
#         return f"Fluidez Lectora Octubre 2026 - {alumno_info}"



# class TablaTemporalAplicadoresFluidezOctubre2026(models.Model):
# 	cuil = models.CharField(max_length=20, primary_key=True)
# 	cueanexo = models.CharField(max_length=15, null=True, blank=True)
# 	nombre_institucion = models.CharField(max_length=255, null=True, blank=True)
# 	localidad = models.CharField(max_length=50, null=True, blank=True)
# 	departamento = models.CharField(max_length=100, null=True, blank=True)
# 	region = models.CharField(max_length=100, null=True, blank=True)
# 	turno = models.CharField(max_length=10, null=True, blank=True)
# 	tipo_documento = models.CharField(max_length=250, null=True, blank=True)
# 	apellido = models.CharField(max_length=250, null=True, blank=True)
# 	nombre_apellido = models.CharField(max_length=300, null=True, blank=True)
# 	titulacion = models.CharField(max_length=255, null=True, blank=True)
# 	grado = models.CharField(max_length=50, null=True, blank=True)
# 	seccion = models.CharField(max_length=250, null=True, blank=True)
# 	estado_inscripcion = models.CharField(max_length=100, null=True, blank=True)
# 	ciclo_lectivo = models.CharField(max_length=50, null=True, blank=True)

# 	class Meta:
# 		managed = False  # <--- Evita que Django cree o modifique la tabla
# 		db_table = '"datos_oficiales"."tabla_temporal_aplicadores_fluidez_octubre_2026"'  # <--- Esquema y tabla

# 	def str(self):
# 		return f"{self.nombre_apellido} - {self.cuil}"

#-------------tabla tabuladores----------------------------

class TabuladoresFluidezOctubre2026(models.Model):
    apellido = models.CharField(max_length=250, null=True, blank=True)
    nombre = models.CharField(max_length=250, null=True, blank=True)
    cuil = models.CharField(max_length=20, primary_key=True)
    correo = models.CharField(max_length=250, null=True, blank=True)
    celular = models.CharField(max_length=250, null=True, blank=True)
    region = models.CharField(max_length=250, null=True, blank=True)
    lista_cueanexos = models.JSONField(default=list, null=True, blank=True)

    class Meta:
        db_table = '"datos_oficiales"."tabuladores_fluidez_octubre_2026"'
    
    def __str__(self):
        return f"{self.apellido} {self.nombre} - {self.cuil}"

class TemporalCargaTabuladoresFluidez2026Eliminar(models.Model):
    region = models.CharField(max_length=100)
    tabuladores_permitidos = models.IntegerField(default=0)

    class Meta:
        managed = False  
        db_table = '"datos_oficiales"."temporal_carga_tabuladores_fluidez_2026_eliminar"'  
    def __str__(self):
        return f"{self.region} (Tabuladores: {self.tabuladores_permitidos})"