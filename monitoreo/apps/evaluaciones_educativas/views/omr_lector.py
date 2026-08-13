"""
views/omr_lector.py

Vistas para el módulo OMR (Optical Mark Recognition) de exámenes de opción múltiple.

Flujo:
  1. seleccionar_alumno  → busca y selecciona el alumno del sistema
  2. lector_omr          → captura de foto + procesamiento frontend + edición manual
  3. guardar_lectura     → POST JSON con las respuestas finales → guarda en DB
  4. lista_lecturas      → historial de lecturas del alumno o globales
  5. detalle_lectura     → detalle de una lectura específica
"""

import io
import json
import logging

from PIL import Image, UnidentifiedImageError
from django.core.exceptions import RequestDataTooBig
from django.core.paginator import Paginator
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.db.models import Q
from django.urls import reverse

from apps.evaluaciones_educativas.models.fluidez_2026 import AlumnoFluidez2026, EstablecimientosFluidez2026
from apps.evaluaciones_educativas.models.omr_lector import LecturaOMR


logger = logging.getLogger(__name__)
ITEM_KEYS = {str(i) for i in range(1, 13)}
SAVE_PAYLOAD_KEYS = {
    'respuestas', 'confianza', 'modelo_examen',
    'revisado_manualmente', 'observaciones',
}
MAX_JSON_BYTES = 32 * 1024
MAX_UPLOAD_BYTES = 12 * 1024 * 1024
MAX_IMAGE_PIXELS = 25_000_000
ALLOWED_IMAGE_FORMATS = {'JPEG', 'PNG', 'WEBP'}
ALLOWED_CONTENT_TYPES = {'image/jpeg', 'image/png', 'image/webp'}
FORMAT_CONTENT_TYPES = {'JPEG': 'image/jpeg', 'PNG': 'image/png', 'WEBP': 'image/webp'}


def _json_error(message, code, status=400):
    return JsonResponse({'ok': False, 'error': message, 'code': code}, status=status)


def _validar_payload_lectura(payload):
    """Valida y normaliza el contrato JSON antes de tocar la base de datos."""
    if not isinstance(payload, dict):
        raise ValueError('El cuerpo JSON debe ser un objeto.')
    unexpected = set(payload) - SAVE_PAYLOAD_KEYS
    if unexpected:
        raise ValueError(f'Campos no permitidos: {", ".join(sorted(unexpected))}.')
    if set(payload) != SAVE_PAYLOAD_KEYS:
        raise ValueError('Faltan campos obligatorios en la lectura.')

    respuestas = payload['respuestas']
    confianza = payload['confianza']
    if not isinstance(respuestas, dict) or set(respuestas) != ITEM_KEYS:
        raise ValueError('Las respuestas deben incluir exactamente los ítems 1 a 12.')
    if not isinstance(confianza, dict) or set(confianza) != ITEM_KEYS:
        raise ValueError('La confianza debe incluir exactamente los ítems 1 a 12.')

    normalized_respuestas = {}
    normalized_confianza = {}
    for key in sorted(ITEM_KEYS, key=int):
        response = respuestas[key]
        if not isinstance(response, str) or response not in {'A', 'B', 'C', 'D'}:
            raise ValueError(f'El ítem {key} debe tener una respuesta entre A y D.')
        confidence = confianza[key]
        if isinstance(confidence, bool) or not isinstance(confidence, int) or not 0 <= confidence <= 100:
            raise ValueError(f'La confianza del ítem {key} debe ser un entero entre 0 y 100.')
        normalized_respuestas[key] = response
        normalized_confianza[key] = confidence

    modelo = payload['modelo_examen']
    if not isinstance(modelo, str) or modelo not in {'', 'A', 'B', 'C', 'D'}:
        raise ValueError('El modelo de examen no es válido.')
    revisado = payload['revisado_manualmente']
    if not isinstance(revisado, bool):
        raise ValueError('El indicador de revisión debe ser verdadero o falso.')
    observaciones = payload['observaciones']
    if not isinstance(observaciones, str) or len(observaciones) > 2000:
        raise ValueError('Las observaciones no pueden superar los 2000 caracteres.')

    return {
        'respuestas': normalized_respuestas,
        'confianza': normalized_confianza,
        'modelo_examen': modelo,
        'revisado_manualmente': revisado,
        'observaciones': observaciones.strip(),
    }


