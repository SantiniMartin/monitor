from django.db import models
import uuid

class EstablecimientosFluidez2026(models.Model):
	cueanexo = models.CharField(primary_key=True,max_length=9)
	escuela = models.CharField(max_length=255)
	sector = models.CharField(max_length=255)
	ambito = models.CharField(max_length=255)
	region = models.CharField(max_length=255)
	localidad = models.CharField(max_length=255)
	departamento = models.CharField(max_length=255)
	class Meta:
		#managed = False
		db_table = '"fluidez_2026"."establecimientos"' 
		#unique_together = ('nombre_año', 'cueanexo')   
	def __str__(self):
		return self.escuela
class GradoFluidez2026(models.Model):
	OPCIONES_GRADO = [
	# ('PRIMERO', '1er Grado'),
	('2do Año/Grado', '2do Grado'),
	('3er Año/Grado', '3er Grado'),
	#cambiamos de SEGUNDO A 2do Año/Grado
	# ('CUARTO', '4to Grado'),
	# ('QUINTO', '5to Grado'),
	# ('SEXTO', '6to Grado'),
	# ('SEPTIMO', '7mo Grado'),
	]
	public_id = models.UUIDField(default=uuid.uuid4,editable=False,unique=True)
	cueanexo = models.CharField(max_length=9)
	nombre_grado = models.CharField(max_length=13, choices= OPCIONES_GRADO, default='2do Año/Grado')
	Establecimiento = models.ForeignKey(EstablecimientosFluidez2026, on_delete=models.CASCADE)
	estado_carga = models.BooleanField(default=False)
	class Meta:
	   #managed = False
		db_table = '"fluidez_2026"."grados"' 
		#unique_together = ('nombre_grado', 'cueanexo')   
	def __str__(self):
		return self.nombre_grado

class SeccionFluidez2026(models.Model):
	OPCIONES_SECCION = [
	('A', 'A'),
	('B', 'B'),
	('C', 'C'),
	('D', 'D'),
	('E', 'E'),
	('F', 'F'),
	('G', 'G'),
	('H', 'H'),
	('I', 'I'),
	('L', 'L'),
	('M', 'M'),
	('N', 'N'),
	('P', 'P'),
	('Q', 'Q'),
	('R', 'R'),
	('S', 'S'),
	('T', 'T'),
	('U', 'U'),
	('Z', 'Z'),
	
	]
	OPCIONES_TURNO = [
	('MAÑANA', 'Mañana'),
	('TARDE', 'Tarde'),
	('DOBLE', 'Doble'),
	]
	public_id = models.UUIDField(default=uuid.uuid4,editable=False,unique=True)
	seccion = models.CharField(max_length=20, choices=OPCIONES_SECCION, blank=True)
	turno = models.CharField(max_length=20, choices=OPCIONES_TURNO, blank=True )
	grado = models.ForeignKey(GradoFluidez2026, on_delete=models.CASCADE)
	class Meta:
		#managed = False
		db_table = '"fluidez_2026"."secciones"'
		#unicidad
		unique_together = ('seccion','grado','turno')
	def __str__(self):
		nombre_seccion=f'{self.grado}_{self.seccion}_{self.turno}'
		return nombre_seccion

class AlumnoFluidez2026(models.Model):
	OPCIONES_COMUNIDAD_INDIGENA = [
	('QOM', 'Qom'),
	('MOQOIT', 'Moqoit'),
	('WICHI', 'Wichí'),
	('NINGUNA', 'Ninguna'),
]
	OPCIONES_DISCAPACIDAD = [
	('SI', 'Sí, la persona tiene una discapacidad'),
	('NO', 'Ninguna'),
]
	public_id = models.UUIDField(default=uuid.uuid4,editable=False,unique=True)
	dni = models.CharField(max_length=10,unique=True,null=True,blank=True)
	nombre = models.CharField(max_length=50)
	apellido = models.CharField(max_length=50)
	comunidad_indigena=models.CharField(max_length=11, choices= OPCIONES_COMUNIDAD_INDIGENA, blank=True,null=True)
	discapacidad = models.CharField(choices=OPCIONES_DISCAPACIDAD, blank=True,null=True)
	seccion = models.ForeignKey(SeccionFluidez2026, on_delete=models.CASCADE,null=True)
	class Meta:
		#managed = False
		db_table = '"fluidez_2026"."alumnos"'
		# unique_together = ('dni','seccion')
	def __str__(self):
		alumno_nombre=f'Alumno:{self.nombre} DNI:{self.dni}'
		return alumno_nombre


