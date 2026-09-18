from decimal import Decimal
import uuid

import django.db.models.deletion
from django.db import migrations, models


OPCIONES_RESPUESTA = [
    ("A", "A"),
    ("B", "B"),
    ("C", "C"),
    ("D", "D"),
    ("", "Sin respuesta"),
]


class Migration(migrations.Migration):
    dependencies = [
        ("evaluaciones_educativas", "0007_rename_lecturas_to_examenes_matematica"),
    ]

    operations = [
        migrations.CreateModel(
            name="ExamenLengua",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "public_id",
                    models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
                ),
                (
                    "modelo_examen",
                    models.CharField(
                        choices=[("A", "Modelo A"), ("B", "Modelo B")],
                        max_length=1,
                    ),
                ),
                ("fecha_lectura", models.DateTimeField(auto_now_add=True)),
                (
                    "encargado_carga",
                    models.CharField(
                        blank=True,
                        help_text="Cuil/ID del docente que realizó la carga",
                        max_length=9,
                    ),
                ),
                *[
                    (
                        f"item_{numero}",
                        models.CharField(
                            blank=True,
                            choices=OPCIONES_RESPUESTA,
                            default="",
                            max_length=1,
                        ),
                    )
                    for numero in range(1, 25)
                ],
                *[
                    (
                        f"item_24_{numero}",
                        models.CharField(
                            blank=True,
                            choices=OPCIONES_RESPUESTA,
                            default="",
                            max_length=1,
                        ),
                    )
                    for numero in range(1, 4)
                ],
                ("confianza_json", models.JSONField(blank=True, null=True)),
                ("puntajes_json", models.JSONField(blank=True, default=dict)),
                (
                    "puntaje_total",
                    models.DecimalField(
                        decimal_places=2,
                        default=Decimal("0"),
                        max_digits=6,
                    ),
                ),
                ("revisado_manualmente", models.BooleanField(default=False)),
                ("observaciones", models.TextField(blank=True, default="")),
                (
                    "alumno",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="examenes_lengua",
                        to="evaluaciones_educativas.alumnodiagnostico_ingreso_2026",
                    ),
                ),
            ],
            options={
                "verbose_name": "Examen de Lengua",
                "verbose_name_plural": "Exámenes de Lengua",
                "db_table": '"diagnostico_ingreso_2026"."examenes_lengua"',
                "ordering": ["-fecha_lectura"],
            },
        ),
    ]
