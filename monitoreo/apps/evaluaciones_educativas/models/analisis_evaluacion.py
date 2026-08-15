from django.db import models


class ExamenLenguaAlumno(models.Model):
    """
    Modelo de solo lectura que mapea la tabla `examen_lengua_alumnos`.
    Campos de capacidad ya calculados: extraer, interpretar, reflexionar_evaluar, Escribir.
    """
    cueanexo    = models.CharField(max_length=128, null=True, blank=True)
    escuela     = models.CharField(max_length=128, null=True, blank=True)
    ambito      = models.CharField(max_length=128, null=True, blank=True)
    sector      = models.CharField(max_length=128, null=True, blank=True)
    localidad   = models.CharField(max_length=128, null=True, blank=True)
    departamento= models.CharField(max_length=128, null=True, blank=True)
    dni         = models.CharField(max_length=128, primary_key=True)
    apellidos   = models.CharField(max_length=128, null=True, blank=True)
    nombres     = models.CharField(max_length=128, null=True, blank=True)
    anio        = models.CharField(max_length=128, null=True, blank=True)
    division    = models.CharField(max_length=128, null=True, blank=True)
    region      = models.CharField(max_length=128, null=True, blank=True)
    # Preguntas — Extraer: p6, p11, p13, p15
    p1          = models.CharField(max_length=128, null=True, blank=True)
    p2          = models.CharField(max_length=128, null=True, blank=True)
    p3          = models.CharField(max_length=128, null=True, blank=True)
    p4          = models.CharField(max_length=128, null=True, blank=True)
    p5          = models.CharField(max_length=128, null=True, blank=True)
    p6          = models.CharField(max_length=128, null=True, blank=True)
    p7          = models.CharField(max_length=128, null=True, blank=True)
    p8          = models.CharField(max_length=128, null=True, blank=True)
    p9          = models.CharField(max_length=128, null=True, blank=True)
    p10         = models.CharField(max_length=128, null=True, blank=True)
    p11         = models.CharField(max_length=128, null=True, blank=True)
    p12         = models.CharField(max_length=128, null=True, blank=True)
    p13         = models.CharField(max_length=128, null=True, blank=True)
    p14         = models.CharField(max_length=128, null=True, blank=True)
    p15         = models.CharField(max_length=128, null=True, blank=True)
    p16         = models.CharField(max_length=128, null=True, blank=True)
    # Totales
    total               = models.CharField(max_length=128, null=True, blank=True)
    extraer             = models.CharField(max_length=128, null=True, blank=True)
    interpretar         = models.CharField(max_length=128, null=True, blank=True)
    reflexionar_evaluar = models.CharField(max_length=128, null=True, blank=True)
    # Columna con mayúscula en la BD
    escribir            = models.CharField(max_length=128, null=True, blank=True, db_column='Escribir')
    discapacidad        = models.CharField(max_length=128, null=True, blank=True)
    etnia               = models.CharField(max_length=128, null=True, blank=True)

    class Meta:
        managed  = False
        db_table = '"diagnostico_2026"."examen_lengua_alumnos"'

    def __str__(self):
        return f"{self.apellidos}, {self.nombres} – DNI: {self.dni}"


class ExamenMatematicaAlumno(models.Model):
    """
    Modelo de solo lectura que mapea la tabla `examen_matematica_alumnos`.
    Campos de capacidad ya calculados: reconocimiento_conceptos, comunicacion, resolucion_situaciones.

    Composición de capacidades:
      Reconocimiento: p3, p7, p10
      Comunicación:   p2, p6, p8, p12, p14
      Resolución:     p1, p4, p5, p9, p11, p13
    """
    cueanexo    = models.CharField(max_length=128, null=True, blank=True)
    escuela     = models.CharField(max_length=128, null=True, blank=True)
    ambito      = models.CharField(max_length=128, null=True, blank=True)
    sector      = models.CharField(max_length=128, null=True, blank=True)
    localidad   = models.CharField(max_length=128, null=True, blank=True)
    departamento= models.CharField(max_length=128, null=True, blank=True)
    dni         = models.CharField(max_length=128, primary_key=True)
    apellidos   = models.CharField(max_length=128, null=True, blank=True)
    nombres     = models.CharField(max_length=128, null=True, blank=True)
    anio        = models.CharField(max_length=128, null=True, blank=True)
    division    = models.CharField(max_length=128, null=True, blank=True)
    region      = models.CharField(max_length=128, null=True, blank=True)
    p1          = models.CharField(max_length=50, null=True, blank=True)
    p2          = models.CharField(max_length=50, null=True, blank=True)
    p3          = models.CharField(max_length=50, null=True, blank=True)
    p4          = models.CharField(max_length=50, null=True, blank=True)
    p5          = models.CharField(max_length=50, null=True, blank=True)
    p6          = models.CharField(max_length=50, null=True, blank=True)
    p7          = models.CharField(max_length=50, null=True, blank=True)
    p8          = models.CharField(max_length=50, null=True, blank=True)
    p9          = models.CharField(max_length=50, null=True, blank=True)
    p10         = models.CharField(max_length=50, null=True, blank=True)
    p11         = models.CharField(max_length=50, null=True, blank=True)
    p12         = models.CharField(max_length=50, null=True, blank=True)
    p13         = models.CharField(max_length=50, null=True, blank=True)
    p14         = models.CharField(max_length=50, null=True, blank=True)
    # Totales
    total                    = models.CharField(max_length=50, null=True, blank=True)
    reconocimiento_conceptos = models.CharField(max_length=50, null=True, blank=True)
    comunicacion             = models.CharField(max_length=50, null=True, blank=True)
    resolucion_situaciones   = models.CharField(max_length=50, null=True, blank=True)
    discapacidad             = models.CharField(max_length=50, null=True, blank=True)
    etnia                    = models.CharField(max_length=50, null=True, blank=True)

    class Meta:
        managed  = False
        db_table = '"diagnostico_2026"."examen_matematica_alumnos"'

    def __str__(self):
        return f"{self.apellidos}, {self.nombres} – DNI: {self.dni}"
