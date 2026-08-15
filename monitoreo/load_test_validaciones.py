import os
import django

# Configuramos el entorno de Django para poder ejecutar el script desde la terminal
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'monitoreo.settings')
django.setup()

from apps.evaluaciones_educativas.models.validaciones_2026 import (
    ValReferenteCargaTemporal, ValCabecera, ValEstablecimiento,
    ValGrado, ValSeccion
)

def create_test_data():
    print("Borrando datos anteriores...")
    ValSeccion.objects.all().delete()
    ValGrado.objects.all().delete()
    ValEstablecimiento.objects.all().delete()
    ValCabecera.objects.all().delete()
    ValReferenteCargaTemporal.objects.all().delete()

    print("Creando referente de carga...")
    referente = ValReferenteCargaTemporal.objects.create(
        cuil="20123456789",
        nombre="Juan",
        apellido="Perez",
        region="Region 1",
        dni="12345678"
    )
    
    referente2 = ValReferenteCargaTemporal.objects.create(
        cuil="27987654321",
        nombre="Maria",
        apellido="Gomez",
        region="Region 2",
        dni="87654321"
    )

    print("Creando cabeceras...")
    cabecera1 = ValCabecera.objects.create(
        codigo_cabecera="CAB01",
        nombre_cabecera="Cabecera Central Región 1",
        regional="Region 1",
        localidad="Capital"
    )
    cabecera2 = ValCabecera.objects.create(
        codigo_cabecera="CAB02",
        nombre_cabecera="Cabecera Norte Región 2",
        regional="Region 2",
        localidad="Norte"
    )

    print("Creando establecimientos...")
    est1 = ValEstablecimiento.objects.create(
        cueanexo="123456700",
        escuela="Escuela N° 1 San Martin",
        region="Region 1",
        cabecera=cabecera1,
        participa_aprender=True
    )
    est2 = ValEstablecimiento.objects.create(
        cueanexo="987654300",
        escuela="Escuela N° 2 Belgrano",
        region="Region 1",
        cabecera=cabecera1,
        participa_aprender=False,
        motivo_no_participa="En reparaciones"
    )
    est3 = ValEstablecimiento.objects.create(
        cueanexo="111222300",
        escuela="Escuela N° 3 Sarmiento",
        region="Region 2",
        cabecera=cabecera2,
        participa_aprender=True
    )

    print("Creando grados...")
    grado1 = ValGrado.objects.create(
        cueanexo=est1.cueanexo,
        nombre_grado='3er Año/Grado',
        establecimiento=est1
    )
    grado2 = ValGrado.objects.create(
        cueanexo=est2.cueanexo,
        nombre_grado='3er Año/Grado',
        establecimiento=est2
    )
    grado3 = ValGrado.objects.create(
        cueanexo=est3.cueanexo,
        nombre_grado='3er Año/Grado',
        establecimiento=est3
    )

    print("Creando secciones...")
    ValSeccion.objects.create(
        seccion='A',
        turno='MAÑANA',
        grado=grado1,
        matricula=25
    )
    ValSeccion.objects.create(
        seccion='B',
        turno='TARDE',
        grado=grado1,
        matricula=22
    )
    ValSeccion.objects.create(
        seccion='A',
        turno='MAÑANA',
        grado=grado2,
        matricula=30
    )
    ValSeccion.objects.create(
        seccion='U',
        turno='MAÑANA EXTENDIDA',
        grado=grado3,
        matricula=15
    )

    print("¡Datos de prueba creados exitosamente!")

if __name__ == '__main__':
    create_test_data()
