from django.db import models
import uuid



class ValEstablecimientoManager(models.Manager):
    def for_referente(self, cuil, cueanexo):
        """Devuelve el establecimiento si el referente tiene acceso a su región, o None."""
        try:
            est = self.get(cueanexo=cueanexo)
        except self.model.DoesNotExist:
            return None
        
        regiones_autorizadas = set(
            ValReferenteCargaTemporal.objects
            .filter(cuil=cuil)
            .values_list('region', flat=True)
        )
        if est.region not in regiones_autorizadas:
            return None
        return est


class ValSeccionManager(models.Manager):
    def for_referente(self, cuil, public_id):
        """Devuelve la sección si el referente tiene acceso a la región del establecimiento, o None."""
        try:
            seccion = self.select_related('grado__establecimiento').get(public_id=public_id)
        except self.model.DoesNotExist:
            return None
            
        regiones_autorizadas = set(
            ValReferenteCargaTemporal.objects
            .filter(cuil=cuil)
            .values_list('region', flat=True)
        )
        if seccion.grado.establecimiento.region not in regiones_autorizadas:
            return None
        return seccion


class ValReferenteCargaTemporal(models.Model):
	"""
	Tabla maestra que mapea CUIL → Región del referente de carga.
	Un mismo CUIL puede tener múltiples filas (varias regiones).
	"""
	cuil = models.CharField(max_length=20)
	nombre = models.CharField(max_length=150)
	apellido = models.CharField(max_length=150)
	region = models.CharField(max_length=100)
	dni = models.CharField(max_length=20, null=True, blank=True)

	class Meta:
		db_table = '"validaciones_2026"."referentes_carga_temporal"'
		verbose_name = 'Referente de Carga Temporal'
		verbose_name_plural = 'Referentes de Carga Temporal'

	def __str__(self):
		return f"{self.apellido}, {self.nombre} — CUIL: {self.cuil} — Región: {self.region}"


class ValEstablecimiento(models.Model):
	"""
	Establecimientos educativos para el proceso de validación 2026.
	Equivalente a EstablecimientosFluidez2026 pero en esquema validaciones_2026.

	Campos de participación Aprender:
	  participa_aprender: None = no procesado, True = participa, False = no participa.
	  cabecera: FK a ValCabecera (solo si participa).
	  carga_completa: True cuando el referente finalizó la carga de secciones.
	  motivo_no_participa: razón por la que no participa (si aplica).
	"""
	objects = ValEstablecimientoManager()
	
	cueanexo = models.CharField(primary_key=True, max_length=9)
	escuela = models.CharField(max_length=255)
	sector = models.CharField(max_length=255)
	ambito = models.CharField(max_length=255)
	region = models.CharField(max_length=255)
	localidad = models.CharField(max_length=255)
	departamento = models.CharField(max_length=255)
	codigo_provincia = models.CharField(max_length=20, blank=True, null=True)
	provincia = models.CharField(max_length=255, blank=True, null=True)
	codigo_departamento = models.CharField(max_length=20, blank=True, null=True)
	codigo_localidad = models.CharField(max_length=20, blank=True, null=True)
	direccion = models.CharField(max_length=255, blank=True, null=True)
	codigo_area = models.CharField(max_length=20, blank=True, null=True)
	codigo_postal = models.CharField(max_length=20, blank=True, null=True)
	telefono = models.CharField(max_length=20, blank=True, null=True)
	nombre_director = models.CharField(max_length=255, blank=True, null=True)
	apellido_director = models.CharField(max_length=255, blank=True, null=True)
	telefono_director = models.CharField(max_length=20, blank=True, null=True)
	correo_director = models.EmailField(max_length=255, blank=True, null=True)
	# ── Participación en Aprender ──────────────────────────────────────
	# 'participa' | 'no participa' | 'sin validar participación'
	class EstadoParticipacion(models.TextChoices):
		PARTICIPA      = 'PARTICIPA',               'Participa'
		NO_PARTICIPA   = 'NO PARTICIPA',            'No participa'
		SIN_VALIDAR    = 'SIN VALIDAR PARTICIPACION', 'Sin validar participación'

	participa_aprender = models.CharField(
		max_length=30,
		choices=EstadoParticipacion.choices,
		default=EstadoParticipacion.SIN_VALIDAR,
		verbose_name='Participa en Aprender',
		help_text="'participa' | 'no participa' | 'sin validar participación'"
	)
	cabecera = models.ForeignKey(
		'ValCabecera',
		on_delete=models.SET_NULL,
		null=True,
		blank=True,
		related_name='establecimientos',
		verbose_name='Cabecera asignada',
	)
	carga_completa = models.BooleanField(
		default=False,
		verbose_name='Carga completa',
		help_text='True cuando el referente confirmó que terminó de cargar todas las secciones'
	)
	motivo_no_participa = models.CharField(
		max_length=150,
		blank=True,
		null=True,
		verbose_name='Motivo de no participación',
	)

	class Meta:
		db_table = '"validaciones_2026"."establecimientos"'
		verbose_name = 'Establecimiento (Validaciones)'
		verbose_name_plural = 'Establecimientos (Validaciones)'

	def __str__(self):
		return self.escuela


