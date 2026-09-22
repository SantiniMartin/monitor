from django.db import migrations, models
import django.db.models.deletion


DATABASE_SQL = r'''
ALTER TABLE datos_oficiales.operativo
    ALTER COLUMN tipo_operativo SET NOT NULL,
    ALTER COLUMN anio SET NOT NULL,
    ALTER COLUMN mes SET NOT NULL;
ALTER TABLE datos_oficiales.operativo
    ADD CONSTRAINT operativo_mes_valido CHECK (mes BETWEEN 1 AND 12);
ALTER TABLE datos_oficiales.operativo
    ADD CONSTRAINT operativo_tipo_anio_mes_uniq
    UNIQUE (tipo_operativo, anio, mes);

ALTER TABLE datos_oficiales.evaluacion
    ADD COLUMN tipo_evaluacion varchar(20);
ALTER TABLE datos_oficiales.evaluacion
    ADD CONSTRAINT evaluacion_tipo_valido
    CHECK (tipo_evaluacion IN ('lengua', 'matematica', 'contexto'));
ALTER TABLE datos_oficiales.evaluacion
    ADD CONSTRAINT evaluacion_operativo_tipo_uniq
    UNIQUE (operativo_id, tipo_evaluacion);
ALTER TABLE datos_oficiales.evaluacion
    ALTER COLUMN tipo_evaluacion SET NOT NULL;

ALTER TABLE datos_oficiales.datos_completo
    DROP CONSTRAINT IF EXISTS datos_completo_id_uuid_alumno_key;
ALTER TABLE datos_oficiales.datos_completo
    ALTER COLUMN id_uuid_alumno TYPE varchar(255)
    USING id_uuid_alumno::text;
ALTER TABLE datos_oficiales.datos_completo
    ALTER COLUMN cueanexo_original SET NOT NULL;
ALTER TABLE datos_oficiales.datos_completo
    ADD CONSTRAINT datos_completo_alumno_evaluacion_uniq
    UNIQUE (id_uuid_alumno, evaluacion_id);

INSERT INTO datos_oficiales.operativo (tipo_operativo, anio, mes)
VALUES ('diagnostico_ingreso_2026', 2026, 9)
ON CONFLICT (tipo_operativo, anio, mes) DO NOTHING;

INSERT INTO datos_oficiales.evaluacion (operativo_id, tipo_evaluacion)
SELECT operativo.id, tipo.tipo_evaluacion
FROM datos_oficiales.operativo AS operativo
CROSS JOIN (
    VALUES ('lengua'), ('matematica'), ('contexto')
) AS tipo(tipo_evaluacion)
WHERE operativo.tipo_operativo = 'diagnostico_ingreso_2026'
  AND operativo.anio = 2026
  AND operativo.mes = 9
ON CONFLICT (operativo_id, tipo_evaluacion) DO NOTHING;

CREATE TABLE datos_oficiales.examen_matematica_diagnostico_ingreso_2026 (
    id bigserial PRIMARY KEY,
    public_id uuid NOT NULL UNIQUE,
    alumno_id bigint NOT NULL UNIQUE,
    evaluacion_id bigint NOT NULL,
    tipo_examen varchar(12) NOT NULL DEFAULT 'matematica',
    modelo_examen varchar(1) NOT NULL DEFAULT '',
    fecha_lectura timestamp with time zone NOT NULL,
    encargado_carga varchar(9) NOT NULL DEFAULT '',
    item_1 varchar(1) NOT NULL DEFAULT '', item_2 varchar(1) NOT NULL DEFAULT '',
    item_3 varchar(1) NOT NULL DEFAULT '', item_4 varchar(1) NOT NULL DEFAULT '',
    item_5 varchar(1) NOT NULL DEFAULT '', item_6 varchar(1) NOT NULL DEFAULT '',
    item_7 varchar(1) NOT NULL DEFAULT '', item_8 varchar(1) NOT NULL DEFAULT '',
    item_9 varchar(1) NOT NULL DEFAULT '', item_10 varchar(1) NOT NULL DEFAULT '',
    item_11 varchar(1) NOT NULL DEFAULT '', item_12 varchar(1) NOT NULL DEFAULT '',
    item_13 varchar(1) NOT NULL DEFAULT '', item_14 varchar(1) NOT NULL DEFAULT '',
    item_15 varchar(1) NOT NULL DEFAULT '', item_16 varchar(1) NOT NULL DEFAULT '',
    item_17 varchar(1) NOT NULL DEFAULT '', item_18 varchar(1) NOT NULL DEFAULT '',
    item_19 varchar(1) NOT NULL DEFAULT '', item_20 varchar(1) NOT NULL DEFAULT '',
    item_21 varchar(1) NOT NULL DEFAULT '', item_22 varchar(1) NOT NULL DEFAULT '',
    item_23 varchar(1) NOT NULL DEFAULT '', item_24 varchar(1) NOT NULL DEFAULT '',
    confianza_json jsonb NULL,
    revisado_manualmente boolean NOT NULL DEFAULT false,
    CONSTRAINT examen_matematica_datos_fk FOREIGN KEY (alumno_id)
        REFERENCES datos_oficiales.datos_completo(id) ON DELETE RESTRICT,
    CONSTRAINT examen_matematica_evaluacion_fk FOREIGN KEY (evaluacion_id)
        REFERENCES datos_oficiales.evaluacion(id) ON DELETE RESTRICT
);
CREATE INDEX examen_matematica_tipo_idx
    ON datos_oficiales.examen_matematica_diagnostico_ingreso_2026(tipo_examen);
CREATE INDEX examen_matematica_evaluacion_idx
    ON datos_oficiales.examen_matematica_diagnostico_ingreso_2026(evaluacion_id);

CREATE TABLE datos_oficiales.examen_lengua_diagnostico_ingreso_2026 (
    id bigserial PRIMARY KEY,
    public_id uuid NOT NULL UNIQUE,
    alumno_id bigint NOT NULL UNIQUE,
    evaluacion_id bigint NOT NULL,
    modelo_examen varchar(1) NOT NULL,
    fecha_lectura timestamp with time zone NOT NULL,
    encargado_carga varchar(9) NOT NULL DEFAULT '',
    item_1 varchar(1) NOT NULL DEFAULT '', item_2 varchar(1) NOT NULL DEFAULT '',
    item_3 varchar(1) NOT NULL DEFAULT '', item_4 varchar(1) NOT NULL DEFAULT '',
    item_5 varchar(1) NOT NULL DEFAULT '', item_6 varchar(1) NOT NULL DEFAULT '',
    item_7 varchar(1) NOT NULL DEFAULT '', item_8 varchar(1) NOT NULL DEFAULT '',
    item_9 varchar(1) NOT NULL DEFAULT '', item_10 varchar(1) NOT NULL DEFAULT '',
    item_11 varchar(1) NOT NULL DEFAULT '', item_12 varchar(1) NOT NULL DEFAULT '',
    item_13 varchar(1) NOT NULL DEFAULT '', item_14 varchar(1) NOT NULL DEFAULT '',
    item_15 varchar(1) NOT NULL DEFAULT '', item_16 varchar(1) NOT NULL DEFAULT '',
    item_17 varchar(1) NOT NULL DEFAULT '', item_18 varchar(1) NOT NULL DEFAULT '',
    item_19 varchar(1) NOT NULL DEFAULT '', item_20 varchar(1) NOT NULL DEFAULT '',
    item_21 varchar(1) NOT NULL DEFAULT '', item_22 varchar(1) NOT NULL DEFAULT '',
    item_23 varchar(1) NOT NULL DEFAULT '', item_24 varchar(1) NOT NULL DEFAULT '',
    item_24_1 varchar(1) NOT NULL DEFAULT '',
    item_24_2 varchar(1) NOT NULL DEFAULT '',
    item_24_3 varchar(1) NOT NULL DEFAULT '',
    confianza_json jsonb NULL,
    puntajes_json jsonb NOT NULL DEFAULT '{}'::jsonb,
    puntaje_total numeric(6,2) NOT NULL DEFAULT 0,
    revisado_manualmente boolean NOT NULL DEFAULT false,
    CONSTRAINT examen_lengua_datos_fk FOREIGN KEY (alumno_id)
        REFERENCES datos_oficiales.datos_completo(id) ON DELETE RESTRICT,
    CONSTRAINT examen_lengua_evaluacion_fk FOREIGN KEY (evaluacion_id)
        REFERENCES datos_oficiales.evaluacion(id) ON DELETE RESTRICT
);
CREATE INDEX examen_lengua_evaluacion_idx
    ON datos_oficiales.examen_lengua_diagnostico_ingreso_2026(evaluacion_id);

CREATE TABLE datos_oficiales.examen_contexto_diagnostico_ingreso_2026 (
    id bigserial PRIMARY KEY,
    public_id uuid NOT NULL UNIQUE,
    alumno_id bigint NOT NULL UNIQUE,
    evaluacion_id bigint NOT NULL,
    fecha_lectura timestamp with time zone NOT NULL,
    encargado_carga varchar(9) NOT NULL DEFAULT '',
    item_1 varchar(11) NOT NULL DEFAULT '', item_2 varchar(1) NOT NULL DEFAULT '',
    item_3 varchar(1) NOT NULL DEFAULT '', item_4 varchar(11) NOT NULL DEFAULT '',
    item_5 varchar(1) NOT NULL DEFAULT '', item_6 varchar(1) NOT NULL DEFAULT '',
    item_7 varchar(11) NOT NULL DEFAULT '', item_8 varchar(11) NOT NULL DEFAULT '',
    item_9 varchar(1) NOT NULL DEFAULT '', item_10 varchar(1) NOT NULL DEFAULT '',
    item_11 varchar(1) NOT NULL DEFAULT '', item_12 varchar(1) NOT NULL DEFAULT '',
    item_13 varchar(1) NOT NULL DEFAULT '', item_14 varchar(11) NOT NULL DEFAULT '',
    item_15 varchar(1) NOT NULL DEFAULT '', item_16 varchar(1) NOT NULL DEFAULT '',
    item_17 varchar(1) NOT NULL DEFAULT '',
    confianza_json jsonb NULL,
    revisado_manualmente boolean NOT NULL DEFAULT false,
    CONSTRAINT examen_contexto_datos_fk FOREIGN KEY (alumno_id)
        REFERENCES datos_oficiales.datos_completo(id) ON DELETE RESTRICT,
    CONSTRAINT examen_contexto_evaluacion_fk FOREIGN KEY (evaluacion_id)
        REFERENCES datos_oficiales.evaluacion(id) ON DELETE RESTRICT
);
CREATE INDEX examen_contexto_evaluacion_idx
    ON datos_oficiales.examen_contexto_diagnostico_ingreso_2026(evaluacion_id);
'''


