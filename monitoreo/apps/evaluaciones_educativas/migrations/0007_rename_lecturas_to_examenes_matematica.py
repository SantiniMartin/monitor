from django.db import migrations


def asegurar_tabla_matematica(apps, schema_editor):
    """Crea la tabla si la historia estaba aplicada pero nunca se materializó."""
    model = apps.get_model("evaluaciones_educativas", "ExamenMatematica")
    connection = schema_editor.connection
    if connection.vendor == "postgresql":
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT 1
                FROM information_schema.tables
                WHERE table_schema = %s AND table_name = %s
                """,
                ["diagnostico_ingreso_2026", "examenes_matematica"],
            )
            exists = cursor.fetchone() is not None
    else:
        with connection.cursor() as cursor:
            exists = "examenes_matematica" in connection.introspection.table_names(cursor)
    if not exists:
        schema_editor.create_model(model)


class Migration(migrations.Migration):
    dependencies = [
        (
            "evaluaciones_educativas",
            "0006_examencontexto_cardinalidad_items",
        ),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql="""
                        ALTER TABLE IF EXISTS
                            "diagnostico_ingreso_2026"."lecturas"
                        RENAME TO "examenes_matematica";
                    """,
                    reverse_sql="""
                        ALTER TABLE IF EXISTS
                            "diagnostico_ingreso_2026"."examenes_matematica"
                        RENAME TO "lecturas";
                    """,
                ),
            ],
            state_operations=[
                migrations.AlterModelTable(
                    name="examenmatematica",
                    table='"diagnostico_ingreso_2026"."examenes_matematica"',
                ),
            ],
        ),
        migrations.RunPython(
            asegurar_tabla_matematica,
            migrations.RunPython.noop,
        ),
    ]