def _validar_imagen_subida(upload):
    """Comprueba tamaño, MIME, formato y dimensiones reales de una imagen."""
    if not upload.size:
        raise ValueError('La imagen está vacía.')
    if upload.size > MAX_UPLOAD_BYTES:
        raise ValueError('La imagen es demasiado grande. El límite es 12 MB.')
    declared_content_type = (upload.content_type or '').lower()
    if declared_content_type not in ALLOWED_CONTENT_TYPES:
        raise ValueError('El archivo debe ser una imagen JPEG, PNG o WebP.')

    image_bytes = upload.read(MAX_UPLOAD_BYTES + 1)
    if len(image_bytes) > MAX_UPLOAD_BYTES:
        raise ValueError('La imagen es demasiado grande. El límite es 12 MB.')
    try:
        with Image.open(io.BytesIO(image_bytes)) as image:
            if image.format not in ALLOWED_IMAGE_FORMATS:
                raise ValueError('El formato de imagen no está permitido.')
            if FORMAT_CONTENT_TYPES[image.format] != declared_content_type:
                raise ValueError('El tipo declarado no coincide con la imagen.')
            width, height = image.size
            if width < 1 or height < 1 or width * height > MAX_IMAGE_PIXELS:
                raise ValueError('La imagen tiene dimensiones demasiado grandes.')
            image.verify()
    except (Image.DecompressionBombError, UnidentifiedImageError, OSError, SyntaxError) as exc:
        raise ValueError('El archivo no contiene una imagen válida.') from exc
    return image_bytes


# ─── 1. Selección de alumno ───────────────────────────────────────────────────

def seleccionar_alumno(request):
    """
    Permite buscar y seleccionar un alumno existente del sistema antes
    de proceder a la carga OMR de su examen.

    GET: muestra formulario de búsqueda
    POST: filtra alumnos por nombre/apellido/DNI y cueanexo
    """
    alumnos = None
    query = ''
    cueanexo_seleccionado = ''

    # Obtener lista de cueanexos disponibles
    establecimientos = EstablecimientosFluidez2026.objects.using('Evaluacion').order_by('escuela')

    if request.method == 'POST':
        query = request.POST.get('q', '').strip()
        cueanexo_seleccionado = request.POST.get('cueanexo', '').strip()

        qs = AlumnoFluidez2026.objects.using('Evaluacion').select_related(
            'seccion',
            'seccion__grado',
            'seccion__grado__Establecimiento',
        )

        if cueanexo_seleccionado:
            qs = qs.filter(seccion__grado__cueanexo=cueanexo_seleccionado)

        if query:
            qs = qs.filter(
                Q(nombre__icontains=query) |
                Q(apellido__icontains=query) |
                Q(dni__icontains=query)
            )

        alumnos = qs.order_by('apellido', 'nombre')[:50]  # Limitar a 50 resultados

    contexto = {
        'alumnos': alumnos,
        'query': query,
        'cueanexo_seleccionado': cueanexo_seleccionado,
        'establecimientos': establecimientos,
    }
    return render(request, 'omr_lector/seleccionar_alumno.html', contexto)


# ─── 2. Lector OMR (captura + procesamiento) ─────────────────────────────────

def lector_omr(request, alumno_public_id):
    """
    Página principal del lector OMR para un alumno específico.

    Muestra:
    - Datos del alumno seleccionado
    - Interfaz de captura de foto (cámara o archivo)
    - Panel de resultados OMR editable
    - Botón para guardar
    """
    alumno = get_object_or_404(
        AlumnoFluidez2026.objects.using('Evaluacion').select_related(
            'seccion',
            'seccion__grado',
            'seccion__grado__Establecimiento',
        ),
        public_id=alumno_public_id,
    )

    # Verificar si ya existe una lectura OMR para este alumno
    lectura_existente = LecturaOMR.objects.using('Evaluacion').filter(
        alumno=alumno
    ).order_by('-fecha_lectura').first()

    contexto = {
        'alumno': alumno,
        'lectura_existente': lectura_existente,
        'num_items': range(1, 13),  # ítems 1 a 12
        'opciones': ['A', 'B', 'C', 'D'],
    }
    return render(request, 'omr_lector/lector.html', contexto)


