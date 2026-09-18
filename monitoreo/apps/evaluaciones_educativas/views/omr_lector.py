"""
views/omr_lector.py

Vistas para el módulo OMR (Optical Mark Recognition) de exámenes de opción múltiple.

Flujo:
  1. seleccionar_alumno  → busca y selecciona el alumno del sistema
  2. lector_omr          → captura y procesamiento OMR, o carga completamente manual
  3. guardar_lectura     → POST JSON con las respuestas finales → guarda en DB
  4. lista_lecturas      → historial de lecturas del alumno o globales
  5. detalle_lectura     → detalle de una lectura específica
"""

import io
import json
import logging
from types import SimpleNamespace

from PIL import Image, UnidentifiedImageError
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, RequestDataTooBig
from django.core.paginator import Paginator
from django.shortcuts import render, get_object_or_404
from django.http import Http404, JsonResponse
from django.views.decorators.http import require_POST
from django.db import transaction
from django.db.models import CharField, Q, Value
from django.urls import reverse

from apps.evaluaciones_educativas.models.omr_lector import (
    AlumnoDiagnostico_Ingreso_2026,
    ExamenContexto,
    ExamenLengua,
    ExamenMatematica,
    EstablecimientosDiagnostico_Ingreso_2026,
)
from apps.evaluaciones_educativas.services.omr_catalogo import (
    ITEMS_MULTIPLES_CONTEXTO,
    MATERIAS,
    OPCIONES_POR_ITEM_CONTEXTO,
    SIMULATION_MODE,
    alumno_autorizado,
    alumnos_de_oferta,
    hojas_del_examen,
    items_por_hoja_del_examen,
    materia_valida,
    oferta_autorizada,
    ofertas_del_usuario,
)


logger = logging.getLogger(__name__)
SAVE_PAYLOAD_KEYS = {
    'lecturas', 'modelo_examen',
    'revisado_manualmente',
}
MAX_JSON_BYTES = 32 * 1024
MAX_UPLOAD_BYTES = 12 * 1024 * 1024
MAX_IMAGE_PIXELS = 25_000_000
ALLOWED_IMAGE_FORMATS = {'JPEG', 'PNG', 'WEBP'}
ALLOWED_CONTENT_TYPES = {'image/jpeg', 'image/png', 'image/webp'}
FORMAT_CONTENT_TYPES = {'JPEG': 'image/jpeg', 'PNG': 'image/png', 'WEBP': 'image/webp'}
LOGIN_URL = '/admin/login/'


def _session_key_examenes_guardados(id_alumno):
    return f'omr_examenes_guardados_{id_alumno}'


def _json_error(message, code, status=400):
    return JsonResponse({'ok': False, 'error': message, 'code': code}, status=status)


