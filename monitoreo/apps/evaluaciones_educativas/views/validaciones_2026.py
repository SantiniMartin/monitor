from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.views.decorators.http import require_POST

from apps.evaluaciones_educativas.models.validaciones_2026 import (
    ValReferenteCargaTemporal,
    ValEstablecimiento,
    ValGrado,
    ValSeccion,
    ValCabecera,
    ValHistorialMatriculas,
    ValHistorialCambiosEstablecimiento,
)
from apps.evaluaciones_educativas.forms.validaciones_2026 import (
    JustificacionCambioMatriculaForm,
    JustificacionNoExisteForm,
    SeleccionCabeceraForm,
)


# ---------------------------------------------------------------------------
# VISTA PRINCIPAL: Lista de secciones para validar
# ---------------------------------------------------------------------------
# @login_required
def lista_validacion(request):
    """
    Vista principal del proceso de validación.
    
    1. Obtiene el CUIL del usuario logueado (username).
    2. Busca las regiones del referente en ReferenteCargaTemporal.
    3. Muestra todas las secciones (con grado y establecimiento) de esas regiones.
    4. Calcula si todas las secciones están procesadas (para mostrar el botón de cabecera).
    """
    # ── CUIL HARDCODEADO PARA PRUEBAS ──────────────────────────────
    cuil = '27999999999'
    # usuario = request.user
    # cuil = usuario.username
    # ───────────────────────────────────────────────────────────────

    # 1. Obtener regiones del referente
    regiones_qs = ValReferenteCargaTemporal.objects.filter(cuil=cuil).values_list('region', flat=True).distinct()
    regiones = list(regiones_qs)

    if not regiones:
        # Si el CUIL no está en la tabla, mostramos error
        contexto = {
            'sin_acceso': True,
            'cuil': cuil,
            'secciones': [],
            'todas_procesadas': False,
            'forma_cabecera': SeleccionCabeceraForm(),
        }
        return render(request, 'validaciones_2026/lista.html', contexto)

    # 2. Obtener todas las secciones de esas regiones, con datos relacionados
    secciones = (
        ValSeccion.objects
        .filter(grado__establecimiento__region__in=regiones)
        .select_related('grado', 'grado__establecimiento', 'cabecera')
        .order_by(
            'grado__establecimiento__region',
            'grado__establecimiento__escuela',
            'grado__nombre_grado',
            'seccion',
            'turno',
        )
    )

    total = secciones.count()
    pendientes = secciones.filter(estado_validacion='PENDIENTE').count()
    todas_procesadas = (total > 0) and (pendientes == 0)

    forma_cabecera = SeleccionCabeceraForm()

    contexto = {
        'sin_acceso': False,
        'cuil': cuil,
        'regiones': regiones,
        'secciones': secciones,
        'total': total,
        'pendientes': pendientes,
        'todas_procesadas': todas_procesadas,
        'forma_cabecera': forma_cabecera,
    }
    return render(request, 'validaciones_2026/lista.html', contexto)


# ---------------------------------------------------------------------------
# VISTA: Aprobar sección (guarda matrícula, con o sin cambio)
# ---------------------------------------------------------------------------
# @login_required
@require_POST
def aprobar_seccion(request, seccion_public_id):
    """
    Aprueba una seccion y guarda su matricula.
    """
    seccion = get_object_or_404(ValSeccion, public_id=seccion_public_id)
    # ── HARDCODEADO PARA PRUEBAS ──
    usuario = 'prueba'
    # usuario = request.user.username

    matricula_nueva_str = request.POST.get('matricula_nueva', '').strip()
    justificacion = request.POST.get('justificacion', '').strip()

    # Validar que la matrícula sea un número
    try:
        matricula_nueva = int(matricula_nueva_str) if matricula_nueva_str != '' else None
    except ValueError:
        return JsonResponse({'ok': False, 'error': 'La matrícula debe ser un número entero.'}, status=400)

    with transaction.atomic():
        matricula_anterior = seccion.matricula

        # Si cambió la matrícula, exigimos justificación y guardamos historial
        if matricula_nueva != matricula_anterior:
            if not justificacion:
                return JsonResponse(
                    {'ok': False, 'error': 'Debés justificar el cambio de matrícula.', 'necesita_justificacion': True},
                    status=400
                )
            ValHistorialMatriculas.objects.create(
                seccion=seccion,
                matricula_anterior=matricula_anterior,
                matricula_nueva=matricula_nueva,
                justificacion=justificacion,
                usuario_cambio=usuario,
            )

        # Actualizar la sección
        seccion.matricula = matricula_nueva
        seccion.estado_validacion = 'APROBADO'
        seccion.usuario_ultima_modificacion = usuario
        seccion.save()

    return JsonResponse({
        'ok': True,
        'estado': 'APROBADO',
        'matricula': matricula_nueva,
        'seccion_id': str(seccion_public_id),
    })