# ─── 3. Guardar lectura ───────────────────────────────────────────────────────

@require_POST
def guardar_lectura(request, alumno_public_id):
    """
    Recibe las respuestas OMR como JSON (desde el frontend) y las guarda
    en la base de datos como un registro LecturaOMR.

    Payload esperado (JSON):
    {
        "respuestas": {"1": "A", "2": "C", ..., "12": "B"},
        "confianza":  {"1": 95,  "2": 40,  ..., "12": 78},
        "modelo_examen": "B",
        "revisado_manualmente": true,
        "observaciones": "..."
    }
    """
    if request.content_type != 'application/json':
        return _json_error('El contenido debe enviarse como JSON.', 'INVALID_CONTENT_TYPE', 415)
    try:
        content_length = int(request.META.get('CONTENT_LENGTH') or 0)
    except (TypeError, ValueError):
        return _json_error('El tamaño declarado no es válido.', 'INVALID_CONTENT_LENGTH')
    if content_length > MAX_JSON_BYTES:
        return _json_error('El JSON supera el tamaño permitido.', 'JSON_TOO_LARGE', 413)
    try:
        body = request.body
        if len(body) > MAX_JSON_BYTES:
            return _json_error('El JSON supera el tamaño permitido.', 'JSON_TOO_LARGE', 413)
        payload = _validar_payload_lectura(json.loads(body))
    except RequestDataTooBig:
        return _json_error('El JSON supera el tamaño permitido.', 'JSON_TOO_LARGE', 413)
    except json.JSONDecodeError:
        return _json_error('El JSON enviado no es válido.', 'INVALID_JSON')
    except (UnicodeDecodeError, ValueError) as exc:
        return _json_error(str(exc), 'INVALID_PAYLOAD')

    respuestas = payload['respuestas']
    confianza = payload['confianza']
    alumno = get_object_or_404(
        AlumnoFluidez2026.objects.using('Evaluacion'),
        public_id=alumno_public_id,
    )

    # Crear o actualizar la lectura OMR
    # Si ya existe una lectura para este alumno, se reemplaza (para permitir re-escaneo)
    lectura, creada = LecturaOMR.objects.using('Evaluacion').update_or_create(
        alumno=alumno,
        defaults={
            'modelo_examen': payload['modelo_examen'],
            'item_1':  respuestas.get('1', ''),
            'item_2':  respuestas.get('2', ''),
            'item_3':  respuestas.get('3', ''),
            'item_4':  respuestas.get('4', ''),
            'item_5':  respuestas.get('5', ''),
            'item_6':  respuestas.get('6', ''),
            'item_7':  respuestas.get('7', ''),
            'item_8':  respuestas.get('8', ''),
            'item_9':  respuestas.get('9', ''),
            'item_10': respuestas.get('10', ''),
            'item_11': respuestas.get('11', ''),
            'item_12': respuestas.get('12', ''),
            'confianza_json': confianza,
            'revisado_manualmente': payload['revisado_manualmente'],
            'observaciones': payload['observaciones'],
            'encargado_carga': str(request.user)[:9] if request.user.is_authenticated else '',
        }
    )

    return JsonResponse({
        'ok': True,
        'creada': creada,
        'lectura_public_id': str(lectura.public_id),
        'redirect_url': reverse(
            'evaluaciones_educativas:omr_lector:detalle_lectura',
            kwargs={'public_id': lectura.public_id},
        ),
    })


# ─── 4. Lista de lecturas ─────────────────────────────────────────────────────

