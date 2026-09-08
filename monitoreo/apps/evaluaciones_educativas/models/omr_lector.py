from django.db import models
import uuid

class EstablecimientosDiagnostico_Ingreso_2026(models.Model):
	# cueanexo = models.CharField(primary_key=True,max_length=9)
	# escuela = models.CharField(max_length=255)
	# sector = models.CharField(max_length=255)
	# ambito = models.CharField(max_length=255)
	# region = models.CharField(max_length=255)
	# localidad = models.CharField(max_length=255)
	# departamento = models.CharField(max_length=255)
	id_establecimiento = models.CharField(max_length=100, primary_key=True)
	class Meta:
		#managed = False
		db_table = '"diagnostico_ingreso_2026"."establecimientos"'
		#unique_together = ('nombre_año', 'cueanexo')
	def __str__(self):
		return self.id_establecimiento

class GradoDiagnostico_Ingreso_2026(models.Model):
	id_grado = models.CharField(max_length=255, primary_key=True)
	# OPCIONES_GRADO = [
	# ('PRIMERO', '1er Grado'),
	# ('2do Año/Grado', '2do Grado'),
	# ('3er Año/Grado', '3er Grado'),
	#cambiamos de SEGUNDO A 2do Año/Grado
	# ('CUARTO', '4to Grado'),
	# ('QUINTO', '5to Grado'),
	# ('SEXTO', '6to Grado'),
	# ('SEPTIMO', '7mo Grado'),
	# ]
	# public_id = models.UUIDField(default=uuid.uuid4,editable=False,unique=True)
	# cueanexo = models.CharField(max_length=9)
	# nombre_grado = models.CharField(max_length=20, choices=OPCIONES_GRADO, default='SEPTIMO')
	# Establecimiento = models.ForeignKey(EstablecimientosDiagnostico_Ingreso_2026, on_delete=models.CASCADE)
	# estado_carga = models.BooleanField(default=False)
	class Meta:
	   #managed = False
		db_table = '"diagnostico_ingreso_2026"."grados"'
		#unique_together = ('nombre_grado', 'cueanexo')
	def __str__(self):
		return self.id_grado

class SeccionDiagnostico_Ingreso_2026(models.Model):
	# OPCIONES_SECCION = [
	# ('A', 'A'),
	# ('B', 'B'),
	# ('C', 'C'),
	# ('D', 'D'),
	# ('E', 'E'),
	# ('F', 'F'),
	# ('G', 'G'),
	# ('H', 'H'),
	# ('I', 'I'),
	# ('L', 'L'),
	# ('M', 'M'),
	# ('N', 'N'),
	# ('P', 'P'),
	# ('Q', 'Q'),
	# ('R', 'R'),
	# ('S', 'S'),
	# ('T', 'T'),
	# ('U', 'U'),
	# ('Z', 'Z'),

	# ]
	# OPCIONES_TURNO = [
	# ('MAÑANA', 'Mañana'),
	# ('TARDE', 'Tarde'),
	# ('DOBLE', 'Doble'),
	# ]
	# public_id = models.UUIDField(default=uuid.uuid4,editable=False,unique=True)
	# seccion = models.CharField(max_length=20, choices=OPCIONES_SECCION, blank=True)
	# turno = models.CharField(max_length=20, choices=OPCIONES_TURNO, blank=True )
	# grado = models.ForeignKey(GradoDiagnostico_Ingreso_2026, on_delete=models.CASCADE)
	id_seccion = models.CharField(max_length=255, primary_key=True)

	class Meta:
		#managed = False
		db_table = '"diagnostico_ingreso_2026"."secciones"'
	def __str__(self):
		return self.id_seccion

class AlumnoDiagnostico_Ingreso_2026(models.Model):
# 	OPCIONES_COMUNIDAD_INDIGENA = [
# 	('QOM', 'Qom'),
# 	('MOQOIT', 'Moqoit'),
# 	('WICHI', 'Wichí'),
# 	('NINGUNA', 'Ninguna'),
# ]
# 	OPCIONES_DISCAPACIDAD = [
# 	('SI', 'Sí, la persona tiene una discapacidad'),
# 	('NO', 'Ninguna'),
# ]
# 	public_id = models.UUIDField(default=uuid.uuid4,editable=False,unique=True)
# 	dni = models.CharField(max_length=10,unique=True,null=True,blank=True)
# 	nombre = models.CharField(max_length=50)
# 	apellido = models.CharField(max_length=50)
# 	comunidad_indigena=models.CharField(max_length=11, choices= OPCIONES_COMUNIDAD_INDIGENA, blank=True,null=True)
# 	discapacidad = models.CharField(
# 		max_length=2,
# 		choices=OPCIONES_DISCAPACIDAD,
# 		blank=True,
# 		null=True,
# 	)

	id_alumno = models.CharField(max_length=255, primary_key=True)

	seccion = models.ForeignKey(SeccionDiagnostico_Ingreso_2026, on_delete=models.CASCADE,null=True)
	class Meta:
		#managed = False
		db_table = '"diagnostico_ingreso_2026"."alumnos"'
		# unique_together = ('dni','seccion')
	def __str__(self):
		return self.id_alumno