class Migration(migrations.Migration):
    atomic = True

    dependencies = [
        ('evaluaciones_educativas', '0008_examenlengua'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(DATABASE_SQL, reverse_sql=migrations.RunSQL.noop),
            ],
            state_operations=[
                migrations.CreateModel(
                    name='Operativo',
                    fields=[
                        ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                        ('tipo_operativo', models.CharField(max_length=100)),
                        ('anio', models.PositiveSmallIntegerField()),
                        ('mes', models.PositiveSmallIntegerField()),
                    ],
                    options={
                        'db_table': '"datos_oficiales"."operativo"',
                        'managed': False,
                        'constraints': [models.UniqueConstraint(fields=('tipo_operativo', 'anio', 'mes'), name='operativo_tipo_anio_mes_uniq')],
                    },
                ),
                migrations.CreateModel(
                    name='Evaluacion',
                    fields=[
                        ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                        ('tipo_evaluacion', models.CharField(choices=[('lengua', 'Lengua'), ('matematica', 'Matemática'), ('contexto', 'Contexto')], max_length=20)),
                        ('operativo', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='evaluaciones', to='evaluaciones_educativas.operativo')),
                    ],
                    options={
                        'db_table': '"datos_oficiales"."evaluacion"',
                        'managed': False,
                        'constraints': [models.UniqueConstraint(fields=('operativo', 'tipo_evaluacion'), name='evaluacion_operativo_tipo_uniq')],
                    },
                ),
                migrations.CreateModel(
                    name='DatosCompleto',
                    fields=[
                        ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                        ('id_uuid_alumno', models.CharField(max_length=255)),
                        ('cueanexo_original', models.CharField(max_length=50)),
                        ('cueanexo', models.CharField(blank=True, max_length=50, null=True)),
                        ('evaluacion', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='alumnos', to='evaluaciones_educativas.evaluacion')),
                    ],
                    options={
                        'db_table': '"datos_oficiales"."datos_completo"',
                        'managed': False,
                        'constraints': [models.UniqueConstraint(fields=('id_uuid_alumno', 'evaluacion'), name='datos_completo_alumno_evaluacion_uniq')],
                    },
                ),
                migrations.RemoveField(model_name='examenmatematica', name='observaciones'),
                migrations.RemoveField(model_name='examenlengua', name='observaciones'),
                migrations.RemoveField(model_name='examencontexto', name='observaciones'),
                migrations.AlterField(
                    model_name='examenmatematica',
                    name='alumno',
                    field=models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name='examenes_matematica', to='evaluaciones_educativas.datoscompleto'),
                ),
                migrations.AlterField(
                    model_name='examenlengua',
                    name='alumno',
                    field=models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name='examenes_lengua', to='evaluaciones_educativas.datoscompleto'),
                ),
                migrations.AlterField(
                    model_name='examencontexto',
                    name='alumno',
                    field=models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name='examenes_contexto', to='evaluaciones_educativas.datoscompleto'),
                ),
                migrations.AlterField(
                    model_name='examenmatematica',
                    name='tipo_examen',
                    field=models.CharField(choices=[('lengua', 'Lengua'), ('matematica', 'Matemática'), ('contexto', 'Examen de contexto')], db_index=True, default='matematica', help_text='Tipo de examen asociado a la lectura OMR', max_length=12),
                ),
                migrations.AddField(
                    model_name='examenmatematica',
                    name='evaluacion',
                    field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='resultados_matematica', to='evaluaciones_educativas.evaluacion'),
                ),
                migrations.AddField(
                    model_name='examenlengua',
                    name='evaluacion',
                    field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='resultados_lengua', to='evaluaciones_educativas.evaluacion'),
                ),
                migrations.AddField(
                    model_name='examencontexto',
                    name='evaluacion',
                    field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='resultados_contexto', to='evaluaciones_educativas.evaluacion'),
                ),
                migrations.AlterModelTable(
                    name='examenmatematica',
                    table='"datos_oficiales"."examen_matematica_diagnostico_ingreso_2026"',
                ),
                migrations.AlterModelTable(
                    name='examenlengua',
                    table='"datos_oficiales"."examen_lengua_diagnostico_ingreso_2026"',
                ),
                migrations.AlterModelTable(
                    name='examencontexto',
                    table='"datos_oficiales"."examen_contexto_diagnostico_ingreso_2026"',
                ),
            ],
        ),
    ]