class ValGrado(models.Model):
	"""
	Grados asociados a los establecimientos (Validaciones 2026).
	Equivalente a GradoFluidez2026 pero en esquema validaciones_2026.
	"""
	OPCIONES_GRADO = [
		('3er Año/Grado', '3er Año/Grado'),
	]
	public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
	cueanexo = models.CharField(max_length=9)
	nombre_grado = models.CharField(max_length=50, choices=OPCIONES_GRADO, default='3er Año/Grado')
	establecimiento = models.ForeignKey(ValEstablecimiento, on_delete=models.CASCADE, related_name='grados')
	estado_carga = models.BooleanField(default=False)
	grado_creado = models.BooleanField(default=False, verbose_name='Grado creado manualmente')

	class Meta:
		db_table = '"validaciones_2026"."grados"'
		verbose_name = 'Grado (Validaciones)'
		verbose_name_plural = 'Grados (Validaciones)'

	def __str__(self):
		return self.nombre_grado


class ValCabecera(models.Model):
	"""
	Lugares o ubicaciones que son cabeceras regionales.
	Contiene datos geográficos y de contacto del coordinador.
	"""
	codigo_departamento = models.CharField(max_length=20, blank=True, null=True)
	localidad = models.CharField(max_length=255, blank=True, null=True)
	codigo_localidad = models.CharField(max_length=20, blank=True, null=True)
	regional = models.CharField(max_length=100, blank=True, null=True)
	codigo_cabecera = models.CharField(max_length=20, blank=True, null=True)
	nombre_cabecera = models.CharField(max_length=255)
	direccion = models.CharField(max_length=255, blank=True, null=True)
	detalle_direccion = models.CharField(max_length=255, blank=True, null=True)
	codigo_postal = models.CharField(max_length=10, blank=True, null=True)
	codigo_area_cabecera = models.CharField(max_length=10, blank=True, null=True)
	telefono_cabecera = models.CharField(max_length=30, blank=True, null=True)
	nombre_coordinador = models.CharField(max_length=255, blank=True, null=True)
	correo_coordinador = models.EmailField(blank=True, null=True)
	codigo_area_coordinador = models.CharField(max_length=10, blank=True, null=True)
	telefono_coordinador = models.CharField(max_length=30, blank=True, null=True)
	cuil_coordinador = models.CharField(max_length=20, blank=True, null=True)
	provincia = models.CharField(max_length=100, blank=True, null=True)
	cod_provincia = models.CharField(max_length=50, blank=True, null=True)
	cantidad_establecimientos_asociados = models.IntegerField(default=0)
	cantidad_secciones_asociadas = models.IntegerField(default=0)
	cantidad_matriculas_por_seccion = models.IntegerField(default=0)

	class Meta:
		db_table = '"validaciones_2026"."cabeceras"'
		verbose_name = 'Cabecera'
		verbose_name_plural = 'Cabeceras'

	def __str__(self):
		return f"{self.nombre_cabecera} — Regional: {self.regional}"


