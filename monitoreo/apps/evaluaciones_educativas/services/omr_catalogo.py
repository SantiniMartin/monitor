"""Fuente de datos del flujo OMR.

La implementacion actual es deliberadamente simulada.  Las vistas consumen
este contrato en lugar de conocer la estructura de la futura base externa. Al
conectar la capa de oferta unica solo sera necesario reemplazar las funciones
publicas de este modulo.
"""

from __future__ import annotations

from dataclasses import dataclass


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


# Datos provisorios. Los IDs son las unicas claves que atraviesan las URLs y
# reproducen el contrato que tendra la base externa.
_OFERTAS = (
    OfertaUsuario("est-0001", "220000001", "E.E.P. N.º 1 - Simulada", "grado-7-01", "7.º grado"),
    OfertaUsuario("est-0002", "220000002", "E.E.P. N.º 2 - Simulada", "grado-7-02", "7.º grado"),
)

_ALUMNOS = (
    AlumnoOferta("alumno-0001", "45000001", "Gómez", "Ana", "est-0001", "grado-7-01", "7.º grado", "A", "Mañana"),
    AlumnoOferta("alumno-0002", "45000002", "Pérez", "Bruno", "est-0001", "grado-7-01", "7.º grado", "A", "Mañana"),
    AlumnoOferta("alumno-0003", "45000003", "López", "Carla", "est-0002", "grado-7-02", "7.º grado", "B", "Tarde"),
)


def ofertas_del_usuario(username: str) -> tuple[OfertaUsuario, ...]:
    """Devuelve las ofertas autorizadas para un usuario autenticado.

    En simulacion todos los usuarios autenticados reciben el mismo catalogo.
    La version real filtrara la capa de oferta unica por CUIL/username.
    """
    if not str(username).strip():
        return ()
    return _OFERTAS


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
    """Lista alumnos del grado que el usuario posee en esa oferta."""
    oferta = oferta_autorizada(username, id_establecimiento)
    if oferta is None:
        return ()
    return tuple(
        alumno
        for alumno in _ALUMNOS
        if alumno.id_establecimiento == oferta.id_establecimiento
        and alumno.id_grado == oferta.id_grado
    )


def alumno_autorizado(username: str, id_alumno: str) -> AlumnoOferta | None:
    ofertas = {
        (oferta.id_establecimiento, oferta.id_grado)
        for oferta in ofertas_del_usuario(username)
    }
    return next(
        (
            alumno
            for alumno in _ALUMNOS
            if alumno.id_alumno == id_alumno
            and (alumno.id_establecimiento, alumno.id_grado) in ofertas
        ),
        None,
    )


def materia_valida(slug: str) -> bool:
    return slug in MATERIAS


def hojas_del_examen(slug: str) -> tuple[str, ...]:
    """Devuelve las hojas requeridas por el examen solicitado."""
    return HOJAS_POR_EXAMEN.get(slug, ())


def items_por_hoja_del_examen(slug: str) -> tuple[int, ...]:
    """Devuelve cuántos ítems contiene cada hoja del examen."""
    return ITEMS_POR_HOJA_EXAMEN.get(slug, ())
