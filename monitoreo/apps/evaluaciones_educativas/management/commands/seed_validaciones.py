"""
Comando de management para cargar datos de prueba en validaciones_2026.

Uso:
    python manage.py seed_validaciones --cuil=27123456789
    python manage.py seed_validaciones  (usa el CUIL por defecto: 27999999999)
    python manage.py seed_validaciones --limpiar  (borra y recarga todo)
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.evaluaciones_educativas.models.validaciones_2026 import (
    ValReferenteCargaTemporal,
    ValEstablecimiento,
    ValGrado,
    ValCabecera,
    ValSeccion,
    ValHistorialMatriculas,
    ValHistorialCambiosEstablecimiento,
)


class Command(BaseCommand):
    help = 'Carga datos de prueba para el modulo validaciones_2026'

    def add_arguments(self, parser):
        parser.add_argument(
            '--cuil',
            type=str,
            default='27999999999',
            help='CUIL del referente de prueba. Default: 27999999999',
        )
        parser.add_argument(
            '--limpiar',
            action='store_true',
            help='Borra todos los datos existentes antes de cargar los nuevos.',
        )

    def handle(self, *args, **options):
        cuil = options['cuil']
        limpiar = options['limpiar']

        self.stdout.write(self.style.NOTICE('\n[SEED] Iniciando carga de datos de prueba para validaciones_2026...'))
        self.stdout.write(f'   CUIL del referente: {cuil}')

        with transaction.atomic():
            if limpiar:
                self.stdout.write(self.style.WARNING('   [!] Limpiando datos existentes...'))
                ValHistorialCambiosEstablecimiento.objects.all().delete()
                ValHistorialMatriculas.objects.all().delete()
                ValSeccion.objects.all().delete()
                ValGrado.objects.all().delete()
                ValEstablecimiento.objects.all().delete()
                ValReferenteCargaTemporal.objects.all().delete()
                ValCabecera.objects.all().delete()
                self.stdout.write(self.style.WARNING('   [OK] Limpieza completa.'))

            # 1. REFERENTE DE CARGA
            region_prueba = 'REGION 1'

            ref, created = ValReferenteCargaTemporal.objects.get_or_create(
                cuil=cuil,
                region=region_prueba,
                defaults={
                    'nombre': 'Juan',
                    'apellido': 'Perez Prueba',
                }
            )
            self.stdout.write(f'   {"[+] Creado" if created else "[=] Ya existe"} -> Referente: {ref}')

            ref2, created2 = ValReferenteCargaTemporal.objects.get_or_create(
                cuil=cuil,
                region='REGION 2',
                defaults={
                    'nombre': 'Juan',
                    'apellido': 'Perez Prueba',
                }
            )
            self.stdout.write(f'   {"[+] Creado" if created2 else "[=] Ya existe"} -> Referente region 2: {ref2}')

            # 2. CABECERAS
            cabeceras_data = [
                {
                    'nombre_cabecera': 'Cabecera Central Norte',
                    'regional': 'REGION 1',
                    'localidad': 'Resistencia',
                    'codigo_departamento': '026',
                    'codigo_localidad': '100010',
                    'codigo_cabecera': 'CAB-001',
                    'direccion': 'Av. Sarmiento 1234',
                    'detalle_direccion': 'Piso 2, Of. 5',
                    'codigo_postal': '3500',
                    'codigo_area_cabecera': '0362',
                    'telefono_cabecera': '4444-1234',
                    'nombre_coordinador': 'Maria Gonzalez',
                    'correo_coordinador': 'mgonzalez@educacion.gob.ar',
                    'codigo_area_coordinador': '0362',
                    'telefono_coordinador': '155-123456',
                    'cuil_coordinador': '27345678901',
                },
                {
                    'nombre_cabecera': 'Cabecera Sur',
                    'regional': 'REGION 1',
                    'localidad': 'Barranqueras',
                    'codigo_departamento': '026',
                    'codigo_localidad': '100020',
                    'codigo_cabecera': 'CAB-002',
                    'direccion': 'Belgrano 500',
                    'detalle_direccion': '',
                    'codigo_postal': '3501',
                    'codigo_area_cabecera': '0362',
                    'telefono_cabecera': '4555-6789',
                    'nombre_coordinador': 'Carlos Romero',
                    'correo_coordinador': 'cromero@educacion.gob.ar',
                    'codigo_area_coordinador': '0362',
                    'telefono_coordinador': '155-654321',
                    'cuil_coordinador': '20456789012',
                },
                {
                    'nombre_cabecera': 'Cabecera Region 2 Este',
                    'regional': 'REGION 2',
                    'localidad': 'Presidencia Roque Saenz Pena',
                    'codigo_departamento': '021',
                    'codigo_localidad': '200010',
                    'codigo_cabecera': 'CAB-003',
                    'direccion': 'San Martin 750',
                    'detalle_direccion': 'Planta Baja',
                    'codigo_postal': '3700',
                    'codigo_area_cabecera': '0364',
                    'telefono_cabecera': '4222-9090',
                    'nombre_coordinador': 'Laura Medina',
                    'correo_coordinador': 'lmedina@educacion.gob.ar',
                    'codigo_area_coordinador': '0364',
                    'telefono_coordinador': '155-001122',
                    'cuil_coordinador': '27567890123',
                },
            ]

            cabeceras_creadas = []
            for cab_data in cabeceras_data:
                cab, c = ValCabecera.objects.get_or_create(
                    nombre_cabecera=cab_data['nombre_cabecera'],
                    defaults=cab_data
                )
                cabeceras_creadas.append(cab)
                self.stdout.write(f'   {"[+] Creada" if c else "[=] Ya existe"} -> Cabecera: {cab.nombre_cabecera}')

            # 3. ESTABLECIMIENTOS
            establecimientos_data = [
                {
                    'cueanexo': '160001000',
                    'escuela': 'Escuela N 1 Juan Bautista Alberdi',
                    'sector': 'Estatal',
                    'ambito': 'Urbano',
                    'region': 'REGION 1',
                    'localidad': 'Resistencia',
                    'departamento': 'San Fernando',
                },
                {
                    'cueanexo': '160002000',
                    'escuela': 'Escuela N 2 Domingo Faustino Sarmiento',
                    'sector': 'Estatal',
                    'ambito': 'Urbano',
                    'region': 'REGION 1',
                    'localidad': 'Barranqueras',
                    'departamento': 'San Fernando',
                },
                {
                    'cueanexo': '160003000',
                    'escuela': 'Escuela N 3 General San Martin',
                    'sector': 'Estatal',
                    'ambito': 'Rural',
                    'region': 'REGION 2',
                    'localidad': 'Presidencia Roque Saenz Pena',
                    'departamento': 'Comandante Fernandez',
                },
            ]

            establecimientos_creados = []
            for est_data in establecimientos_data:
                est, c = ValEstablecimiento.objects.get_or_create(
                    cueanexo=est_data['cueanexo'],
                    defaults=est_data
                )
                establecimientos_creados.append(est)
                self.stdout.write(f'   {"[+] Creado" if c else "[=] Ya existe"} -> Establecimiento: {est.escuela}')

            # 4. GRADOS
            grados_creados = []
            for est in establecimientos_creados:
                for nombre_grado in ['2do Año/Grado', '3er Año/Grado']:
                    grado, c = ValGrado.objects.get_or_create(
                        cueanexo=est.cueanexo,
                        nombre_grado=nombre_grado,
                        establecimiento=est,
                    )
                    grados_creados.append(grado)
                    self.stdout.write(f'   {"[+] Creado" if c else "[=] Ya existe"} -> Grado: {est.cueanexo} | {nombre_grado}')

            # 5. SECCIONES
            secciones_base = [
                ('A', 'MAÑANA', 28),
                ('B', 'TARDE', None),
                ('C', 'MAÑANA', 32),
            ]

            total_secciones = 0
            for grado in grados_creados:
                for sec, turno, matricula in secciones_base:
                    obj, c = ValSeccion.objects.get_or_create(
                        seccion=sec,
                        turno=turno,
                        grado=grado,
                        defaults={
                            'matricula': matricula,
                            'estado_validacion': 'PENDIENTE',
                        }
                    )
                    if c:
                        total_secciones += 1
                    self.stdout.write(
                        f'   {"[+] Creada" if c else "[=] Ya existe"} -> Seccion {grado.establecimiento.cueanexo} '
                        f'{grado.nombre_grado} {sec}/{turno} matricula={matricula}'
                    )

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS('[OK] Carga de datos de prueba completada'))
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(f'   CUIL del referente : {cuil}')
        self.stdout.write(f'   Regiones asignadas : REGION 1, REGION 2')
        self.stdout.write(f'   Establecimientos   : {len(establecimientos_creados)}')
        self.stdout.write(f'   Grados             : {len(grados_creados)}')
        self.stdout.write(f'   Secciones creadas  : {total_secciones}')
        self.stdout.write(f'   Cabeceras          : {len(cabeceras_creadas)}')
        self.stdout.write('')
        self.stdout.write(self.style.NOTICE('[INFO] Accede a: http://127.0.0.1:8000/validaciones_2026/'))
        self.stdout.write(self.style.SUCCESS('=' * 60))