class EvaluacionFluidezLectoraFluidez2026(models.Model):
	OPCIONES_EVALUACION = [
	('A', 'A'),
	('B', 'B'),
	('C', 'C'),
	('D', 'D'),
	('NORESPONDE', 'NoResponde'),    
	]
	OPCIONES_ASISTENCIA = [
	('PRESENTE','Presente'),
	('AUSENTE','Ausente'),    
	]
	cantidad_palabras_leidas = models.IntegerField(default=0, null=True)
	pregunta_1 = models.CharField(max_length=10,choices= OPCIONES_EVALUACION, blank=True,null=True)
	pregunta_2 = models.CharField(max_length=10,choices= OPCIONES_EVALUACION, blank=True,null=True)
	pregunta_3 = models.CharField(max_length=10,choices= OPCIONES_EVALUACION, blank=True,null=True)
	pregunta_4 = models.CharField(max_length=10,choices= OPCIONES_EVALUACION, blank=True,null=True)
	pregunta_5 = models.CharField(max_length=10,choices= OPCIONES_EVALUACION, blank=True,null=True)
	pregunta_6 = models.CharField(max_length=10,choices= OPCIONES_EVALUACION, blank=True,null=True)
	asistencia = models.CharField(choices=OPCIONES_ASISTENCIA,default='AUSENTE')
	encargado_carga=models.CharField(max_length=9)
	alumno = models.OneToOneField(AlumnoFluidez2026,primary_key=True, on_delete=models.CASCADE)
	class Meta:
		#managed = False
		db_table = '"fluidez_2026"."evaluaciones_fluidez_lectora"'
	def __str__(self):
		nombre_examen=f'Examen fluidez lectora de {self.alumno.nombre} {self.alumno.apellido} DNI:{self.alumno.dni}'
		return nombre_examen
	


class TablaTemporalAplicadores(models.Model):
	cuil = models.CharField(max_length=20, primary_key=True)
	cueanexo = models.CharField(max_length=15, null=True, blank=True)
	nombre_institucion = models.CharField(max_length=255, null=True, blank=True)
	localidad = models.CharField(max_length=50, null=True, blank=True)
	departamento = models.CharField(max_length=100, null=True, blank=True)
	region = models.CharField(max_length=100, null=True, blank=True)
	turno = models.CharField(max_length=10, null=True, blank=True)
	tipo_documento = models.CharField(max_length=250, null=True, blank=True)
	apellido = models.CharField(max_length=250, null=True, blank=True)
	nombre_apellido = models.CharField(max_length=300, null=True, blank=True)
	titulacion = models.CharField(max_length=255, null=True, blank=True)
	grado = models.CharField(max_length=50, null=True, blank=True)
	seccion = models.CharField(max_length=250, null=True, blank=True)
	estado_inscripcion = models.CharField(max_length=100, null=True, blank=True)
	ciclo_lectivo = models.CharField(max_length=50, null=True, blank=True)

	class Meta:
		managed = False  # <--- Evita que Django cree o modifique la tabla
		db_table = '"fluidez_2026"."tabla_temporal_aplicadores"'  # <--- Esquema y tabla

	def str(self):
		return f"{self.nombre_apellido} - {self.cuil}"
	

class TablaTemporalAlumnoFluidez2026(models.Model):
    # NOTA: Django necesita obligatoriamente un campo primary_key.
    # Si la tabla no tiene una clave primaria explícita, puedes usar uno de los 
    # campos existentes (como numero_de_documento si es único) o definir un campo ficticio.
    # Usamos primary_key=True en el documento asumiendo que te servirá para identificar filas.
    numero_de_documento = models.CharField(max_length=20, primary_key=True, db_column='numero_de_documento')

    cueanexo = models.CharField(max_length=15, null=True, blank=True)
    nombre_institucion = models.CharField(max_length=255, null=True, blank=True)
    nivel = models.CharField(max_length=100, null=True, blank=True)
    tipo_documento = models.CharField(max_length=250, null=True, blank=True)
    apellido = models.CharField(max_length=250, null=True, blank=True)
    nombre = models.CharField(max_length=250, null=True, blank=True)
    titulacion = models.CharField(max_length=255, null=True, blank=True)
    anio = models.CharField(max_length=50, null=True, blank=True)
    seccion = models.CharField(max_length=250, null=True, blank=True)
    estado_inscripcion = models.CharField(max_length=100, null=True, blank=True)
    ciclo_lectivo = models.CharField(max_length=50, null=True, blank=True)

    class Meta:
        managed = False  # <--- Evita que Django cree o modifique la tabla
        db_table = '"fluidez_2026"."tabla_temporal_alumno"'  # <--- Esquema y tabla

    def str(self):
        return f"{self.apellido}, {self.nombre} - {self.numero_de_documento}"