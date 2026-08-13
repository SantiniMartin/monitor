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


# ---------------------------------------------------------------------------
# HELPER: CUIL del usuario (hardcodeado para pruebas)
# ---------------------------------------------------------------------------
def _get_cuil(request):
    return '27999999999'
    # return request.user.username


# ---------------------------------------------------------------------------
# PASO 0: Seleccionar región
# ---------------------------------------------------------------------------
# @login_required
def seleccionar_region(request):
    """
    Paso 0: muestra las regiones disponibles para el referente y permite
    elegir con cuál trabajar. Es el punto de entrada del flujo.
    """
    cuil = _get_cuil(request)

    regiones_qs = (
        ValReferenteCargaTemporal.objects
        .filter(cuil=cuil)
        .values('region')
        .distinct()
        .order_by('region')
    )
    regiones = list(regiones_qs.values_list('region', flat=True))

    if not regiones:
        return render(request, 'validaciones_2026/seleccionar_region.html', {
            'sin_acceso': True,
            'cuil': cuil,
        })

    # Si solo hay una región, redirigir directamente
    if len(regiones) == 1:
        return redirect(
            'evaluaciones_educativas:validaciones_2026:lista_establecimientos',
            region=regiones[0]
        )

    # Estadísticas por región para mostrar progreso en las tarjetas
    regiones_info = []
    for region in regiones:
        ests = ValEstablecimiento.objects.filter(region=region)
        total_r      = ests.count()
        procesados_r = ests.exclude(participa_aprender=None).count()
        regiones_info.append({
            'nombre':      region,
            'total':       total_r,
            'procesados':  procesados_r,
            'sin_procesar': total_r - procesados_r,
            'pct':         round((procesados_r / total_r) * 100) if total_r else 0,
        })

    return render(request, 'validaciones_2026/seleccionar_region.html', {
        'sin_acceso':   False,
        'cuil':         cuil,
        'regiones_info': regiones_info,
    })


# ---------------------------------------------------------------------------
# PASO 1: Lista de establecimientos de una región (tarjetas)
# ---------------------------------------------------------------------------
# @login_required
def lista_establecimientos(request, region):
    """
    Paso 1: muestra los establecimientos de la región elegida en tarjetas.
    Cada tarjeta refleja el estado de participación (None / True / False)
    y, si participa, muestra la cabecera asignada.
    """
    cuil = _get_cuil(request)

    # Verificar que el referente tiene acceso a esta región
    regiones_autorizadas = list(
        ValReferenteCargaTemporal.objects
        .filter(cuil=cuil)
        .values_list('region', flat=True)
        .distinct()
    )
    if not regiones_autorizadas:
        return render(request, 'validaciones_2026/establecimientos.html', {
            'sin_acceso': True,
            'cuil': cuil,
        })
    if region not in regiones_autorizadas:
        return redirect('evaluaciones_educativas:validaciones_2026:lista')

    # Establecimientos de la región elegida
    establecimientos = (
        ValEstablecimiento.objects
        .filter(region=region)
        .select_related('cabecera')
        .order_by('escuela')
    )

    # Contadores (antes de convertir a lista)
    total_est  = establecimientos.count()
    procesados = establecimientos.exclude(participa_aprender=None).count()

    # Adjuntar stats de secciones directamente al objeto
    establecimientos_list = list(establecimientos)
    for est in establecimientos_list:
        secciones_qs = ValSeccion.objects.filter(grado__establecimiento=est)
        total_s = secciones_qs.count()
        pendientes_s = secciones_qs.filter(estado_validacion='PENDIENTE').count()
        est.total_secciones      = total_s
        est.pendientes_secciones = pendientes_s
        est.completadas_secciones = total_s - pendientes_s

    sin_procesar = total_est - procesados
    porcentaje_progreso = round((procesados / total_est) * 100) if total_est else 0

    cabeceras = ValCabecera.objects.all().order_by('nombre_cabecera')

    contexto = {
        'sin_acceso': False,
        'cuil': cuil,
        'region_actual': region,
        'regiones_autorizadas': regiones_autorizadas,
        'establecimientos': establecimientos_list,
        'total_est': total_est,
        'procesados': procesados,
        'sin_procesar': sin_procesar,
        'porcentaje_progreso': porcentaje_progreso,
        'cabeceras': cabeceras,
    }
    return render(request, 'validaciones_2026/establecimientos.html', contexto)


