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

import json
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_GET
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from django.db.models import Q
from django.utils import timezone

from apps.evaluaciones_educativas.models.fluidez_2026 import AlumnoFluidez2026, SeccionFluidez2026, GradoFluidez2026, EstablecimientosFluidez2026
from apps.evaluaciones_educativas.models.omr_lector import LecturaOMR


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
    alumno = get_object_or_404(
        AlumnoFluidez2026.objects.using('Evaluacion'),
        public_id=alumno_public_id,
    )

    try:
        payload = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'ok': False, 'error': 'JSON inválido'}, status=400)

    respuestas = payload.get('respuestas', {})
    confianza = payload.get('confianza', {})
    modelo_examen = payload.get('modelo_examen', '')
    revisado = payload.get('revisado_manualmente', False)
    observaciones = payload.get('observaciones', '')

    # Validar que las respuestas sean A/B/C/D o vacío
    opciones_validas = {'A', 'B', 'C', 'D', ''}
    for item_num, resp in respuestas.items():
        if resp not in opciones_validas:
            return JsonResponse(
                {'ok': False, 'error': f'Respuesta inválida en ítem {item_num}: "{resp}"'},
                status=400,
            )

    # Crear o actualizar la lectura OMR
    # Si ya existe una lectura para este alumno, se reemplaza (para permitir re-escaneo)
    lectura, creada = LecturaOMR.objects.using('Evaluacion').update_or_create(
        alumno=alumno,
        defaults={
            'modelo_examen': modelo_examen[:1] if modelo_examen else '',
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
            'confianza_json': {str(k): int(v) for k, v in confianza.items()} if confianza else None,
            'revisado_manualmente': bool(revisado),
            'observaciones': observaciones,
            'encargado_carga': str(request.user) if request.user.is_authenticated else '',
        }
    )

    return JsonResponse({
        'ok': True,
        'creada': creada,
        'lectura_public_id': str(lectura.public_id),
        'redirect_url': f'/evaluaciones_educativas/omr/historial/{lectura.public_id}/',
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

    contexto = {
        'lecturas': lecturas[:100],
        'query': query,
        'cueanexo': cueanexo,
        'establecimientos': establecimientos,
        'total': lecturas.count(),
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