class LecturaOMR(models.Model):
    """
    Registro de una hoja de respuestas de opción múltiple
    leída mediante OMR (Optical Mark Recognition) desde foto.

    Se vincula a un AlumnoFluidez2026 existente.
    Almacena las 12 respuestas detectadas (ítems 1-12, opciones A/B/C/D).
    """

    OPCIONES_RESPUESTA = [
        ('A', 'A'),
        ('B', 'B'),
        ('C', 'C'),
        ('D', 'D'),
        ('', 'Sin respuesta'),
    ]

    OPCIONES_MODELO = [
        ('A', 'Modelo A'),
        ('B', 'Modelo B'),
        ('C', 'Modelo C'),
        ('D', 'Modelo D'),
        ('', 'Sin especificar'),
    ]

    public_id = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True
    )

    # Relación con el alumno existente en el sistema
    alumno = models.ForeignKey(
        'evaluaciones_educativas.AlumnoDiagnostico_Ingreso_2026',
        on_delete=models.CASCADE,
        related_name='lecturas_omr',
        null=True,
        blank=True,
    )

    # Metadatos del examen
    modelo_examen = models.CharField(
        max_length=1,
        choices=OPCIONES_MODELO,
        blank=True,
        default='',
        help_text='Modelo del examen (A, B, C, D)',
    )

    fecha_lectura = models.DateTimeField(auto_now_add=True)
    encargado_carga = models.CharField(
        max_length=9,
        blank=True,
        help_text='Cuil/ID del docente que realizó la carga',
    )

    # Respuestas detectadas por OMR (ítems 1 a 12)
    item_1  = models.CharField(max_length=1, choices=OPCIONES_RESPUESTA, blank=True, default='')
    item_2  = models.CharField(max_length=1, choices=OPCIONES_RESPUESTA, blank=True, default='')
    item_3  = models.CharField(max_length=1, choices=OPCIONES_RESPUESTA, blank=True, default='')
    item_4  = models.CharField(max_length=1, choices=OPCIONES_RESPUESTA, blank=True, default='')
    item_5  = models.CharField(max_length=1, choices=OPCIONES_RESPUESTA, blank=True, default='')
    item_6  = models.CharField(max_length=1, choices=OPCIONES_RESPUESTA, blank=True, default='')
    item_7  = models.CharField(max_length=1, choices=OPCIONES_RESPUESTA, blank=True, default='')
    item_8  = models.CharField(max_length=1, choices=OPCIONES_RESPUESTA, blank=True, default='')
    item_9  = models.CharField(max_length=1, choices=OPCIONES_RESPUESTA, blank=True, default='')
    item_10 = models.CharField(max_length=1, choices=OPCIONES_RESPUESTA, blank=True, default='')
    item_11 = models.CharField(max_length=1, choices=OPCIONES_RESPUESTA, blank=True, default='')
    item_12 = models.CharField(max_length=1, choices=OPCIONES_RESPUESTA, blank=True, default='')

    # Nivel de confianza de la detección por ítem (0-100), almacenado como JSON
    # Ejemplo: {"1": 95, "2": 40, "3": 88, ...}
    confianza_json = models.JSONField(
        null=True,
        blank=True,
        help_text='Nivel de confianza de la detección OMR por ítem (0-100)',
    )

    # Indica si el docente revisó y confirmó los resultados manualmente
    revisado_manualmente = models.BooleanField(default=False)

    # Observaciones opcionales del docente
    observaciones = models.TextField(blank=True, default='')

    class Meta:
        db_table = '"diagnostico_ingreso_2026"."lecturas"'
        ordering = ['-fecha_lectura']
        verbose_name = 'Lectura OMR'
        verbose_name_plural = 'Lecturas OMR'

    def __str__(self):
        alumno_str = str(self.alumno) if self.alumno else 'Sin alumno'
        return f'OMR [{alumno_str}] — {self.fecha_lectura.strftime("%d/%m/%Y %H:%M")}'

    @property
    def respuestas_dict(self):
        """Devuelve las respuestas como diccionario {1: 'A', 2: 'B', ...}"""
        return {
            i: getattr(self, f'item_{i}', '')
            for i in range(1, 13)
        }

    @property
    def items_sin_respuesta(self):
        """Lista de ítems donde no se detectó ninguna respuesta"""
        return [i for i in range(1, 13) if not getattr(self, f'item_{i}', '')]

    @property
    def items_dudosos(self):
        """Lista de ítems con confianza baja (< 50)"""
        if not self.confianza_json:
            return []
        return [int(k) for k, v in self.confianza_json.items() if v < 50]
