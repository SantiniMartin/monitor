from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.views.decorators.http import require_POST
from django.urls import reverse

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
# HELPERS
# ---------------------------------------------------------------------------
def _get_cuil(request):
    usuario = request.user
    cuil = usuario.username
    return '20123456789'


def _get_referente(cuil):
    """Obtiene el primer referente con ese CUIL (puede ser None)."""
    return ValReferenteCargaTemporal.objects.filter(cuil=cuil).first()



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

    regiones = list(
        ValReferenteCargaTemporal.objects
        .filter(cuil=cuil)
        .values_list('region', flat=True)
        .distinct()
        .order_by('region')
    )

    if not regiones:
        return render(request, 'validaciones_2026/seleccionar_region.html', {
            'sin_acceso': True,
            'cuil': cuil,
        })

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
    Estados: sin_validar (amarillo) | validado (verde) | no_participa (rojo).
    """
    cuil = _get_cuil(request)

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

    from django.db.models import Count, Q

    establecimientos = (
        ValEstablecimiento.objects
        .filter(region=region)
        .select_related('cabecera')
        .annotate(
            total_secciones_annotated=Count('grados__secciones'),
            pendientes_secciones_annotated=Count(
                'grados__secciones',
                filter=Q(grados__secciones__estado_validacion='PENDIENTE')
            )
        )
        .order_by('escuela')
    )

    total_est  = establecimientos.count()
    procesados = establecimientos.exclude(participa_aprender=None).count()

    establecimientos_list = list(establecimientos)
    for est in establecimientos_list:
        est.total_secciones       = est.total_secciones_annotated
        est.pendientes_secciones  = est.pendientes_secciones_annotated
        est.completadas_secciones = est.total_secciones_annotated - est.pendientes_secciones_annotated

    sin_procesar = total_est - procesados
    porcentaje_progreso = round((procesados / total_est) * 100) if total_est else 0

    cabeceras = ValCabecera.objects.all().order_by('nombre_cabecera')

    # Mensaje de advertencia si viene de secciones sin agregar ninguna
    sin_secciones_cue = request.GET.get('sin_secciones')

    contexto = {
        'sin_acceso':           False,
        'cuil':                 cuil,
        'region_actual':        region,
        'regiones_autorizadas': regiones_autorizadas,
        'establecimientos':     establecimientos_list,
        'total_est':            total_est,
        'procesados':           procesados,
        'sin_procesar':         sin_procesar,
        'porcentaje_progreso':  porcentaje_progreso,
        'cabeceras':            cabeceras,
        'sin_secciones_cue':    sin_secciones_cue,
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
    Body esperado: { "participa": "true"|"false", "motivo": "<str>" }
    """
    cuil = _get_cuil(request)
    est = ValEstablecimiento.objects.for_referente(cuil, cueanexo)
    if not est:
        return JsonResponse({'ok': False, 'error': 'Sin acceso a este establecimiento.'}, status=403)

    participa_str = request.POST.get('participa', '').strip().lower()
    motivo        = request.POST.get('motivo', '').strip()

    if participa_str not in ('true', 'false'):
        return JsonResponse({'ok': False, 'error': 'Valor inválido. Se esperaba true o false.'}, status=400)

    referente = _get_referente(cuil)

    with transaction.atomic():
        est.participa_aprender = (participa_str == 'true')

        if not est.participa_aprender:
            est.cabecera = None
            est.carga_completa = False
            est.motivo_no_participa = motivo or 'No especificado'
        else:
            est.motivo_no_participa = None

        est.save()

        texto_historial = motivo if motivo else ('Participa en Aprender' if est.participa_aprender else 'No participa en Aprender')
        ValHistorialCambiosEstablecimiento.objects.create(
            establecimiento=est,
            justificacion=texto_historial,
            usuario=cuil,
            referente=referente,
        )

    return JsonResponse({
        'ok': True,
        'cueanexo': cueanexo,
        'participa': est.participa_aprender,
        'motivo': est.motivo_no_participa or '',
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
    Responde con redirect_url para que el frontend redirija a secciones.
    """
    cuil = _get_cuil(request)
    est = ValEstablecimiento.objects.for_referente(cuil, cueanexo)
    if not est:
        return JsonResponse({'ok': False, 'error': 'Sin acceso a este establecimiento.'}, status=403)

    cabecera_id = request.POST.get('cabecera_id', '').strip()
    if not cabecera_id:
        return JsonResponse({'ok': False, 'error': 'Debés seleccionar una cabecera.'}, status=400)

    cabecera = get_object_or_404(ValCabecera, pk=cabecera_id)
    referente = _get_referente(cuil)

    with transaction.atomic():
        est.cabecera = cabecera
        est.participa_aprender = True  # coherencia
        est.save()

        ValHistorialCambiosEstablecimiento.objects.create(
            establecimiento=est,
            justificacion=f'Cabecera asignada: {cabecera.nombre_cabecera}',
            usuario=cuil,
            referente=referente,
        )

    redirect_url = reverse(
        'evaluaciones_educativas:validaciones_2026:lista_secciones',
        kwargs={'cueanexo': cueanexo}
    )

    return JsonResponse({
        'ok': True,
        'cueanexo': cueanexo,
        'cabecera_id': cabecera.pk,
        'cabecera_nombre': cabecera.nombre_cabecera,
        'cabecera_localidad': cabecera.localidad or '',
        'cabecera_codigo_departamento': cabecera.codigo_departamento or '',
        'cabecera_direccion': cabecera.direccion or '',
        'redirect_url': redirect_url,
    })


# ---------------------------------------------------------------------------
# ACCIÓN: Revertir establecimiento a sin validar si vuelve sin secciones
# ---------------------------------------------------------------------------
# @login_required
@require_POST
def revertir_sin_secciones(request, cueanexo):
    """
    Cuando el usuario abandona la página de secciones sin haber agregado ninguna,
    se llama este endpoint para revertir el establecimiento a 'sin validar'.
    """
    cuil = _get_cuil(request)
    est = ValEstablecimiento.objects.for_referente(cuil, cueanexo)
    if not est:
        return JsonResponse({'ok': False, 'error': 'Sin acceso.'}, status=403)

    total_secciones = ValSeccion.objects.filter(grado__establecimiento=est).count()
    if total_secciones > 0:
        # Ya tiene secciones, no revertir
        return JsonResponse({'ok': False, 'tiene_secciones': True})

    referente = _get_referente(cuil)

    with transaction.atomic():
        est.participa_aprender = None
        est.carga_completa = False
        est.save()

        ValHistorialCambiosEstablecimiento.objects.create(
            establecimiento=est,
            justificacion='Revertido a sin validar: no se agregaron secciones.',
            usuario=cuil,
            referente=referente,
        )

    return JsonResponse({'ok': True})


# ---------------------------------------------------------------------------
# PASO 3: Lista de secciones de un establecimiento
# ---------------------------------------------------------------------------
# @login_required
def lista_secciones(request, cueanexo):
    """
    Muestra todas las secciones de un establecimiento, con botones Validar /
    Deshabilitar / Modificar matrícula y el botón Validación completa.
    """
    cuil = _get_cuil(request)
    est = ValEstablecimiento.objects.for_referente(cuil, cueanexo)
    if not est:
        return redirect('evaluaciones_educativas:validaciones_2026:lista')

    if est.participa_aprender is not True:
        return redirect('evaluaciones_educativas:validaciones_2026:lista')

    secciones = (
        ValSeccion.objects
        .filter(grado__establecimiento=est)
        .select_related('grado')
        .prefetch_related('historial_matriculas')
        .order_by('grado__nombre_grado', 'seccion', 'turno')
    )

    total          = secciones.count()
    pendientes     = secciones.filter(estado_validacion='PENDIENTE').count()
    deshabilitadas = secciones.filter(estado_validacion='DESHABILITADO').count()
    todas_procesadas      = (total > 0) and (pendientes == 0)
    todas_deshabilitadas  = (total > 0) and (deshabilitadas == total)
    sin_secciones         = (total == 0)

    contexto = {
        'establecimiento':      est,
        'secciones':            secciones,
        'total':                total,
        'pendientes':           pendientes,
        'deshabilitadas':       deshabilitadas,
        'todas_procesadas':     todas_procesadas,
        'todas_deshabilitadas': todas_deshabilitadas,
        'sin_secciones':        sin_secciones,
        'cuil':                 cuil,
        # Opciones para el modal de crear sección
        'opciones_seccion': ValSeccion.OPCIONES_SECCION,
        'opciones_turno':   ValSeccion.OPCIONES_TURNO,
        'opciones_grado':   ValGrado.OPCIONES_GRADO,
    }
    return render(request, 'validaciones_2026/secciones.html', contexto)


# ---------------------------------------------------------------------------
# ACCIÓN: Crear sección (crea el grado si no existe)
# ---------------------------------------------------------------------------
# @login_required
@require_POST
def crear_seccion(request, cueanexo):
    """
    Crea una nueva sección en el establecimiento.
    Si el grado '3er Año/Grado' no existe, lo crea con grado_creado=True.
    La sección se crea directamente en estado APROBADO con seccion_creada=True.
    """
    cuil = _get_cuil(request)
    est = ValEstablecimiento.objects.for_referente(cuil, cueanexo)
    if not est:
        return JsonResponse({'ok': False, 'error': 'Sin acceso.'}, status=403)

    if est.participa_aprender is not True:
        return JsonResponse({'ok': False, 'error': 'El establecimiento no participa en el programa.'}, status=400)

    nombre_seccion = request.POST.get('seccion', '').strip()
    turno          = request.POST.get('turno', '').strip()
    matricula_str  = request.POST.get('matricula', '').strip()
    motivo         = request.POST.get('motivo', '').strip()
    nombre_grado   = request.POST.get('nombre_grado', '3er Año/Grado').strip()

    # Validar sección
    secciones_validas = [s[0] for s in ValSeccion.OPCIONES_SECCION]
    if nombre_seccion not in secciones_validas:
        return JsonResponse({'ok': False, 'error': 'Sección inválida.'}, status=400)

    # Validar turno
    turnos_validos = [t[0] for t in ValSeccion.OPCIONES_TURNO]
    if turno not in turnos_validos:
        return JsonResponse({'ok': False, 'error': 'Turno inválido.'}, status=400)

    # Validar grado
    grados_validos = [g[0] for g in ValGrado.OPCIONES_GRADO]
    if nombre_grado not in grados_validos:
        return JsonResponse({'ok': False, 'error': 'Grado inválido.'}, status=400)

    # Validar matrícula
    try:
        matricula = int(matricula_str)
        if not (1 <= matricula <= 99):
            return JsonResponse({'ok': False, 'error': 'La matrícula debe estar entre 1 y 99.'}, status=400)
    except (ValueError, TypeError):
        return JsonResponse({'ok': False, 'error': 'La matrícula debe ser un número entero entre 1 y 99.'}, status=400)

    # Validar motivo (solo letras y espacios)
    motivo_limpio = motivo.replace(' ', '')
    if not motivo or not motivo_limpio.isalpha():
        return JsonResponse({'ok': False, 'error': 'El motivo debe contener solo letras.'}, status=400)

    referente = _get_referente(cuil)

    with transaction.atomic():
        # Crear o recuperar el grado para este establecimiento
        grado, grado_es_nuevo = ValGrado.objects.get_or_create(
            establecimiento=est,
            nombre_grado=nombre_grado,
            defaults={
                'cueanexo': cueanexo,
                'grado_creado': True,
            }
        )
        if grado_es_nuevo:
            grado.grado_creado = True
            grado.save()

        # Verificar que no exista ya esa combinación
        if ValSeccion.objects.filter(grado=grado, seccion=nombre_seccion, turno=turno).exists():
            return JsonResponse(
                {'ok': False, 'error': 'Ya existe una sección con esa letra y turno para este grado.'},
                status=400
            )

        seccion = ValSeccion.objects.create(
            grado=grado,
            seccion=nombre_seccion,
            turno=turno,
            matricula=matricula,
            estado_validacion='APROBADO',
            seccion_creada=True,
        )

        # Registrar en historial de matrículas
        ValHistorialMatriculas.objects.create(
            seccion=seccion,
            matricula_anterior=None,
            matricula_nueva=matricula,
            justificacion=f'Sección creada manualmente. Motivo: {motivo}',
            usuario_cambio=cuil,
            referente=referente,
        )

    return JsonResponse({
        'ok': True,
        'seccion_id':  str(seccion.public_id),
        'grado':       grado.nombre_grado,
        'seccion':     nombre_seccion,
        'turno':       turno,
        'matricula':   matricula,
        'estado':      'APROBADO',
        'grado_nuevo': grado_es_nuevo,
    })


# ---------------------------------------------------------------------------
# ACCIÓN: Validar sección → estado APROBADO
# ---------------------------------------------------------------------------
# @login_required
@require_POST
def validar_seccion(request, seccion_public_id):
    """
    Marca la sección como APROBADO directamente (sin cambiar la matrícula).
    """
    cuil = _get_cuil(request)
    seccion = ValSeccion.objects.for_referente(cuil, seccion_public_id)
    if not seccion:
        return JsonResponse({'ok': False, 'error': 'Sin acceso.'}, status=403)

    referente = _get_referente(cuil)

    with transaction.atomic():
        seccion.estado_validacion = 'APROBADO'
        seccion.motivo_deshabilitacion = None
        seccion.save()

        # Registro mínimo en historial
        ValHistorialMatriculas.objects.create(
            seccion=seccion,
            matricula_anterior=seccion.matricula,
            matricula_nueva=seccion.matricula,
            justificacion='Sección validada.',
            usuario_cambio=cuil,
            referente=referente,
        )

    return JsonResponse({
        'ok': True,
        'estado': 'APROBADO',
        'seccion_id': str(seccion_public_id),
    })


# ---------------------------------------------------------------------------
# ACCIÓN: Deshabilitar sección
# ---------------------------------------------------------------------------
# @login_required
@require_POST
def deshabilitar_seccion(request, seccion_public_id):
    """
    Marca la sección como DESHABILITADO con motivo obligatorio.
    Devuelve 'todas_deshabilitadas: true' si todas las secciones del
    establecimiento quedaron deshabilitadas.
    """
    cuil = _get_cuil(request)
    seccion = ValSeccion.objects.for_referente(cuil, seccion_public_id)
    if not seccion:
        return JsonResponse({'ok': False, 'error': 'Sin acceso.'}, status=403)

    motivo = request.POST.get('motivo', '').strip()
    if not motivo:
        return JsonResponse({'ok': False, 'error': 'El motivo es obligatorio.'}, status=400)

    referente = _get_referente(cuil)
    est = seccion.grado.establecimiento

    with transaction.atomic():
        seccion.estado_validacion = 'DESHABILITADO'
        seccion.motivo_deshabilitacion = motivo
        seccion.save()

        ValHistorialMatriculas.objects.create(
            seccion=seccion,
            matricula_anterior=seccion.matricula,
            matricula_nueva=seccion.matricula,
            justificacion=f'Sección deshabilitada. Motivo: {motivo}',
            usuario_cambio=cuil,
            referente=referente,
        )

        # Verificar si todas las secciones del establecimiento están deshabilitadas
        todas_qs    = ValSeccion.objects.filter(grado__establecimiento=est)
        total       = todas_qs.count()
        deshabilitadas = todas_qs.filter(estado_validacion='DESHABILITADO').count()
        todas_deshabilitadas = (total > 0) and (deshabilitadas == total)

    return JsonResponse({
        'ok': True,
        'estado': 'DESHABILITADO',
        'seccion_id': str(seccion_public_id),
        'todas_deshabilitadas': todas_deshabilitadas,
        'cueanexo': str(est.cueanexo),
    })


# ---------------------------------------------------------------------------
# ACCIÓN: Marcar establecimiento como "no participa" (todas deshabilitadas)
# ---------------------------------------------------------------------------
# @login_required
@require_POST
def marcar_no_participa_all_deshabilitadas(request, cueanexo):
    """
    Cuando el usuario confirma que el establecimiento no participa porque
    todas sus secciones fueron deshabilitadas.
    """
    cuil = _get_cuil(request)
    est = ValEstablecimiento.objects.for_referente(cuil, cueanexo)
    if not est:
        return JsonResponse({'ok': False, 'error': 'Sin acceso.'}, status=403)

    referente = _get_referente(cuil)

    with transaction.atomic():
        est.participa_aprender = None   # Vuelve a Sin Validar para que el referente valide de nuevo
        est.cabecera = None
        est.carga_completa = False
        est.motivo_no_participa = None
        est.save()

        ValHistorialCambiosEstablecimiento.objects.create(
            establecimiento=est,
            justificacion='Establecimiento revertido a Sin Validar: todas las secciones fueron deshabilitadas.',
            usuario=cuil,
            referente=referente,
        )

    redirect_url = reverse(
        'evaluaciones_educativas:validaciones_2026:lista_establecimientos',
        kwargs={'region': est.region}
    )
    return JsonResponse({'ok': True, 'redirect_url': redirect_url})


# ---------------------------------------------------------------------------
# ACCIÓN: Aprobar sección (compatibilidad con flujo anterior)
# ---------------------------------------------------------------------------
# @login_required
@require_POST
def aprobar_seccion(request, seccion_public_id):
    """
    Aprueba una sección. Si la matrícula cambió, exige justificación.
    """
    cuil = _get_cuil(request)
    seccion = ValSeccion.objects.for_referente(cuil, seccion_public_id)
    if not seccion:
        return JsonResponse({'ok': False, 'error': 'Sin acceso.'}, status=403)

    matricula_nueva_str = request.POST.get('matricula_nueva', '').strip()
    justificacion = request.POST.get('justificacion', '').strip()
    referente = _get_referente(cuil)

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
                usuario_cambio=cuil,
                referente=referente,
            )
        seccion.matricula = matricula_nueva
        seccion.estado_validacion = 'APROBADO'
        seccion.save()

    return JsonResponse({
        'ok': True,
        'estado': 'APROBADO',
        'matricula': matricula_nueva,
        'seccion_id': str(seccion_public_id),
    })


# ---------------------------------------------------------------------------
# ACCIÓN: Modificar matrícula (1-99, solo enteros)
# ---------------------------------------------------------------------------
# @login_required
@require_POST
def modificar_seccion(request, seccion_public_id):
    """
    Modifica la matrícula de una sección con justificación obligatoria.
    Matrícula debe estar entre 1 y 99. Guarda historial. Estado: MODIFICADO.
    """
    cuil = _get_cuil(request)
    seccion = ValSeccion.objects.for_referente(cuil, seccion_public_id)
    if not seccion:
        return JsonResponse({'ok': False, 'error': 'Sin acceso.'}, status=403)

    matricula_nueva_str = request.POST.get('matricula_nueva', '').strip()
    justificacion = request.POST.get('justificacion', '').strip()
    referente = _get_referente(cuil)

    if not justificacion:
        return JsonResponse({'ok': False, 'error': 'La justificación es obligatoria.'}, status=400)

    try:
        matricula_nueva = int(matricula_nueva_str)
        if not (1 <= matricula_nueva <= 99):
            return JsonResponse({'ok': False, 'error': 'La matrícula debe estar entre 1 y 99.'}, status=400)
    except (ValueError, TypeError):
        return JsonResponse({'ok': False, 'error': 'La matrícula debe ser un número entero entre 1 y 99.'}, status=400)

    with transaction.atomic():
        matricula_anterior = seccion.matricula
        ValHistorialMatriculas.objects.create(
            seccion=seccion,
            matricula_anterior=matricula_anterior,
            matricula_nueva=matricula_nueva,
            justificacion=justificacion,
            usuario_cambio=cuil,
            referente=referente,
        )
        seccion.matricula = matricula_nueva
        seccion.estado_validacion = 'MODIFICADO'
        seccion.save()

    return JsonResponse({
        'ok': True,
        'estado': 'MODIFICADO',
        'matricula': matricula_nueva,
        'seccion_id': str(seccion_public_id),
    })


# ---------------------------------------------------------------------------
# ACCIÓN: Editar sección (reset a PENDIENTE)
# ---------------------------------------------------------------------------
# @login_required
@require_POST
def editar_seccion(request, seccion_public_id):
    """
    Vuelve una sección al estado PENDIENTE para re-procesarla.
    """
    cuil = _get_cuil(request)
    seccion = ValSeccion.objects.for_referente(cuil, seccion_public_id)
    if not seccion:
        return JsonResponse({'ok': False, 'error': 'Sin acceso.'}, status=403)

    seccion.estado_validacion = 'PENDIENTE'
    seccion.motivo_deshabilitacion = None
    seccion.save()

    return JsonResponse({
        'ok': True,
        'estado': 'PENDIENTE',
        'seccion_id': str(seccion_public_id),
    })


# ---------------------------------------------------------------------------
# ACCIÓN: Marcar sección como sin matrícula (compatibilidad)
# ---------------------------------------------------------------------------
# @login_required
@require_POST
def marcar_sin_matricula(request, seccion_public_id):
    """
    Marca una sección como SIN_MATRICULA y guarda la justificación.
    """
    cuil = _get_cuil(request)
    seccion = ValSeccion.objects.for_referente(cuil, seccion_public_id)
    if not seccion:
        return JsonResponse({'ok': False, 'error': 'Sin acceso.'}, status=403)

    justificacion = request.POST.get('justificacion', '').strip()
    referente = _get_referente(cuil)

    if not justificacion:
        return JsonResponse({'ok': False, 'error': 'La justificación es obligatoria.'}, status=400)

    with transaction.atomic():
        ValHistorialMatriculas.objects.create(
            seccion=seccion,
            matricula_anterior=seccion.matricula,
            matricula_nueva=None,
            justificacion=justificacion,
            usuario_cambio=cuil,
            referente=referente,
        )
        seccion.estado_validacion = 'SIN_MATRICULA'
        seccion.matricula = None
        seccion.save()

    return JsonResponse({
        'ok': True,
        'estado': 'SIN_MATRICULA',
        'seccion_id': str(seccion_public_id),
    })


# ---------------------------------------------------------------------------
# ACCIÓN: Validación completa del establecimiento (toggle)
# ---------------------------------------------------------------------------
# @login_required
@require_POST
def validar_establecimiento_completo(request, cueanexo):
    """
    Marca carga_completa=True cuando todas las secciones están procesadas.
    Si ya estaba True (re-presionado), lo vuelve a False para permitir edición.
    """
    cuil = _get_cuil(request)
    est = ValEstablecimiento.objects.for_referente(cuil, cueanexo)
    if not est:
        return JsonResponse({'ok': False, 'error': 'Sin acceso.'}, status=403)

    # Verificar que no haya secciones pendientes
    pendientes = ValSeccion.objects.filter(
        grado__establecimiento=est,
        estado_validacion='PENDIENTE'
    ).count()
    if pendientes > 0:
        return JsonResponse(
            {'ok': False, 'error': f'Hay {pendientes} sección(es) aún pendiente(s) de validar.'},
            status=400
        )

    referente = _get_referente(cuil)

    with transaction.atomic():
        # Toggle: si ya está True, lo abre para re-edición
        est.carga_completa = not est.carga_completa
        est.save()

        ValHistorialCambiosEstablecimiento.objects.create(
            establecimiento=est,
            justificacion='Carga marcada como completa.' if est.carga_completa else 'Carga reabierta para modificación.',
            usuario=cuil,
            referente=referente,
        )

    return JsonResponse({'ok': True, 'carga_completa': est.carga_completa})