class ValSeccion(models.Model):
	"""
	Secciones de cada grado (Validaciones 2026).
	Equivalente a SeccionFluidez2026 pero en esquema validaciones_2026,
	con campos adicionales: matricula, estado de validación.
	"""
	objects = ValSeccionManager()

	OPCIONES_SECCION = [
		('A', 'A'), ('B', 'B'), ('C', 'C'), ('D', 'D'), ('E', 'E'),
		('F', 'F'), ('G', 'G'), ('H', 'H'), ('I', 'I'), ('L', 'L'),
		('M', 'M'), ('N', 'N'), ('P', 'P'), ('Q', 'Q'), ('R', 'R'),
		('S', 'S'), ('T', 'T'), ('U', 'U'), ('Z', 'Z'),
	]
	OPCIONES_TURNO = [
		('MAÑANA', 'Mañana'),
		('MAÑANA EXTENDIDA', 'Mañana Extendida'),
		('TARDE', 'Tarde'),
		('TARDE EXTENDIDA', 'Tarde Extendida'),
		('DOBLE', 'Doble'),
		('VESPERTINO', 'Vespertino'),
	]
	OPCIONES_ESTADO = [
		('PENDIENTE', 'Pendiente'),
		('APROBADO', 'Aprobado'),
		('SIN_MATRICULA', 'Sin matrícula'),
		('MODIFICADO', 'Modificado'),
		('DESHABILITADO', 'Deshabilitado'),
	]

	public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
	seccion = models.CharField(max_length=20, choices=OPCIONES_SECCION, blank=True)
	turno = models.CharField(max_length=20, choices=OPCIONES_TURNO, blank=True)
	grado = models.ForeignKey(ValGrado, on_delete=models.CASCADE, related_name='secciones')
	matricula = models.IntegerField(null=True, blank=True, verbose_name='Matrícula cargada')
	estado_validacion = models.CharField(
		max_length=15,
		choices=OPCIONES_ESTADO,
		default='PENDIENTE',
		verbose_name='Estado de validación'
	)
	motivo_deshabilitacion = models.CharField(
		max_length=150,
		blank=True,
		null=True,
		verbose_name='Motivo de deshabilitación',
	)
	seccion_creada = models.BooleanField(
		default=False,
		verbose_name='Sección creada manualmente',
	)
	class Meta:
		db_table = '"validaciones_2026"."secciones"'
		unique_together = ('seccion', 'grado', 'turno')
		verbose_name = 'Sección (Validaciones)'
		verbose_name_plural = 'Secciones (Validaciones)'

	def __str__(self):
		return f"{self.grado}_{self.seccion}_{self.turno}"


class ValHistorialMatriculas(models.Model):
	"""
	Registra cada cambio de matrícula en una sección.
	La matrícula nueva pisa el valor en ValSeccion.matricula,
	y acá queda el historial completo con justificación.
	"""
	seccion = models.ForeignKey(ValSeccion, on_delete=models.CASCADE, related_name='historial_matriculas')
	matricula_anterior = models.IntegerField(null=True, blank=True)
	matricula_nueva = models.IntegerField(null=True, blank=True)
	justificacion = models.TextField(verbose_name='Justificación del cambio')
	fecha_cambio = models.DateTimeField(auto_now_add=True)
	usuario_cambio = models.CharField(max_length=50, blank=True, null=True)
	referente = models.ForeignKey(
		ValReferenteCargaTemporal,
		on_delete=models.SET_NULL,
		null=True,
		blank=True,
		related_name='historial_matriculas_modificadas',
		verbose_name='Referente de Carga'
	)

	class Meta:
		db_table = '"validaciones_2026"."historial_matriculas"'
		ordering = ['-fecha_cambio']
		verbose_name = 'Historial de Matrícula'
		verbose_name_plural = 'Historial de Matrículas'

	def __str__(self):
		return f"Sección {self.seccion} | Anterior: {self.matricula_anterior} → Nueva: {self.matricula_nueva}"


class ValHistorialCambiosEstablecimiento(models.Model):
	"""
	Registra la justificación al validar la participación del establecimiento.
	"""
	establecimiento = models.ForeignKey(
		ValEstablecimiento,
		on_delete=models.CASCADE,
		related_name='historial_cambios',
		null=True,
		blank=True
	)
	justificacion = models.TextField(verbose_name='Justificación de participación')
	fecha = models.DateTimeField(auto_now_add=True)
	usuario = models.CharField(max_length=50, blank=True, null=True)
	referente = models.ForeignKey(
		ValReferenteCargaTemporal,
		on_delete=models.SET_NULL,
		null=True,
		blank=True,
		related_name='historial_establecimientos_modificados',
		verbose_name='Referente de Carga'
	)

	class Meta:
		db_table = '"validaciones_2026"."historial_cambios_establecimiento"'
		ordering = ['-fecha']
		verbose_name = 'Historial de Cambio de Establecimiento'
		verbose_name_plural = 'Historial de Cambios de Establecimiento'

	def __str__(self):
		return f"Establecimiento {self.establecimiento} validado — {self.fecha}"
