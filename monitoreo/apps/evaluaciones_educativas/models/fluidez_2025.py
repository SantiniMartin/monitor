from django.db import models
import uuid

# Create your models here.

class Grado(models.Model):
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
    cueanexo = models.CharField(max_length=9)#REPRESENTA A ESCUELA
    nombre_grado = models.CharField(max_length=13, choices= OPCIONES_GRADO, default='2do Año/Grado')
    class Meta:
       #managed = False
        db_table = 'grados' 
        #unique_together = ('nombre_grado', 'cueanexo')   
    def __str__(self):
        return self.nombre_grado

class Seccion(models.Model):
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
    seccion = models.CharField(max_length=5, choices=OPCIONES_SECCION, blank=True)
    turno = models.CharField(max_length=6, choices=OPCIONES_TURNO, blank=True )
    grado = models.ForeignKey(Grado, on_delete=models.CASCADE)
    class Meta:
        #managed = False
        db_table = 'secciones'
        #unicidad
        unique_together = ('seccion','grado','turno')
    def __str__(self):
        nombre_seccion=f'{self.grado}_{self.seccion}_{self.turno}'
        return nombre_seccion

class Alumno(models.Model):
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
    dni = models.CharField(max_length=8,unique=True,null=True,blank=True)
    nombre = models.CharField(max_length=50)
    apellido = models.CharField(max_length=50)
    comunidad_indigena=models.CharField(max_length=11, choices= OPCIONES_COMUNIDAD_INDIGENA, blank=True)
    discapacidad = models.CharField(choices=OPCIONES_DISCAPACIDAD, blank=True)
    seccion = models.ForeignKey(Seccion, on_delete=models.CASCADE)
    class Meta:
        #managed = False
        db_table = 'alumnos'
        # unique_together = ('dni','seccion')
    def __str__(self):
        alumno_nombre=f'Alumno:{self.nombre} DNI:{self.dni}'
        return alumno_nombre


class EvaluacionFluidezLectora(models.Model):
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
    alumno = models.OneToOneField(Alumno,primary_key=True, on_delete=models.CASCADE)
    class Meta:
        #managed = False
        db_table = 'evaluaciones_fluidez_lectora'
    def __str__(self):
        nombre_examen=f'Examen fluidez lectora de {self.alumno.nombre} {self.alumno.apellido} DNI:{self.alumno.dni}'
        return nombre_examen