# ---------------------------------------------------------------------------
# PASO 1 → ACCIÓN: Marcar participación del establecimiento
# ---------------------------------------------------------------------------
# @login_required
@require_POST
def set_participacion(request, cueanexo):
    """
    POST JSON: marca participa_aprender = True o False en ValEstablecimiento.
    Body esperado: { "participa": true | false, "justificacion": "opcional" }
    """
    est = get_object_or_404(ValEstablecimiento, cueanexo=cueanexo)
    participa_str = request.POST.get('participa', '').strip().lower()
    justificacion = request.POST.get('justificacion', '').strip()

    if participa_str not in ('true', 'false'):
        return JsonResponse({'ok': False, 'error': 'Valor inválido. Se esperaba true o false.'}, status=400)

    est.participa_aprender = (participa_str == 'true')

    # Si no participa, limpiamos la cabecera asignada
    if not est.participa_aprender:
        est.cabecera = None

    est.save()

    # Guardar en el historial
    if justificacion:
        ValHistorialCambiosEstablecimiento.objects.create(
            establecimiento=est,
            justificacion=justificacion,
            usuario=request.user.username if request.user.is_authenticated else _get_cuil(request)
        )

    return JsonResponse({
        'ok': True,
        'cueanexo': cueanexo,
        'participa': est.participa_aprender,
    })


# ---------------------------------------------------------------------------
# PASO 1 → MODAL: Asignar cabecera al establecimiento
# ---------------------------------------------------------------------------
# @login_required
@require_POST
def set_cabecera_establecimiento(request, cueanexo):
    """
    POST JSON: asigna una cabecera al establecimiento.
    Body esperado: { "cabecera_id": <int> }
    """
    est = get_object_or_404(ValEstablecimiento, cueanexo=cueanexo)
    cabecera_id = request.POST.get('cabecera_id', '').strip()

    if not cabecera_id:
        return JsonResponse({'ok': False, 'error': 'Debés seleccionar una cabecera.'}, status=400)

    cabecera = get_object_or_404(ValCabecera, pk=cabecera_id)

    est.cabecera = cabecera
    est.participa_aprender = True  # asegurar coherencia
    est.save()

    return JsonResponse({
        'ok': True,
        'cueanexo': cueanexo,
        'cabecera_id': cabecera.pk,
        'cabecera_nombre': cabecera.nombre_cabecera,
        'cabecera_localidad': cabecera.localidad or '',
        'cabecera_codigo_departamento': cabecera.codigo_departamento or '',
        'cabecera_direccion': cabecera.direccion or '',
    })


# ---------------------------------------------------------------------------
# PASO 3: Lista de secciones de un establecimiento
# ---------------------------------------------------------------------------
# @login_required
def lista_secciones(request, cueanexo):
    """
    Paso 3: muestra todas las secciones de un establecimiento,
    agrupadas por grado, con botones Aprobar / Sin matrícula / Modificar.
    """
    est = get_object_or_404(ValEstablecimiento.objects.select_related('cabecera'), cueanexo=cueanexo)

    # Solo puede acceder si el establecimiento participa
    if est.participa_aprender is not True:
        return redirect('evaluaciones_educativas:validaciones_2026:lista')

    secciones = (
        ValSeccion.objects
        .filter(grado__establecimiento=est)
        .select_related('grado', 'cabecera')
        .prefetch_related('historial_matriculas')
        .order_by('grado__nombre_grado', 'seccion', 'turno')
    )

    total = secciones.count()
    pendientes = secciones.filter(estado_validacion='PENDIENTE').count()
    todas_procesadas = (total > 0) and (pendientes == 0)

    contexto = {
        'establecimiento': est,
        'secciones': secciones,
        'total': total,
        'pendientes': pendientes,
        'todas_procesadas': todas_procesadas,
    }
    return render(request, 'validaciones_2026/secciones.html', contexto)


