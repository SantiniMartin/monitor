import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'monitoreo.settings')
django.setup()

from django.db import connections

for db_name in connections:
    print(f"Checking DB: {db_name}")
    try:
        with connections[db_name].cursor() as c:
            c.execute("""
                SELECT n.nspname as schema, c.relname as relation, c.relkind
                FROM pg_class c
                JOIN pg_namespace n ON n.oid = c.relnamespace
                WHERE c.relname ILIKE '%trayectoria%'
            """)
            rows = c.fetchall()
            print(f"Relations in {db_name}: {rows}")
    except Exception as e:
        print(f"Error in {db_name}: {e}")