# ---------------------------------------------------------------------------
# VISTA: Marcar sección como "No existe" (✖)
# ---------------------------------------------------------------------------
# @login_required
@require_POST
def marcar_no_existe(request, seccion_public_id):
    """
    Marca una seccion como 'NO_EXISTE' y guarda la justificacion en el historial.
    """
    seccion = get_object_or_404(ValSeccion, public_id=seccion_public_id)
    # ── HARDCODEADO PARA PRUEBAS ──
    usuario = 'prueba'
    # usuario = request.user.username

    justificacion = request.POST.get('justificacion', '').strip()

    if not justificacion:
        return JsonResponse({'ok': False, 'error': 'La justificación es obligatoria.'}, status=400)

    with transaction.atomic():
        ValHistorialCambiosEstablecimiento.objects.create(
            seccion=seccion,
            justificacion=justificacion,
            usuario=usuario,
        )
        seccion.estado_validacion = 'NO_EXISTE'
        seccion.usuario_ultima_modificacion = usuario
        seccion.save()

    return JsonResponse({
        'ok': True,
        'estado': 'NO_EXISTE',
        'seccion_id': str(seccion_public_id),
    })


# ---------------------------------------------------------------------------
# VISTA: Restablecer sección a PENDIENTE (botón ✏ Editar)
# ---------------------------------------------------------------------------
# @login_required
@require_POST
def editar_seccion(request, seccion_public_id):
    """
    Vuelve una seccion al estado PENDIENTE para que el usuario pueda re-procesarla.
    """
    seccion = get_object_or_404(ValSeccion, public_id=seccion_public_id)
    # ── HARDCODEADO PARA PRUEBAS ──
    usuario = 'prueba'
    # usuario = request.user.username

    seccion.estado_validacion = 'PENDIENTE'
    seccion.cabecera = None
    seccion.usuario_ultima_modificacion = usuario
    seccion.save()

    return JsonResponse({
        'ok': True,
        'estado': 'PENDIENTE',
        'seccion_id': str(seccion_public_id),
    })


# ---------------------------------------------------------------------------
# VISTA: Asignar cabecera a sección (pantalla final)
# ---------------------------------------------------------------------------
# @login_required
@require_POST
def asignar_cabecera(request, seccion_public_id):
    """
    Asigna una cabecera a la seccion en la pantalla final.
    """
    seccion = get_object_or_404(ValSeccion, public_id=seccion_public_id)
    # ── HARDCODEADO PARA PRUEBAS ──
    usuario = 'prueba'
    # usuario = request.user.username

    cabecera_id = request.POST.get('cabecera', '').strip()

    if not cabecera_id:
        return JsonResponse({'ok': False, 'error': 'Debés seleccionar una cabecera.'}, status=400)

    cabecera = get_object_or_404(ValCabecera, pk=cabecera_id)

    seccion.cabecera = cabecera
    seccion.usuario_ultima_modificacion = usuario
    seccion.save()

    return JsonResponse({
        'ok': True,
        'seccion_id': str(seccion_public_id),
        'cabecera_nombre': str(cabecera),
        'cabecera_id': cabecera.pk,
    })
