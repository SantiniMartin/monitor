from django.db import migrations, models


RESPUESTA_CHOICES = [
    ('A', 'A'),
    ('B', 'B'),
    ('C', 'C'),
    ('D', 'D'),
    ('', 'Sin respuesta'),
]


class Migration(migrations.Migration):
    dependencies = [
        (
            'evaluaciones_educativas',
            '0003_alter_secciondiagnostico_ingreso_2026_unique_together_and_more',
        ),
    ]

    operations = [
        migrations.AddField(
            model_name='lecturaomr',
            name='tipo_examen',
            field=models.CharField(
                choices=[
                    ('lengua', 'Lengua'),
                    ('matematica', 'Matemática'),
                    ('contexto', 'Examen de contexto'),
                ],
                db_index=True,
                default='lengua',
                help_text='Tipo de examen asociado a la lectura OMR',
                max_length=12,
            ),
        ),
        *[
            migrations.AddField(
                model_name='lecturaomr',
                name=f'item_{numero}',
                field=models.CharField(
                    blank=True,
                    choices=RESPUESTA_CHOICES,
                    default='',
                    max_length=1,
                ),
            )
            for numero in range(13, 25)
        ],
    ]
