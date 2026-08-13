"""
Script de migración manual para aplicar los cambios del 0003 a la BD Evaluacion.
Ejecutar con: python fix_migration.py
"""
import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'monitoreo.settings')
django.setup()

from django.db import connections

SQL = """
ALTER TABLE "validaciones_2026"."establecimientos"
  ADD COLUMN IF NOT EXISTS "cabecera_id" bigint NULL
  CONSTRAINT "establecimientos_cabecera_id_deed40db_fk_cabeceras_id"
  REFERENCES "validaciones_2026"."cabeceras"("id") DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE "validaciones_2026"."establecimientos"
  ADD COLUMN IF NOT EXISTS "participa_aprender" boolean NULL;

ALTER TABLE "validaciones_2026"."secciones"
  ALTER COLUMN "estado_validacion" TYPE varchar(13);

CREATE INDEX IF NOT EXISTS "establecimientos_cabecera_id_deed40db"
  ON "validaciones_2026"."establecimientos" ("cabecera_id");
"""

with connections['Evaluacion'].cursor() as cursor:
    cursor.execute(SQL)
    print("OK - Migracion aplicada correctamente a la BD Evaluacion.")
