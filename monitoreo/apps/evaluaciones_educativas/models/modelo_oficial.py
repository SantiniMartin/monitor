from django.db import models
import uuid


#Desde septiembre del 2026 la lofica se cambia a consumir una vista materializada V_Trayectoria_Alumnos_SGE que nos envia estadisiticas, es decir que antes se realziaba modelos por opertaivos pero ahora vasmoa realziar solo vamos a realizar modelos de evaluaciones por operativos
# sineod cada evaluacionhija de el modelo evaluacion que esta realaizadona el oeprativo y qued recibe un alumno en datos completos 


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
    id_persona = models.IntegerField(null=True, blank=True)
    id_alumno = models.IntegerField(null=True, blank=True)
    id_alumno_inscripcion = models.IntegerField(null=True, blank=True)
    id_titulacion_unidad_servicio = models.IntegerField(null=True, blank=True)
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
        return f"{self.alumno or self.apellido or self.id}"


# =============================================================================
# Modelos del diagrama oficial de Evaluaciones Educativas
# =============================================================================

class Operativo(models.Model):
    """
    Representa un operativo de evaluación.
    Relación: 1 Operativo → n Evaluaciones.
    """
    tipo_operativo = models.CharField(max_length=100, null=True, blank=True)
    anio = models.IntegerField(null=True, blank=True, verbose_name="Año")
    mes = models.IntegerField(null=True, blank=True)

    # TODO: agregar campos adicionales según se definan

    class Meta:
        db_table = '"evaluaciones_educativas"."operativo"'
        verbose_name = "Operativo"
        verbose_name_plural = "Operativos"

    def __str__(self):
        return f"Operativo {self.tipo_operativo} - {self.anio}/{self.mes}"


class Evaluacion(models.Model):
    """
    Evaluación vinculada a un Operativo.
    Relación: n Evaluaciones → 1 Operativo (FK).
    Cada Evaluación puede tener una especialización exclusiva: Eval1 o Eva2.
    """
    operativo = models.ForeignKey(
        Operativo,
        on_delete=models.CASCADE,
        related_name="evaluaciones",
    )

    # TODO: definir campos (Item 1, Item 2, Item 3, etc.)

    class Meta:
        db_table = '"evaluaciones_educativas"."evaluacion"'
        verbose_name = "Evaluación"
        verbose_name_plural = "Evaluaciones"

    def __str__(self):
        return f"Evaluación #{self.pk} - Operativo {self.operativo_id}"


class DatosCompleto(models.Model):
    """
    Datos completos del alumno asociados a una evaluación.
    Relación: n DatosCompleto → 1 Evaluación (FK).
    """
    id_uuid_alumno = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True,
        verbose_name="UUID del alumno",
    )
    evaluacion = models.ForeignKey(
        Evaluacion,
        on_delete=models.CASCADE,
        related_name="datos_completos",
    )
    cueanexo_original = models.CharField(max_length=50, null=True, blank=True)
    cueanexo = models.CharField(max_length=50, null=True, blank=True)

    class Meta:
        db_table = '"evaluaciones_educativas"."datos_completo"'
        verbose_name = "Datos Completo"
        verbose_name_plural = "Datos Completos"

    def __str__(self):
        return f"DatosCompleto {self.id_uuid_alumno} - Eval #{self.evaluacion_id}"


class Fluidez_Lectora_Octubre_2026 (models.Model):
    """
    Subtipo exclusivo de Evaluación (especialización 1).
    Relación: 1:1 con Evaluación.
    """
    evaluacion = models.OneToOneField(
        Evaluacion,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name="fluidez_lectora_octubre_2026",
    )

    # TODO: definir campos (Item 1, Item 2, Item 3, etc.)

    class Meta:
        db_table = '"evaluaciones_educativas"."fluidez_lectora_octubre_2026"'
        verbose_name = "Fluidez Lectora Octubre 2026"
        verbose_name_plural = "Fluidez Lectora Octubre 2026"

    def __str__(self):
        return f"Fluidez Lectora Octubre 2026 - Evaluación #{self.evaluacion_id}"


class Diagnostico_Ingreso_Noviembre_2026(models.Model):
    """
    Subtipo exclusivo de Evaluación (especialización 2).
    Relación: 1:1 con Evaluación.
    """
    evaluacion = models.OneToOneField(
        Evaluacion,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name="diag_ing_nov_2026",
    )

    # TODO: definir campos (Item 1, Item 2, Item 3, etc.)

    class Meta:
        db_table = '"evaluaciones_educativas"."diag_ing_nov_2026"'
        verbose_name = "Diagnostico Ingreso Noviembre 2026"
        verbose_name_plural = "Diagnostico Ingreso Noviembre 2026"

    def __str__(self):
        return f"Diagnostico Ingreso Noviembre 2026 - Evaluación #{self.evaluacion_id}"