def _validar_payload_lectura(payload, items_por_hoja, materia='lengua'):
    """Valida y normaliza el contrato JSON antes de tocar la base de datos."""
    if not isinstance(payload, dict):
        raise ValueError('El cuerpo JSON debe ser un objeto.')
    unexpected = set(payload) - SAVE_PAYLOAD_KEYS
    if unexpected:
        raise ValueError(f'Campos no permitidos: {", ".join(sorted(unexpected))}.')
    if set(payload) != SAVE_PAYLOAD_KEYS:
        raise ValueError('Faltan campos obligatorios en la lectura.')

    cantidad_hojas = len(items_por_hoja)
    image_keys = {f'imagen_{numero}' for numero in range(1, cantidad_hojas + 1)}
    lecturas = payload['lecturas']
    if not isinstance(lecturas, dict) or set(lecturas) != image_keys:
        raise ValueError(
            f'Deben enviarse exactamente {cantidad_hojas} hoja(s) para este examen.'
        )

    normalized_lecturas = {}
    for image_key in sorted(image_keys):
        numero_hoja = int(image_key.removeprefix('imagen_'))
        item_keys = {
            str(item) for item in range(1, items_por_hoja[numero_hoja - 1] + 1)
        }
        lectura = lecturas[image_key]
        if not isinstance(lectura, dict) or set(lectura) != {'respuestas', 'confianza'}:
            raise ValueError(f'La lectura {image_key} no tiene el formato esperado.')
        respuestas = lectura['respuestas']
        confianza = lectura['confianza']
        if not isinstance(respuestas, dict) or set(respuestas) != item_keys:
            raise ValueError(
                f'Las respuestas de {image_key} deben incluir los ítems '
                f'1 a {len(item_keys)}.'
            )
        if not isinstance(confianza, dict) or set(confianza) != item_keys:
            raise ValueError(
                f'La confianza de {image_key} debe incluir los ítems '
                f'1 a {len(item_keys)}.'
            )

        normalized_respuestas = {}
        normalized_confianza = {}
        for key in sorted(item_keys, key=int):
            response = respuestas[key]
            if not isinstance(response, str):
                raise ValueError(f'El ítem {key} de {image_key} debe ser texto.')
            if materia == 'contexto':
                global_item = sum(items_por_hoja[:numero_hoja - 1]) + int(key)
                allowed = set('ABCDEF'[:OPCIONES_POR_ITEM_CONTEXTO[global_item - 1]])
                selected = response.split(',') if response else []
                if (
                    len(selected) != len(set(selected))
                    or any(option not in allowed for option in selected)
                    or response != ','.join(sorted(selected))
                    or (global_item not in ITEMS_MULTIPLES_CONTEXTO and len(selected) > 1)
                ):
                    raise ValueError(
                        f'La respuesta del ítem {global_item} de Contexto no es válida.'
                    )
            elif response not in {'', 'A', 'B', 'C', 'D'}:
                raise ValueError(
                    f'El ítem {key} de {image_key} debe quedar vacío '
                    'o tener una respuesta entre A y D.'
                )
            confidence = confianza[key]
            if isinstance(confidence, bool) or not isinstance(confidence, int) or not 0 <= confidence <= 100:
                raise ValueError(f'La confianza del ítem {key} de {image_key} debe estar entre 0 y 100.')
            normalized_respuestas[key] = response
            normalized_confianza[key] = confidence
        normalized_lecturas[image_key] = {
            'respuestas': normalized_respuestas,
            'confianza': normalized_confianza,
        }

    modelo = payload['modelo_examen']
    if not isinstance(modelo, str) or modelo not in {'', 'A', 'B', 'C', 'D'}:
        raise ValueError('El modelo de examen no es válido.')
    if materia == 'contexto' and modelo:
        raise ValueError('El examen de contexto no utiliza modelo de respuestas.')
    if materia == 'lengua' and modelo not in {'A', 'B'}:
        raise ValueError('El examen de Lengua requiere el modelo A o B.')
    revisado = payload['revisado_manualmente']
    if not isinstance(revisado, bool):
        raise ValueError('El indicador de revisión debe ser verdadero o falso.')
    return {
        'lecturas': normalized_lecturas,
        'modelo_examen': modelo,
        'revisado_manualmente': revisado,
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


def _campos_lectura(payload, materia, items_por_hoja, username):
    """Convierte las hojas validadas en campos del modelo de examen indicado."""
    defaults = {
        'revisado_manualmente': payload['revisado_manualmente'],
        'encargado_carga': str(username)[:9],
        'confianza_json': {},
    }
    if materia == 'matematica':
        defaults.update({
            'tipo_examen': materia,
            'modelo_examen': payload['modelo_examen'],
        })
    elif materia == 'lengua':
        defaults['modelo_examen'] = payload['modelo_examen']
    total_items = sum(items_por_hoja)
    if materia == 'lengua':
        defaults.update({
            ExamenLengua.campo_item(item): ''
            for item in range(1, total_items + 1)
        })
    else:
        defaults.update({f'item_{item}': '' for item in range(1, total_items + 1)})

    global_item = 0
    for numero_hoja, cantidad_items in enumerate(items_por_hoja, start=1):
        lectura = payload['lecturas'][f'imagen_{numero_hoja}']
        for local_item in range(1, cantidad_items + 1):
            global_item += 1
            field_name = (
                ExamenLengua.campo_item(global_item)
                if materia == 'lengua' else f'item_{global_item}'
            )
            defaults[field_name] = lectura['respuestas'][str(local_item)]
            defaults['confianza_json'][str(global_item)] = lectura['confianza'][str(local_item)]
    return defaults


# ─── 1. Oferta, establecimiento y selección provisoria de alumno ─────────────


# @login_required()
def seleccionar_alumno(request):
    """Lista únicamente establecimientos y alumnos habilitados al usuario."""
    username = request.user.get_username()
    ofertas = ofertas_del_usuario(username)
    id_establecimiento = request.GET.get('establecimiento', '').strip()
    query_original = request.GET.get('q', '').strip()
    query = query_original.casefold()
    oferta = None
    alumnos = None

    if id_establecimiento:
        oferta = oferta_autorizada(username, id_establecimiento)
        if oferta is None:
            raise PermissionDenied('El establecimiento no pertenece a la oferta del usuario.')
        alumnos = alumnos_de_oferta(username, id_establecimiento)
        if query:
            alumnos = tuple(
                alumno for alumno in alumnos
                if query in f'{alumno.apellido} {alumno.nombre} {alumno.dni}'.casefold()
            )

    return render(request, 'omr_lector/flujo_alumnos.html', {
        'ofertas': ofertas,
        'oferta_seleccionada': oferta,
        'alumnos': alumnos,
        'query': query_original,
        'modo_simulacion': SIMULATION_MODE,
    })


# @login_required()
def seleccionar_materia(request, id_alumno):
    alumno = alumno_autorizado(request.user.get_username(), id_alumno)
    if alumno is None:
        raise PermissionDenied('El alumno no pertenece a una oferta habilitada para el usuario.')
    guardados = set(request.session.get(_session_key_examenes_guardados(id_alumno), []))
    examenes = [
        {
            'slug': slug,
            'nombre': nombre,
            'cantidad_hojas': len(hojas_del_examen(slug)),
            'guardado': slug in guardados,
        }
        for slug, nombre in MATERIAS.items()
    ]
    examenes.sort(key=lambda examen: examen['slug'] == 'contexto')
    return render(request, 'omr_lector/seleccionar_materia.html', {
        'alumno': alumno,
        'examenes': examenes,
        'modo_simulacion': SIMULATION_MODE,
    })


# ─── 2. Lector OMR (captura, procesamiento o carga manual) ───────────────────

# @login_required()
def lector_omr(request, id_alumno, materia):
    """
    Página principal del lector OMR para un alumno específico.

    Muestra:
    - Datos del alumno seleccionado
    - Interfaz de captura de foto (cámara o archivo) o carga manual
    - Panel de respuestas editable para las hojas requeridas por el examen
    - Botón para guardar
    """
    alumno_oferta = alumno_autorizado(request.user.get_username(), id_alumno)
    if alumno_oferta is None:
        raise PermissionDenied('El alumno no pertenece a una oferta habilitada para el usuario.')
    if not materia_valida(materia):
        raise PermissionDenied('La materia seleccionada no es válida.')

    nombres_hojas = hojas_del_examen(materia)
    items_por_hoja = items_por_hoja_del_examen(materia)
    oferta = oferta_autorizada(
        request.user.get_username(), alumno_oferta.id_establecimiento
    )
    establecimiento = SimpleNamespace(escuela=oferta.establecimiento)
    grado = SimpleNamespace(
        nombre_grado=alumno_oferta.grado,
        Establecimiento=establecimiento,
    )
    seccion = SimpleNamespace(
        grado=grado,
        seccion=alumno_oferta.seccion,
        turno=alumno_oferta.turno,
    )
    alumno = SimpleNamespace(
        public_id=alumno_oferta.id_alumno,
        id_alumno=alumno_oferta.id_alumno,
        dni=alumno_oferta.dni,
        nombre=alumno_oferta.nombre,
        apellido=alumno_oferta.apellido,
        seccion=seccion,
    )

    contexto = {
        'alumno': alumno,
        'lectura_existente': None,
        'materia': materia,
        'materia_nombre': MATERIAS[materia],
        'nombres_hojas': nombres_hojas,
        'total_hojas': len(nombres_hojas),
        'items_por_hoja': items_por_hoja,
        'opciones_contexto': OPCIONES_POR_ITEM_CONTEXTO,
        'items_multiples_contexto': sorted(ITEMS_MULTIPLES_CONTEXTO),
        'modo_simulacion': SIMULATION_MODE,
        'num_items': range(1, max(items_por_hoja) + 1),
        'opciones': ['A', 'B', 'C', 'D'],
    }
    return render(request, 'omr_lector/lector.html', contexto)


# ─── 3. Guardar lectura ───────────────────────────────────────────────────────

@require_POST
# @login_required()
def guardar_lectura(request, id_alumno, materia):
    """
    Recibe las respuestas OMR como JSON (desde el frontend) y las guarda
    en el modelo correspondiente de la base de datos dedicada.

    Payload esperado (JSON):
    {
        "lecturas": {
            "imagen_1": {"respuestas": {...}, "confianza": {...}}
        },
        "modelo_examen": "B",
        "revisado_manualmente": true,
    }
    La clave imagen_2 se exige solamente para el examen de contexto.
    """
    if not materia_valida(materia):
        raise PermissionDenied('El tipo de examen seleccionado no es válido.')
    items_por_hoja = items_por_hoja_del_examen(materia)

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
        payload = _validar_payload_lectura(json.loads(body), items_por_hoja, materia)
    except RequestDataTooBig:
        return _json_error('El JSON supera el tamaño permitido.', 'JSON_TOO_LARGE', 413)
    except json.JSONDecodeError:
        return _json_error('El JSON enviado no es válido.', 'INVALID_JSON')
    except (UnicodeDecodeError, ValueError) as exc:
        return _json_error(str(exc), 'INVALID_PAYLOAD')

    if alumno_autorizado(request.user.get_username(), id_alumno) is None:
        raise PermissionDenied('El alumno no pertenece a una oferta habilitada para el usuario.')

    # Mientras el catálogo usa alumnos ficticios no se crean registros huérfanos.
    # Al conectar la oferta real, se persiste siempre en la BD dedicada.
    lectura = None
    if not SIMULATION_MODE:
        alumno = get_object_or_404(
            AlumnoDiagnostico_Ingreso_2026.objects.using('Evaluacion'),
            pk=id_alumno,
        )
        defaults = _campos_lectura(
            payload,
            materia,
            items_por_hoja,
            request.user.get_username(),
        )
        with transaction.atomic(using='Evaluacion'):
            if materia == 'contexto':
                lectura = (
                    ExamenContexto.objects.using('Evaluacion')
                    .filter(alumno=alumno)
                    .order_by('-fecha_lectura')
                    .first()
                )
                model_class = ExamenContexto
            elif materia == 'lengua':
                lectura = (
                    ExamenLengua.objects.using('Evaluacion')
                    .filter(alumno=alumno)
                    .order_by('-fecha_lectura')
                    .first()
                )
                model_class = ExamenLengua
            else:
                lectura = (
                    ExamenMatematica.objects.using('Evaluacion')
                    .filter(alumno=alumno, tipo_examen=materia)
                    .order_by('-fecha_lectura')
                    .first()
                )
                model_class = ExamenMatematica
            if lectura is None:
                lectura = model_class(alumno=alumno, **defaults)
            else:
                for field, value in defaults.items():
                    setattr(lectura, field, value)
            # Además de la validación estricta del JSON, aplica las reglas del
            # propio modelo antes de escribir en la base dedicada.
            lectura.clean()
            lectura.save(using='Evaluacion')

    session_key = _session_key_examenes_guardados(id_alumno)
    guardados = set(request.session.get(session_key, []))
    guardados.add(materia)
    request.session[session_key] = sorted(guardados)

    return JsonResponse({
        'ok': True,
        'modo_simulacion': SIMULATION_MODE,
        'lectura_public_id': str(lectura.public_id) if lectura else None,
        'redirect_url': reverse(
            'evaluaciones_educativas:omr_lector:seleccionar_materia',
            args=[id_alumno],
        ),
    })


# ─── 4. Lista de lecturas ─────────────────────────────────────────────────────

# @login_required()
def lista_lecturas(request):
    """
    Historial de todas las lecturas OMR.
    Soporta filtrado por cueanexo y búsqueda por nombre/apellido de alumno.
    """
    if SIMULATION_MODE:
        raise PermissionDenied('El historial no está disponible durante la simulación.')

    query = request.GET.get('q', '').strip()
    cueanexo = request.GET.get('cueanexo', '').strip()

    def aplicar_filtros(queryset):
        if cueanexo:
            queryset = queryset.filter(alumno__seccion__grado__cueanexo=cueanexo)
        if query:
            queryset = queryset.filter(
                Q(alumno__nombre__icontains=query) |
                Q(alumno__apellido__icontains=query) |
                Q(alumno__dni__icontains=query)
            )
        return queryset

    matematica = aplicar_filtros(
        ExamenMatematica.objects.using('Evaluacion').exclude(tipo_examen='contexto')
    )
    lengua_qs = aplicar_filtros(ExamenLengua.objects.using('Evaluacion'))
    contexto_qs = aplicar_filtros(ExamenContexto.objects.using('Evaluacion'))
    indice = matematica.order_by().annotate(
        origen=Value('matematica', output_field=CharField()),
    ).values('public_id', 'fecha_lectura', 'origen').union(
        lengua_qs.order_by().annotate(
            origen=Value('lengua', output_field=CharField()),
        ).values('public_id', 'fecha_lectura', 'origen'),
        contexto_qs.order_by().annotate(
            origen=Value('contexto', output_field=CharField()),
        ).values('public_id', 'fecha_lectura', 'origen'),
        all=True,
    ).order_by('-fecha_lectura')

    paginator = Paginator(indice, 25)
    page_obj = paginator.get_page(request.GET.get('page'))
    filas = list(page_obj.object_list)
    ids_matematica = [fila['public_id'] for fila in filas if fila['origen'] == 'matematica']
    ids_lengua = [fila['public_id'] for fila in filas if fila['origen'] == 'lengua']
    ids_contexto = [fila['public_id'] for fila in filas if fila['origen'] == 'contexto']
    relaciones = (
        'alumno', 'alumno__seccion', 'alumno__seccion__grado',
        'alumno__seccion__grado__Establecimiento',
    )
    objetos = {
        ('matematica', lectura.public_id): lectura
        for lectura in matematica.filter(public_id__in=ids_matematica).select_related(*relaciones)
    }
    objetos.update({
        ('lengua', lectura.public_id): lectura
        for lectura in lengua_qs.filter(public_id__in=ids_lengua).select_related(*relaciones)
    })
    objetos.update({
        ('contexto', lectura.public_id): lectura
        for lectura in contexto_qs.filter(public_id__in=ids_contexto).select_related(*relaciones)
    })
    page_obj.object_list = [
        objetos[(fila['origen'], fila['public_id'])]
        for fila in filas
        if (fila['origen'], fila['public_id']) in objetos
    ]

    establecimientos = EstablecimientosDiagnostico_Ingreso_2026.objects.using(
        'Evaluacion'
    ).order_by('escuela')

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

# @login_required()
def detalle_lectura(request, public_id):
    """
    Muestra el detalle completo de una lectura OMR específica.
    Permite al docente editar y corregir respuestas desde esta vista también.
    """
    if SIMULATION_MODE:
        raise PermissionDenied('El detalle no está disponible durante la simulación.')

    relaciones = (
        'alumno', 'alumno__seccion', 'alumno__seccion__grado',
        'alumno__seccion__grado__Establecimiento',
    )
    lectura = (
        ExamenMatematica.objects.using('Evaluacion')
        .exclude(tipo_examen='contexto')
        .select_related(*relaciones)
        .filter(public_id=public_id)
        .first()
    )
    if lectura is None:
        lectura = (
            ExamenLengua.objects.using('Evaluacion')
            .select_related(*relaciones)
            .filter(public_id=public_id)
            .first()
        )
    if lectura is None:
        lectura = (
            ExamenContexto.objects.using('Evaluacion')
            .select_related(*relaciones)
            .filter(public_id=public_id)
            .first()
        )
    if lectura is None:
        raise Http404('No se encontró el examen solicitado.')

    # Construir lista de ítems con respuesta y confianza para el template
    items_detalle = []
    confianza = lectura.confianza_json or {}
    for i in range(1, lectura.cantidad_items + 1):
        field_name = (
            lectura.campo_item(i)
            if lectura.tipo_examen == 'lengua' else f'item_{i}'
        )
        item_label = (
            lectura.etiqueta_item(i)
            if lectura.tipo_examen == 'lengua' else str(i)
        )
        resp = getattr(lectura, field_name, '')
        conf = confianza.get(str(i), None)
        items_detalle.append({
            'num': item_label,
            'respuesta': resp,
            'seleccionadas': resp.split(',') if resp else [],
            'opciones': (
                list('ABCDEF'[:OPCIONES_POR_ITEM_CONTEXTO[i - 1]])
                if lectura.tipo_examen == 'contexto' else ['A', 'B', 'C', 'D']
            ),
            'confianza': conf,
            'dudoso': conf is not None and conf < 50,
            'puntaje': (
                lectura.puntajes_json.get(item_label)
                if lectura.tipo_examen == 'lengua' else None
            ),
        })

    contexto = {
        'lectura': lectura,
        'items_detalle': items_detalle,
    }
    return render(request, 'omr_lector/detalle_lectura.html', contexto)


# ─── 6. Procesar imagen con OpenCV (backend) ──────────────────────────────────

@require_POST
# @login_required()
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
    tipo_examen = request.POST.get('tipo_examen', '').strip()
    if not materia_valida(tipo_examen):
        return _json_error('El tipo de examen no es válido.', 'INVALID_EXAM_TYPE')

    try:
        from apps.evaluaciones_educativas.views.omr_utils import procesar_imagen
        imagen_bytes = _validar_imagen_subida(imagen_file)
        resultado = procesar_imagen(imagen_bytes, tipo_examen=tipo_examen)
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