def lista_lecturas(request):
    """
    Historial de todas las lecturas OMR.
    Soporta filtrado por cueanexo y búsqueda por nombre/apellido de alumno.
    """
    query = request.GET.get('q', '').strip()
    cueanexo = request.GET.get('cueanexo', '').strip()

    lecturas = LecturaOMR.objects.using('Evaluacion').select_related(
        'alumno',
        'alumno__seccion',
        'alumno__seccion__grado',
        'alumno__seccion__grado__Establecimiento',
    ).order_by('-fecha_lectura')

    if cueanexo:
        lecturas = lecturas.filter(alumno__seccion__grado__cueanexo=cueanexo)

    if query:
        lecturas = lecturas.filter(
            Q(alumno__nombre__icontains=query) |
            Q(alumno__apellido__icontains=query) |
            Q(alumno__dni__icontains=query)
        )

    establecimientos = EstablecimientosFluidez2026.objects.using('Evaluacion').order_by('escuela')

    paginator = Paginator(lecturas, 25)
    page_obj = paginator.get_page(request.GET.get('page'))
    contexto = {
        'lecturas': page_obj,
        'page_obj': page_obj,
        'query': query,
        'cueanexo': cueanexo,
        'establecimientos': establecimientos,
        'total': paginator.count,
    }
    return render(request, 'omr_lector/lista_lecturas.html', contexto)


# ─── 5. Detalle de lectura ────────────────────────────────────────────────────

def detalle_lectura(request, public_id):
    """
    Muestra el detalle completo de una lectura OMR específica.
    Permite al docente editar y corregir respuestas desde esta vista también.
    """
    lectura = get_object_or_404(
        LecturaOMR.objects.using('Evaluacion').select_related(
            'alumno',
            'alumno__seccion',
            'alumno__seccion__grado',
            'alumno__seccion__grado__Establecimiento',
        ),
        public_id=public_id,
    )

    # Construir lista de ítems con respuesta y confianza para el template
    items_detalle = []
    confianza = lectura.confianza_json or {}
    for i in range(1, 13):
        resp = getattr(lectura, f'item_{i}', '')
        conf = confianza.get(str(i), None)
        items_detalle.append({
            'num': i,
            'respuesta': resp,
            'confianza': conf,
            'dudoso': conf is not None and conf < 50,
        })

    contexto = {
        'lectura': lectura,
        'items_detalle': items_detalle,
        'opciones': ['A', 'B', 'C', 'D'],
    }
    return render(request, 'omr_lector/detalle_lectura.html', contexto)


# ─── 6. Procesar imagen con OpenCV (backend) ──────────────────────────────────

@require_POST
def procesar_imagen_omr(request):
    """
    Endpoint de procesamiento OMR server-side.

    Recibe: multipart/form-data con campo 'imagen' (File de foto del examen)
    Retorna: JSON con las respuestas detectadas por ítem.

    Ventaja frente al procesamiento en el navegador (OpenCV.js):
    - No requiere descargar ~8MB de WASM al celular del docente.
    - Procesamiento más rápido y preciso en servidor.
    - Funciona en celulares viejos y con mala conexión.

    Respuesta exitosa:
    {
        "ok": true,
        "respuestas": {"1": "A", "2": "C", ...},
        "confianza":  {"1": 85,  "2": 40, ...},
        "items_dudosos": [3, 7],
        "used_warp": true
    }

    Si opencv-python-headless no está instalado:
    {"ok": false, "cv_not_installed": true, "error": "..."}
    """
    if 'imagen' not in request.FILES:
        return _json_error('No se recibió ninguna imagen.', 'IMAGE_REQUIRED')

    imagen_file = request.FILES['imagen']

    try:
        from apps.evaluaciones_educativas.views.omr_utils import procesar_imagen
        imagen_bytes = _validar_imagen_subida(imagen_file)
        resultado = procesar_imagen(imagen_bytes)
        return JsonResponse({'ok': True, **resultado})

    except ImportError:
        # No se expone el detalle de instalación ni de rutas internas al cliente.
        return JsonResponse({
            'ok': False,
            'cv_not_installed': True,
            'error': 'El servicio de reconocimiento no está disponible.',
            'code': 'SERVICE_UNAVAILABLE',
        }, status=503)

    except ValueError as e:
        message = str(e)
        code = 'IMAGE_TOO_LARGE' if 'demasiado grande' in message else 'INVALID_IMAGE'
        return _json_error(message, code)

    except Exception:
        logger.exception('Error inesperado al procesar una imagen OMR')
        return _json_error(
            'No se pudo procesar la imagen. Intentá nuevamente.',
            'PROCESSING_ERROR',
            500,
        )
