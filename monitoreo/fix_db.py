import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'monitoreo.settings')
django.setup()

from django.db import connections

queries = [
    'ALTER TABLE "validaciones_2026"."establecimientos" ADD COLUMN "carga_completa" boolean DEFAULT false NOT NULL;',
    'ALTER TABLE "validaciones_2026"."establecimientos" ADD COLUMN "motivo_no_participa" character varying(150) NULL;',
    'ALTER TABLE "validaciones_2026"."grados" ADD COLUMN "grado_creado" boolean DEFAULT false NOT NULL;',
    'ALTER TABLE "validaciones_2026"."secciones" ADD COLUMN "motivo_deshabilitacion" character varying(150) NULL;',
    'ALTER TABLE "validaciones_2026"."secciones" ADD COLUMN "seccion_creada" boolean DEFAULT false NOT NULL;'
]

with connections['Evaluacion'].cursor() as cursor:
    for q in queries:
        try:
            cursor.execute(q)
            print("OK:", q)
        except Exception as e:
            print("ERROR:", q)
            print(e)