# ---------------------------------------------------------------------------
# ACCIÓN: Aprobar sección (matrícula OK, con o sin cambio)
# ---------------------------------------------------------------------------
# @login_required
@require_POST
def aprobar_seccion(request, seccion_public_id):
    """
    Aprueba una sección y guarda su matrícula.
    Si la matrícula cambió respecto al historial, exige justificación.
    """
    seccion = get_object_or_404(ValSeccion, public_id=seccion_public_id)
    usuario = _get_cuil(request)

    matricula_nueva_str = request.POST.get('matricula_nueva', '').strip()
    justificacion = request.POST.get('justificacion', '').strip()

    try:
        matricula_nueva = int(matricula_nueva_str) if matricula_nueva_str != '' else None
    except ValueError:
        return JsonResponse({'ok': False, 'error': 'La matrícula debe ser un número entero.'}, status=400)

    with transaction.atomic():
        matricula_anterior = seccion.matricula

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
# ACCIÓN: Marcar sección como "Sin matrícula" (antes "No existe")
# ---------------------------------------------------------------------------
# @login_required
@require_POST
def marcar_sin_matricula(request, seccion_public_id):
    """
    Marca una sección como SIN_MATRICULA y guarda la justificación.
    Muestra el dato del historial (última matrícula registrada) al usuario.
    """
    seccion = get_object_or_404(ValSeccion, public_id=seccion_public_id)
    usuario = _get_cuil(request)

    justificacion = request.POST.get('justificacion', '').strip()

    if not justificacion:
        return JsonResponse({'ok': False, 'error': 'La justificación es obligatoria.'}, status=400)

    with transaction.atomic():
        ValHistorialCambiosEstablecimiento.objects.create(
            seccion=seccion,
            justificacion=justificacion,
            usuario=usuario,
        )
        seccion.estado_validacion = 'SIN_MATRICULA'
        seccion.matricula = None
        seccion.usuario_ultima_modificacion = usuario
        seccion.save()

    return JsonResponse({
        'ok': True,
        'estado': 'SIN_MATRICULA',
        'seccion_id': str(seccion_public_id),
    })


# ---------------------------------------------------------------------------
# ACCIÓN: Modificar matrícula con justificación
# ---------------------------------------------------------------------------
# @login_required
@require_POST
def modificar_seccion(request, seccion_public_id):
    """
    Modifica la matrícula de una sección con justificación obligatoria.
    Guarda historial del cambio. El estado queda en MODIFICADO.
    """
    seccion = get_object_or_404(ValSeccion, public_id=seccion_public_id)
    usuario = _get_cuil(request)

    matricula_nueva_str = request.POST.get('matricula_nueva', '').strip()
    justificacion = request.POST.get('justificacion', '').strip()

    if not justificacion:
        return JsonResponse({'ok': False, 'error': 'La justificación es obligatoria.'}, status=400)

    try:
        matricula_nueva = int(matricula_nueva_str) if matricula_nueva_str != '' else None
    except ValueError:
        return JsonResponse({'ok': False, 'error': 'La matrícula debe ser un número entero.'}, status=400)

    with transaction.atomic():
        matricula_anterior = seccion.matricula
        ValHistorialMatriculas.objects.create(
            seccion=seccion,
            matricula_anterior=matricula_anterior,
            matricula_nueva=matricula_nueva,
            justificacion=justificacion,
            usuario_cambio=usuario,
        )
        seccion.matricula = matricula_nueva
        seccion.estado_validacion = 'MODIFICADO'
        seccion.usuario_ultima_modificacion = usuario
        seccion.save()

    return JsonResponse({
        'ok': True,
        'estado': 'MODIFICADO',
        'matricula': matricula_nueva,
        'seccion_id': str(seccion_public_id),
    })


# ---------------------------------------------------------------------------
# ACCIÓN: Restablecer sección a PENDIENTE (botón Editar)
# ---------------------------------------------------------------------------
# @login_required
@require_POST
def editar_seccion(request, seccion_public_id):
    """
    Vuelve una sección al estado PENDIENTE para re-procesarla.
    """
    seccion = get_object_or_404(ValSeccion, public_id=seccion_public_id)
    usuario = _get_cuil(request)

    seccion.estado_validacion = 'PENDIENTE'
    seccion.usuario_ultima_modificacion = usuario
    seccion.save()

    return JsonResponse({
        'ok': True,
        'estado': 'PENDIENTE',
        'seccion_id': str(seccion_public_id),
    })
