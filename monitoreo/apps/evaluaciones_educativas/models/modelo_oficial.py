from django.db import models

class V_Trayectoria_Alumnos_SGE(models.Model):
    # En la imagen 'id' figura con icono de texto (AZ), por lo que se define como CharField primary_key.
    # Si en tu base de datos fuera numérico autoincremental, cámbialo por: models.BigAutoField(primary_key=True)
    id = models.CharField(max_length=255, primary_key=True)

    # Ciclo lectivo
    c_ciclo_lectivo = models.IntegerField(null=True, blank=True)
    anio_ciclo = models.IntegerField(null=True, blank=True)
    ciclo_lectivo = models.CharField(max_length=100, null=True, blank=True)

    # Nivel / Institución
    c_nivel_servicio = models.IntegerField(null=True, blank=True)
    nivel = models.CharField(max_length=150, null=True, blank=True)
    id_unidad_servicio = models.IntegerField(null=True, blank=True)
    id_institucion = models.IntegerField(null=True, blank=True)
    cueanexo = models.CharField(max_length=50, null=True, blank=True)
    escuela = models.CharField(max_length=255, null=True, blank=True)

    # Sección / Turno
    c_grado_nivel_servicio = models.IntegerField(null=True, blank=True)
    anio_grado = models.CharField(max_length=100, null=True, blank=True)
    id_seccion = models.IntegerField(null=True, blank=True)
    nombre_seccion = models.CharField(max_length=150, null=True, blank=True)
    c_tipo_seccion = models.IntegerField(null=True, blank=True)
    tipo_seccion = models.CharField(max_length=150, null=True, blank=True)
    c_turno = models.IntegerField(null=True, blank=True)
    turno = models.CharField(max_length=100, null=True, blank=True)

    # Alumno / Persona
    #id_persona = models.IntegerField(null=True, blank=True)
    id_alumno = models.IntegerField(null=True, blank=True)
    #id_alumno_inscripcion = models.IntegerField(null=True, blank=True)
    #id_titulacion_unidad_servicio = models.IntegerField(null=True, blank=True)
    numero_documento = models.CharField(max_length=50, null=True, blank=True)
    cuil = models.CharField(max_length=50, null=True, blank=True)
    apellido = models.CharField(max_length=150, null=True, blank=True)
    nombre = models.CharField(max_length=150, null=True, blank=True)
    alumno = models.CharField(max_length=255, null=True, blank=True)
    comunidad_indigena = models.CharField(max_length=100, null=True, blank=True)
    discapacidad = models.CharField(max_length=100, null=True, blank=True)

    # Inscripción
    c_estado_inscripcion = models.IntegerField(null=True, blank=True)
    fecha_insc = models.DateField(null=True, blank=True)  # Si tiene hora usa DateTimeField
    anio_ingreso = models.IntegerField(null=True, blank=True)

    # Ubicación
    region_loc = models.CharField(max_length=150, null=True, blank=True)
    sector = models.CharField(max_length=150, null=True, blank=True)
    ambito = models.CharField(max_length=150, null=True, blank=True)
    departamento = models.CharField(max_length=150, null=True, blank=True)
    localidad = models.CharField(max_length=150, null=True, blank=True)

    class Meta:
        managed = False
        # Si está en el esquema 'public' de PostgreSQL:
        db_table = '"public"."trayectoria_alumnos_sge"'
        verbose_name = "Trayectoria Alumno SGE"
        verbose_name_plural = "Trayectorias Alumnos SGE"

    def __str__(self):
        return f"{self.alumno } {self.cueanexo } - {self.anio_grado}"