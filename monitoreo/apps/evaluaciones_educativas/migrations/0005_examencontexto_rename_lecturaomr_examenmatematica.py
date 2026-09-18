import django.db.models.deletion
import uuid

from django.db import migrations, models


def columnas_tabla(schema_editor, model):
    """Obtiene las columnas reales sin confiar solo en django_migrations."""
    connection = schema_editor.connection
    qualified_name = model._meta.db_table.replace('"', '')
    name_parts = qualified_name.split('.', 1)
    schema_name, table_name = (
        name_parts if len(name_parts) == 2 else ('public', name_parts[0])
    )
    if connection.vendor == "postgresql":
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = %s AND table_name = %s
                """,
                [schema_name, table_name],
            )
            available_columns = {row[0] for row in cursor.fetchall()}
    else:
        with connection.cursor() as cursor:
            table_names = connection.introspection.table_names(cursor)
            if table_name not in table_names:
                return set()
            description = connection.introspection.get_table_description(
                cursor, table_name,
            )
            available_columns = {column.name for column in description}

    return available_columns


def copiar_contextos_existentes(apps, schema_editor):
    """Conserva lecturas de Contexto creadas antes de separar los modelos."""
    # Algunas bases tienen el historial 0001-0004, pero las tablas de este
    # esquema nunca fueron materializadas. Se reparan primero las dependencias
    # mínimas, sin tocar las que ya existen ni borrar datos.
    for model_name in (
        "EstablecimientosDiagnostico_Ingreso_2026",
        "GradoDiagnostico_Ingreso_2026",
        "SeccionDiagnostico_Ingreso_2026",
        "AlumnoDiagnostico_Ingreso_2026",
    ):
        dependency_model = apps.get_model("evaluaciones_educativas", model_name)
        if not columnas_tabla(schema_editor, dependency_model):
            schema_editor.create_model(dependency_model)

    examen_matematica = apps.get_model("evaluaciones_educativas", "ExamenMatematica")
    examen_contexto = apps.get_model("evaluaciones_educativas", "ExamenContexto")
    available_columns = columnas_tabla(schema_editor, examen_matematica)
    if not available_columns:
        # La historia de migraciones puede provenir de una instalación donde
        # esta tabla nunca llegó a materializarse. Se crea con el estado actual
        # para que Matemática y Contexto puedan persistir normalmente.
        schema_editor.create_model(examen_matematica)
        return
    required_columns = {
        field.column for field in examen_matematica._meta.local_concrete_fields
    }
    if not required_columns.issubset(available_columns):
        # Una tabla parcial no es una fuente segura para la copia opcional.
        return
    database = schema_editor.connection.alias
    nuevos = []
    fechas = {}
    for lectura in examen_matematica.objects.using(database).filter(tipo_examen="contexto").iterator():
        values = {
            "public_id": lectura.public_id,
            "alumno_id": lectura.alumno_id,
            "encargado_carga": lectura.encargado_carga,
            "confianza_json": lectura.confianza_json,
            "revisado_manualmente": lectura.revisado_manualmente,
            "observaciones": lectura.observaciones,
        }
        values.update({f"item_{numero}": getattr(lectura, f"item_{numero}") for numero in range(1, 18)})
        nuevos.append(examen_contexto(**values))
        fechas[lectura.public_id] = lectura.fecha_lectura
    if nuevos:
        examen_contexto.objects.using(database).bulk_create(nuevos, batch_size=500)
        for nuevo in nuevos:
            nuevo.fecha_lectura = fechas[nuevo.public_id]
        examen_contexto.objects.using(database).bulk_update(
            nuevos, ["fecha_lectura"], batch_size=500,
        )


class Migration(migrations.Migration):
    dependencies = [
        (
            "evaluaciones_educativas",
            "0004_lectura_omr_matematica_24_items",
        ),
    ]

    operations = [
        migrations.RenameModel(
            old_name="LecturaOMR",
            new_name="ExamenMatematica",
        ),
        migrations.AlterModelOptions(
            name="examenmatematica",
            options={
                "ordering": ["-fecha_lectura"],
                "verbose_name": "Examen de Matemática",
                "verbose_name_plural": "Exámenes de Matemática",
            },
        ),
        migrations.AlterField(
            model_name="examenmatematica",
            name="alumno",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="examenes_matematica",
                to="evaluaciones_educativas.alumnodiagnostico_ingreso_2026",
            ),
        ),
        migrations.CreateModel(
            name="ExamenContexto",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("fecha_lectura", models.DateTimeField(auto_now_add=True)),
                ("encargado_carga", models.CharField(blank=True, help_text="Cuil/ID del docente que realizó la carga", max_length=9)),
                *[
                    (f"item_{numero}", models.CharField(blank=True, default="", max_length=11))
                    for numero in range(1, 18)
                ],
                ("confianza_json", models.JSONField(blank=True, help_text="Nivel de confianza de la detección OMR por pregunta (0-100)", null=True)),
                ("revisado_manualmente", models.BooleanField(default=False)),
                ("observaciones", models.TextField(blank=True, default="")),
                (
                    "alumno",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="examenes_contexto",
                        to="evaluaciones_educativas.alumnodiagnostico_ingreso_2026",
                    ),
                ),
            ],
            options={
                "verbose_name": "Examen de Contexto",
                "verbose_name_plural": "Exámenes de Contexto",
                "db_table": '"diagnostico_ingreso_2026"."examenes_contexto"',
                "ordering": ["-fecha_lectura"],
            },
        ),
        migrations.RunPython(copiar_contextos_existentes, migrations.RunPython.noop),
    ]
