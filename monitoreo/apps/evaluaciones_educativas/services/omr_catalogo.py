"""Fuente de datos autorizada para el flujo OMR."""

from __future__ import annotations

from dataclasses import dataclass
import re


MATERIAS = {
    "lengua": "Lengua",
    "contexto": "Examen de contexto",
    "matematica": "Matemática",
}
HOJAS_POR_EXAMEN = {
    "lengua": ("Hoja principal",),
    "matematica": ("Hoja principal",),
    "contexto": ("Hoja de contexto · preguntas 1 a 8", "Hoja de contexto · preguntas 9 a 17"),
}
ITEMS_POR_HOJA_EXAMEN = {
    # 1-24 más los tres criterios adicionales 24.1, 24.2 y 24.3.
    "lengua": (27,),
    "matematica": (24,),
    "contexto": (8, 9),
}
# Cantidad de casilleros impresos en cada pregunta del cuestionario.
OPCIONES_POR_ITEM_CONTEXTO = (6, 2, 3, 6, 5, 3, 4, 6, 3, 6, 3, 3, 3, 5, 4, 4, 3)
ITEMS_MULTIPLES_CONTEXTO = frozenset({1, 4, 7, 8, 14})
# El lector ya persiste en los modelos OMR de la base dedicada.
SIMULATION_MODE = False
ANIO_GRADO_OMR = '7mo Año/Grado'
_CUEANEXO_RE = re.compile(r'^\d{9}$')
_TRAYECTORIA_FIELDS = (
    'id', 'id_alumno', 'cueanexo', 'escuela', 'c_grado_nivel_servicio',
    'anio_grado', 'numero_documento', 'apellido', 'nombre',
    'nombre_seccion', 'turno',
)


@dataclass(frozen=True)
class OfertaUsuario:
    id_establecimiento: str
    cueanexo: str
    establecimiento: str
    id_grado: str
    grado: str


@dataclass(frozen=True)
class AlumnoOferta:
    id_alumno: str
    dni: str
    apellido: str
    nombre: str
    id_establecimiento: str
    id_grado: str
    grado: str
    seccion: str
    turno: str


# El identificador de trayectoria es la clave estable que atraviesa las URLs.
def _cueanexo_del_usuario(username: str) -> str | None:
    """Un usuario CUE/anexo sólo puede consultar su propio establecimiento."""
    cueanexo = str(username or '').strip()
    return cueanexo if _CUEANEXO_RE.fullmatch(cueanexo) else None


def _trayectorias_de_siete(cueanexo: str):
    """Consulta de sólo lectura a la vista oficial mediante su alias dedicado."""
    # Importación diferida: este servicio también es usado por los modelos OMR.
    from apps.evaluaciones_educativas.models.modelo_oficial import V_Trayectoria_Alumnos_SGE

    return (
        V_Trayectoria_Alumnos_SGE.objects.using('test')
        .filter(cueanexo=cueanexo, anio_grado=ANIO_GRADO_OMR)
        .only(*_TRAYECTORIA_FIELDS)
    )


def _alumno_oferta(trayectoria) -> AlumnoOferta:
    return AlumnoOferta(
        id_alumno=str(trayectoria.id),
        dni=str(trayectoria.numero_documento or ''),
        apellido=str(trayectoria.apellido or ''),
        nombre=str(trayectoria.nombre or ''),
        id_establecimiento=str(trayectoria.cueanexo),
        id_grado=str(trayectoria.c_grado_nivel_servicio or ''),
        grado=str(trayectoria.anio_grado),
        seccion=str(trayectoria.nombre_seccion or ''),
        turno=str(trayectoria.turno or ''),
    )


def ofertas_del_usuario(username: str) -> tuple[OfertaUsuario, ...]:
    """Devuelve la oferta de 7mo Año/Grado autorizada para el usuario CUE."""
    cueanexo = _cueanexo_del_usuario(username)
    if cueanexo is None:
        return ()
    trayectoria = _trayectorias_de_siete(cueanexo).order_by('escuela', 'id').first()
    if trayectoria is None:
        return ()
    return (OfertaUsuario(
        id_establecimiento=cueanexo,
        cueanexo=cueanexo,
        establecimiento=str(trayectoria.escuela or ''),
        id_grado=str(trayectoria.c_grado_nivel_servicio or ''),
        grado=ANIO_GRADO_OMR,
    ),)


def oferta_autorizada(username: str, id_establecimiento: str) -> OfertaUsuario | None:
    return next(
        (
            oferta
            for oferta in ofertas_del_usuario(username)
            if oferta.id_establecimiento == id_establecimiento
        ),
        None,
    )


def alumnos_de_oferta(username: str, id_establecimiento: str) -> tuple[AlumnoOferta, ...]:
    """Lista alumnos de 7mo Año/Grado del CUE/anexo autenticado."""
    cueanexo = _cueanexo_del_usuario(username)
    if cueanexo is None or id_establecimiento != cueanexo:
        return ()
    return tuple(
        _alumno_oferta(trayectoria)
        for trayectoria in _trayectorias_de_siete(cueanexo).order_by('apellido', 'nombre', 'id')
    )


def alumno_autorizado(username: str, id_alumno: str) -> AlumnoOferta | None:
    cueanexo = _cueanexo_del_usuario(username)
    if cueanexo is None:
        return None
    trayectoria = _trayectorias_de_siete(cueanexo).filter(id=str(id_alumno)).first()
    return _alumno_oferta(trayectoria) if trayectoria is not None else None


def materia_valida(slug: str) -> bool:
    return slug in MATERIAS


def hojas_del_examen(slug: str) -> tuple[str, ...]:
    """Devuelve las hojas requeridas por el examen solicitado."""
    return HOJAS_POR_EXAMEN.get(slug, ())


def items_por_hoja_del_examen(slug: str) -> tuple[int, ...]:
    """Devuelve cuántos ítems contiene cada hoja del examen."""
    return ITEMS_POR_HOJA_EXAMEN.get(slug, ())
