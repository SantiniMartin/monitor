from django.db import models
from django.core.exceptions import ValidationError
from decimal import Decimal
import uuid

from apps.evaluaciones_educativas.services.omr_catalogo import (
    ITEMS_MULTIPLES_CONTEXTO,
    OPCIONES_POR_ITEM_CONTEXTO,
)

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

class ExamenMatematica(models.Model):
    """
    Registro de una hoja de respuestas de opción múltiple
    leída mediante OMR (Optical Mark Recognition) desde foto.

    Se vincula a un alumno del diagnóstico 2026.
    Almacena hasta 24 respuestas de Matemática (A/B/C/D).
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

    TIPOS_EXAMEN = [
        ('lengua', 'Lengua'),
        ('matematica', 'Matemática'),
        ('contexto', 'Examen de contexto'),
    ]

    RESPUESTAS_CORRECTAS_MATEMATICA = {
        1: 'C', 2: 'A', 3: 'B', 4: 'D', 5: 'B',
        6: 'C', 7: 'C', 8: 'A', 9: 'B', 10: 'C',
        11: 'B', 12: 'C', 13: 'A', 14: 'C', 15: 'D',
        16: 'C', 17: 'D', 18: 'C', 19: 'C', 20: 'B',
    }

    PUNTAJES_MATEMATICA_21_A_24 = {
        21: {'A': Decimal('3'), 'B': Decimal('2'), 'C': Decimal('1'), 'D': Decimal('0')},
        22: {'A': Decimal('4'), 'B': Decimal('3'), 'C': Decimal('1.5'), 'D': Decimal('0')},
        23: {'A': Decimal('4.5'), 'B': Decimal('3'), 'C': Decimal('1.5'), 'D': Decimal('0')},
        24: {'A': Decimal('6'), 'B': Decimal('3'), 'C': Decimal('1.5'), 'D': Decimal('0')},
    }

    public_id = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True
    )

    # Relación con el alumno existente en el sistema
    alumno = models.ForeignKey(
        'evaluaciones_educativas.AlumnoDiagnostico_Ingreso_2026',
        on_delete=models.CASCADE,
        related_name='examenes_matematica',
        null=True,
        blank=True,
    )

    # Metadatos del examen
    tipo_examen = models.CharField(
        max_length=12,
        choices=TIPOS_EXAMEN,
        default='lengua',
        db_index=True,
        help_text='Tipo de examen asociado a la lectura OMR',
    )
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

    # Respuestas detectadas por OMR (hasta 24 ítems según el examen)
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
    item_13 = models.CharField(max_length=1, choices=OPCIONES_RESPUESTA, blank=True, default='')
    item_14 = models.CharField(max_length=1, choices=OPCIONES_RESPUESTA, blank=True, default='')
    item_15 = models.CharField(max_length=1, choices=OPCIONES_RESPUESTA, blank=True, default='')
    item_16 = models.CharField(max_length=1, choices=OPCIONES_RESPUESTA, blank=True, default='')
    item_17 = models.CharField(max_length=1, choices=OPCIONES_RESPUESTA, blank=True, default='')
    item_18 = models.CharField(max_length=1, choices=OPCIONES_RESPUESTA, blank=True, default='')
    item_19 = models.CharField(max_length=1, choices=OPCIONES_RESPUESTA, blank=True, default='')
    item_20 = models.CharField(max_length=1, choices=OPCIONES_RESPUESTA, blank=True, default='')
    item_21 = models.CharField(max_length=1, choices=OPCIONES_RESPUESTA, blank=True, default='')
    item_22 = models.CharField(max_length=1, choices=OPCIONES_RESPUESTA, blank=True, default='')
    item_23 = models.CharField(max_length=1, choices=OPCIONES_RESPUESTA, blank=True, default='')
    item_24 = models.CharField(max_length=1, choices=OPCIONES_RESPUESTA, blank=True, default='')

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
        db_table = '"diagnostico_ingreso_2026"."examenes_matematica"'
        ordering = ['-fecha_lectura']
        verbose_name = 'Examen de Matemática'
        verbose_name_plural = 'Exámenes de Matemática'

    def __str__(self):
        alumno_str = str(self.alumno) if self.alumno else 'Sin alumno'
        return f'OMR [{alumno_str}] — {self.fecha_lectura.strftime("%d/%m/%Y %H:%M")}'

    @property
    def respuestas_dict(self):
        """Devuelve las respuestas como diccionario {1: 'A', 2: 'B', ...}"""
        return {
            i: getattr(self, f'item_{i}', '')
            for i in range(1, self.cantidad_items + 1)
        }

    @property
    def cantidad_items(self):
        if self.tipo_examen == 'matematica':
            return 24
        return 12

    @property
    def items_sin_respuesta(self):
        """Lista de ítems donde no se detectó ninguna respuesta"""
        return [
            i for i in range(1, self.cantidad_items + 1)
            if not getattr(self, f'item_{i}', '')
        ]

    @property
    def items_dudosos(self):
        """Lista de ítems con confianza baja (< 50)"""
        if not self.confianza_json:
            return []
        return [int(k) for k, v in self.confianza_json.items() if v < 50]

    def puntaje_item_matematica(self, numero_item):
        """Calcula el puntaje de un ítem de Matemática según su respuesta."""
        if numero_item not in range(1, 25):
            raise ValueError('El número de ítem debe estar entre 1 y 24.')

        respuesta = (getattr(self, f'item_{numero_item}', '') or '').upper()
        if numero_item <= 20:
            correcta = self.RESPUESTAS_CORRECTAS_MATEMATICA[numero_item]
            return Decimal('1') if respuesta == correcta else Decimal('0')

        return self.PUNTAJES_MATEMATICA_21_A_24[numero_item].get(
            respuesta,
            Decimal('0'),
        )

    def calcular_puntaje_matematica(self):
        """Devuelve el puntaje total; el máximo posible es 37.5 puntos."""
        if self.tipo_examen != 'matematica':
            return None
        return sum(
            (self.puntaje_item_matematica(item) for item in range(1, 25)),
            Decimal('0'),
        )


class ExamenLengua(models.Model):
    """Hoja OMR de Lengua, incluida la rúbrica docente del ítem 24."""

    OPCIONES_RESPUESTA = ExamenMatematica.OPCIONES_RESPUESTA
    OPCIONES_MODELO = [('A', 'Modelo A'), ('B', 'Modelo B')]
    CAMPOS_POR_ITEM = {
        **{item: f'item_{item}' for item in range(1, 25)},
        25: 'item_24_1',
        26: 'item_24_2',
        27: 'item_24_3',
    }
    ETIQUETAS_POR_ITEM = {
        **{item: str(item) for item in range(1, 25)},
        25: '24.1',
        26: '24.2',
        27: '24.3',
    }

    # Modelo A: clave oficial del PDF, páginas 4 a 10.
    # Modelo B: clave de la hoja patrón fotografiada incluida con las muestras.
    RESPUESTAS_CORRECTAS_LENGUA = {
        'A': {
            1: 'B', 2: 'C', 3: 'C', 4: 'A', 5: 'B',
            6: 'D', 7: 'C', 8: 'B', 9: 'A', 10: 'D',
            11: 'A', 12: 'B', 13: 'C', 14: 'B', 15: 'A',
            16: 'A', 17: 'B', 18: 'C', 19: 'D', 20: 'B',
        },
        'B': {
            1: 'A', 2: 'B', 3: 'A', 4: 'C', 5: 'D',
            6: 'A', 7: 'D', 8: 'B', 9: 'C', 10: 'D',
            11: 'D', 12: 'A', 13: 'B', 14: 'C', 15: 'A',
            16: 'A', 17: 'B', 18: 'C', 19: 'A', 20: 'D',
        },
    }
    PUNTAJES_LENGUA_1_A_20 = {
        1: Decimal('2'), 2: Decimal('3.15'), 3: Decimal('4'),
        4: Decimal('1.30'), 5: Decimal('4.5'), 6: Decimal('2'),
        7: Decimal('2'), 8: Decimal('2'), 9: Decimal('2.75'),
        10: Decimal('2.75'), 11: Decimal('4.75'), 12: Decimal('5.5'),
        13: Decimal('3'), 14: Decimal('3'), 15: Decimal('3.15'),
        16: Decimal('4.5'), 17: Decimal('2.75'), 18: Decimal('4.75'),
        19: Decimal('2.75'), 20: Decimal('4.75'),
    }
    PUNTAJES_RUBRICA_LENGUA = {
        21: {'A': Decimal('4.5'), 'B': Decimal('2.5'), 'C': Decimal('1.5'), 'D': Decimal('0')},
        22: {'A': Decimal('2'), 'B': Decimal('1'), 'C': Decimal('.5'), 'D': Decimal('0')},
        23: {'A': Decimal('3.15'), 'B': Decimal('2.15'), 'C': Decimal('1.15'), 'D': Decimal('0')},
        24: {'A': Decimal('8'), 'B': Decimal('4'), 'C': Decimal('2'), 'D': Decimal('0')},
        25: {'A': Decimal('6'), 'B': Decimal('3'), 'C': Decimal('1.5'), 'D': Decimal('0')},
        26: {'A': Decimal('6'), 'B': Decimal('3'), 'C': Decimal('1.5'), 'D': Decimal('0')},
        27: {'A': Decimal('5'), 'B': Decimal('3'), 'C': Decimal('2'), 'D': Decimal('0')},
    }

    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    alumno = models.ForeignKey(
        'evaluaciones_educativas.AlumnoDiagnostico_Ingreso_2026',
        on_delete=models.CASCADE,
        related_name='examenes_lengua',
        null=True,
        blank=True,
    )
    modelo_examen = models.CharField(max_length=1, choices=OPCIONES_MODELO)
    fecha_lectura = models.DateTimeField(auto_now_add=True)
    encargado_carga = models.CharField(
        max_length=9,
        blank=True,
        help_text='Cuil/ID del docente que realizó la carga',
    )

    item_1 = models.CharField(max_length=1, choices=OPCIONES_RESPUESTA, blank=True, default='')
    item_2 = models.CharField(max_length=1, choices=OPCIONES_RESPUESTA, blank=True, default='')
    item_3 = models.CharField(max_length=1, choices=OPCIONES_RESPUESTA, blank=True, default='')
    item_4 = models.CharField(max_length=1, choices=OPCIONES_RESPUESTA, blank=True, default='')
    item_5 = models.CharField(max_length=1, choices=OPCIONES_RESPUESTA, blank=True, default='')
    item_6 = models.CharField(max_length=1, choices=OPCIONES_RESPUESTA, blank=True, default='')
    item_7 = models.CharField(max_length=1, choices=OPCIONES_RESPUESTA, blank=True, default='')
    item_8 = models.CharField(max_length=1, choices=OPCIONES_RESPUESTA, blank=True, default='')
    item_9 = models.CharField(max_length=1, choices=OPCIONES_RESPUESTA, blank=True, default='')
    item_10 = models.CharField(max_length=1, choices=OPCIONES_RESPUESTA, blank=True, default='')
    item_11 = models.CharField(max_length=1, choices=OPCIONES_RESPUESTA, blank=True, default='')
    item_12 = models.CharField(max_length=1, choices=OPCIONES_RESPUESTA, blank=True, default='')
    item_13 = models.CharField(max_length=1, choices=OPCIONES_RESPUESTA, blank=True, default='')
    item_14 = models.CharField(max_length=1, choices=OPCIONES_RESPUESTA, blank=True, default='')
    item_15 = models.CharField(max_length=1, choices=OPCIONES_RESPUESTA, blank=True, default='')
    item_16 = models.CharField(max_length=1, choices=OPCIONES_RESPUESTA, blank=True, default='')
    item_17 = models.CharField(max_length=1, choices=OPCIONES_RESPUESTA, blank=True, default='')
    item_18 = models.CharField(max_length=1, choices=OPCIONES_RESPUESTA, blank=True, default='')
    item_19 = models.CharField(max_length=1, choices=OPCIONES_RESPUESTA, blank=True, default='')
    item_20 = models.CharField(max_length=1, choices=OPCIONES_RESPUESTA, blank=True, default='')
    item_21 = models.CharField(max_length=1, choices=OPCIONES_RESPUESTA, blank=True, default='')
    item_22 = models.CharField(max_length=1, choices=OPCIONES_RESPUESTA, blank=True, default='')
    item_23 = models.CharField(max_length=1, choices=OPCIONES_RESPUESTA, blank=True, default='')
    item_24 = models.CharField(max_length=1, choices=OPCIONES_RESPUESTA, blank=True, default='')
    item_24_1 = models.CharField(max_length=1, choices=OPCIONES_RESPUESTA, blank=True, default='')
    item_24_2 = models.CharField(max_length=1, choices=OPCIONES_RESPUESTA, blank=True, default='')
    item_24_3 = models.CharField(max_length=1, choices=OPCIONES_RESPUESTA, blank=True, default='')

    confianza_json = models.JSONField(null=True, blank=True)
    puntajes_json = models.JSONField(default=dict, blank=True)
    puntaje_total = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=Decimal('0'),
    )
    revisado_manualmente = models.BooleanField(default=False)
    observaciones = models.TextField(blank=True, default='')

    class Meta:
        db_table = '"diagnostico_ingreso_2026"."examenes_lengua"'
        ordering = ['-fecha_lectura']
        verbose_name = 'Examen de Lengua'
        verbose_name_plural = 'Exámenes de Lengua'

    def __str__(self):
        alumno_str = str(self.alumno) if self.alumno else 'Sin alumno'
        return f'Lengua [{alumno_str}] — {self.fecha_lectura.strftime("%d/%m/%Y %H:%M")}'

    @property
    def tipo_examen(self):
        return 'lengua'

    def get_tipo_examen_display(self):
        return 'Lengua'

    @property
    def cantidad_items(self):
        return 27

    @classmethod
    def campo_item(cls, numero_item):
        return cls.CAMPOS_POR_ITEM[numero_item]

    @classmethod
    def etiqueta_item(cls, numero_item):
        return cls.ETIQUETAS_POR_ITEM[numero_item]

    @property
    def respuestas_dict(self):
        return {
            item: getattr(self, self.campo_item(item), '')
            for item in range(1, self.cantidad_items + 1)
        }

    @property
    def items_sin_respuesta(self):
        return [item for item, respuesta in self.respuestas_dict.items() if not respuesta]

    @property
    def items_dudosos(self):
        if not self.confianza_json:
            return []
        return [int(key) for key, value in self.confianza_json.items() if value < 50]

    def puntaje_item_lengua(self, numero_item):
        if numero_item not in range(1, 28):
            raise ValueError('El número de ítem debe estar entre 1 y 27.')
        respuesta = (
            getattr(self, self.campo_item(numero_item), '') or ''
        ).upper()
        if numero_item <= 20:
            correcta = self.RESPUESTAS_CORRECTAS_LENGUA.get(
                self.modelo_examen,
                {},
            ).get(numero_item)
            return (
                self.PUNTAJES_LENGUA_1_A_20[numero_item]
                if correcta and respuesta == correcta else Decimal('0')
            )
        return self.PUNTAJES_RUBRICA_LENGUA[numero_item].get(
            respuesta,
            Decimal('0'),
        )

    def calcular_puntaje_lengua(self):
        return sum(
            (self.puntaje_item_lengua(item) for item in range(1, 28)),
            Decimal('0'),
        )

    def actualizar_puntajes(self):
        puntajes = {
            self.etiqueta_item(item): self.puntaje_item_lengua(item)
            for item in range(1, 28)
        }
        self.puntajes_json = {
            etiqueta: float(puntaje)
            for etiqueta, puntaje in puntajes.items()
        }
        self.puntaje_total = sum(puntajes.values(), Decimal('0'))

    def clean(self):
        super().clean()
        errors = {}
        if self.modelo_examen not in {'A', 'B'}:
            errors['modelo_examen'] = 'Lengua requiere seleccionar el modelo A o B.'
        for item, respuesta in self.respuestas_dict.items():
            if respuesta not in {'', 'A', 'B', 'C', 'D'}:
                errors[self.campo_item(item)] = 'La respuesta debe ser A, B, C, D o vacía.'
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.actualizar_puntajes()
        return super().save(*args, **kwargs)


class ExamenContexto(models.Model):
    """Respuestas del cuestionario de Contexto (17 preguntas, sin puntaje)."""

    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    alumno = models.ForeignKey(
        'evaluaciones_educativas.AlumnoDiagnostico_Ingreso_2026',
        on_delete=models.CASCADE,
        related_name='examenes_contexto',
        null=True,
        blank=True,
    )
    fecha_lectura = models.DateTimeField(auto_now_add=True)
    encargado_carga = models.CharField(
        max_length=9,
        blank=True,
        help_text='Cuil/ID del docente que realizó la carga',
    )

    # A-F; solo las preguntas declaradas como múltiples admiten "A,C,F".
    item_1 = models.CharField(max_length=11, blank=True, default='')
    item_2 = models.CharField(max_length=1, blank=True, default='')
    item_3 = models.CharField(max_length=1, blank=True, default='')
    item_4 = models.CharField(max_length=11, blank=True, default='')
    item_5 = models.CharField(max_length=1, blank=True, default='')
    item_6 = models.CharField(max_length=1, blank=True, default='')
    item_7 = models.CharField(max_length=11, blank=True, default='')
    item_8 = models.CharField(max_length=11, blank=True, default='')
    item_9 = models.CharField(max_length=1, blank=True, default='')
    item_10 = models.CharField(max_length=1, blank=True, default='')
    item_11 = models.CharField(max_length=1, blank=True, default='')
    item_12 = models.CharField(max_length=1, blank=True, default='')
    item_13 = models.CharField(max_length=1, blank=True, default='')
    item_14 = models.CharField(max_length=11, blank=True, default='')
    item_15 = models.CharField(max_length=1, blank=True, default='')
    item_16 = models.CharField(max_length=1, blank=True, default='')
    item_17 = models.CharField(max_length=1, blank=True, default='')

    confianza_json = models.JSONField(
        null=True,
        blank=True,
        help_text='Nivel de confianza de la detección OMR por pregunta (0-100)',
    )
    revisado_manualmente = models.BooleanField(default=False)
    observaciones = models.TextField(blank=True, default='')

    class Meta:
        db_table = '"diagnostico_ingreso_2026"."examenes_contexto"'
        ordering = ['-fecha_lectura']
        verbose_name = 'Examen de Contexto'
        verbose_name_plural = 'Exámenes de Contexto'

    def __str__(self):
        alumno_str = str(self.alumno) if self.alumno else 'Sin alumno'
        return f'Contexto [{alumno_str}] — {self.fecha_lectura.strftime("%d/%m/%Y %H:%M")}'

    @property
    def tipo_examen(self):
        return 'contexto'

    @property
    def modelo_examen(self):
        return ''

    def get_tipo_examen_display(self):
        return 'Examen de contexto'

    def clean(self):
        """Hace cumplir la cardinalidad y opciones impresas en el modelo."""
        super().clean()
        errors = {}
        for item, option_count in enumerate(OPCIONES_POR_ITEM_CONTEXTO, start=1):
            field_name = f'item_{item}'
            value = getattr(self, field_name, '')
            selected = value.split(',') if value else []
            allowed = set('ABCDEF'[:option_count])
            if (
                len(selected) != len(set(selected))
                or any(option not in allowed for option in selected)
                or value != ','.join(sorted(selected))
                or (item not in ITEMS_MULTIPLES_CONTEXTO and len(selected) > 1)
            ):
                cardinality = 'una o más opciones' if item in ITEMS_MULTIPLES_CONTEXTO else 'una sola opción'
                errors[field_name] = f'El ítem {item} admite {cardinality} entre A y {chr(64 + option_count)}.'
        if errors:
            raise ValidationError(errors)

    @property
    def cantidad_items(self):
        return 17

    @property
    def respuestas_dict(self):
        return {i: getattr(self, f'item_{i}', '') for i in range(1, 18)}

    @property
    def items_sin_respuesta(self):
        return [i for i in range(1, 18) if not getattr(self, f'item_{i}', '')]

    @property
    def items_dudosos(self):
        if not self.confianza_json:
            return []
        return [int(key) for key, value in self.confianza_json.items() if value < 50]
