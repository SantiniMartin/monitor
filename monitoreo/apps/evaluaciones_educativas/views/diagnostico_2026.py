from apps import evaluaciones
from apps.evaluaciones.models import Alumno
from apps.evaluaciones_educativas.models.diagnostico_2026 import Establecimientos2026, EvaluacionDiagnostica2026, Año2026
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.urls import reverse
from django.http import FileResponse
from django.contrib.auth.decorators import login_required
from django.db.models import Q
import io
import re
from reportlab.lib.pagesizes import landscape, A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from ..forms import MatematicaForm, LenguaForm, AlumnoForm
from ..models import Alumno2026, Matematica2026, Lengua2026, Seccion2026, TablaTemporalAlumno
from ..utils import utilidades
from django.core.paginator import Paginator
from apps.consultasge.models import CapaUnicaOfertas
from django.core.exceptions import PermissionDenied

def _orden_pregunta_field(field):
	numeros = re.findall(r'\d+', field.name)
	return [int(n) for n in numeros] if numeros else [0]


def _respuestas_formulario(form):
	"""Valores actuales de cada pregunta (para marcar radios en la plantilla)."""
	return {
		name: form[name].value()
		for name in form.fields
		if name.startswith('pregunta_')
	}


def _limpiar_preguntas_si_ausente(examen):
	"""Si el alumno estuvo ausente, no se guardan respuestas de ítems."""
	if examen.asistencia != 'AUSENTE':
		return
	for field in examen._meta.get_fields():
		if hasattr(field, 'name') and field.name.startswith('pregunta_'):
			setattr(examen, field.name, None)


def _guardar_examen(form, alumno):

	#========================== Lógica para guardar resultados de preguntas cerradas: =============================

	# ── Claves de respuesta por modelo ───────────────────────────────────────────

	CLAVE_MATEMATICA = {
		'A': {'pregunta_3': ('A', 7), 'pregunta_8': ('C', 8), 'pregunta_10': ('A', 11)},
		'B': {'pregunta_3': ('A', 7), 'pregunta_8': ('B', 8), 'pregunta_10': ('A', 11)},
	}

	CLAVE_LENGUA = {
		'A': {
			'pregunta_1':  ('B', 1.50), 'pregunta_2':  ('B', 1.50), 'pregunta_3':  ('B', 2.50),
			'pregunta_4':  ('A', 2.50), 'pregunta_5':  ('B', 4.50), 'pregunta_6':  ('C', 4.50),
			'pregunta_7':  ('B', 6.00), 'pregunta_8':  ('B', 1.50), 'pregunta_9':  ('D', 4.50),
			'pregunta_10': ('A', 5.50), 'pregunta_12': ('A', 1.50), 'pregunta_13': ('B', 2.50),
			'pregunta_14': ('B', 5.50), 'pregunta_15': ('A', 5.50), 'pregunta_16': ('D', 4.50),
			'pregunta_17': ('A', 4.50), 'pregunta_18': ('C', 2.50), 'pregunta_19': ('A', 4.50),
			'pregunta_20': ('A', 4.50), 'pregunta_21': ('A', 5.50),
		},
		'B': {
			'pregunta_1':  ('C', 1.50), 'pregunta_2':  ('D', 1.50), 'pregunta_3':  ('D', 2.50),
			'pregunta_4':  ('D', 2.50), 'pregunta_5':  ('C', 4.50), 'pregunta_6':  ('D', 4.50),
			'pregunta_7':  ('C', 6.00), 'pregunta_8':  ('A', 1.50), 'pregunta_9':  ('A', 4.50),
			'pregunta_10': ('D', 5.50), 'pregunta_12': ('D', 1.50), 'pregunta_13': ('C', 2.50),
			'pregunta_14': ('C', 5.50), 'pregunta_15': ('B', 5.50), 'pregunta_16': ('C', 4.50),
			'pregunta_17': ('C', 4.50), 'pregunta_18': ('B', 2.50), 'pregunta_19': ('C', 4.50),
			'pregunta_20': ('D', 4.50), 'pregunta_21': ('C', 5.50),
		},
	}


# ── Helpers para obtener el puntaje de cada pregunta ─────────────────────────

	def _puntaje_pregunta_matematica(examen, nombre_campo):
		"""
		Para preguntas cerradas (3, 8, 10): devuelve el puntaje si la respuesta es correcta.
		Para el resto: convierte el valor del CharField a float.
		"""
		valor = getattr(examen, nombre_campo, None)
		if valor is None:
			return 0.0

		clave = CLAVE_MATEMATICA.get(examen.modelo, {})
		if nombre_campo in clave:
			respuesta_correcta, puntos = clave[nombre_campo]
			return float(puntos) if valor == respuesta_correcta else 0.0

		# Preguntas numéricas: el valor ya es el puntaje (ej. "6,5" → 6.5)
		try:
			return float(str(valor).replace(',', '.'))
		except (ValueError, TypeError):
			return 0.0


	def _puntaje_pregunta_lengua(examen, nombre_campo):
		"""
		Para preguntas de opción múltiple (1-10, 12-21): puntaje si es correcta.
		Para preguntas compuestas (11_x, 22_x): el valor ya es el puntaje.
		"""
		valor = getattr(examen, nombre_campo, None)
		if valor is None:
			return 0.0

		clave = CLAVE_LENGUA.get(examen.modelo, {})
		if nombre_campo in clave:
			respuesta_correcta, puntos = clave[nombre_campo]
			return float(puntos) if valor == respuesta_correcta else 0.0

		# Preguntas compuestas (11_x, 22_x): el valor ya es el puntaje
		try:
			return float(str(valor).replace(',', '.'))
		except (ValueError, TypeError):
			return 0.0


	# ── Cálculo de correcciones ───────────────────────────────────────────────────

	def _calcular_correcciones_matematica(examen):
		"""Calcula y asigna los campos de corrección del examen de Matemática."""
		if examen.asistencia == 'AUSENTE':
			examen.correcion_comunicacion  = None
			examen.correcion_reconocimiento = None
			examen.correcion_resolucion    = None
			examen.total_puntaje           = None
			return

		p = lambda campo: _puntaje_pregunta_matematica(examen, campo)

		examen.correcion_comunicacion   = p('pregunta_2') + p('pregunta_5') + p('pregunta_12') + p('pregunta_10')
		examen.correcion_reconocimiento = p('pregunta_1') + p('pregunta_3') + p('pregunta_8')  + p('pregunta_11')
		examen.correcion_resolucion     = p('pregunta_4') + p('pregunta_6') + p('pregunta_7')  + p('pregunta_9')
		examen.total_puntaje = (
			examen.correcion_comunicacion +
			examen.correcion_reconocimiento +
			examen.correcion_resolucion
		)


	def _calcular_correcciones_lengua(examen):
		"""Calcula y asigna los campos de corrección del examen de Lengua."""
		if examen.asistencia == 'AUSENTE':
			examen.correcion_reflexion      = None
			examen.correcion_interpretacion = None
			examen.correcion_extraccion     = None
			examen.correcion_escritura      = None
			examen.total_puntaje            = None
			return

		p = lambda campo: _puntaje_pregunta_lengua(examen, campo)

		examen.correcion_reflexion = (
			p('pregunta_8')  + p('pregunta_10') + p('pregunta_16') + p('pregunta_18') +
			p('pregunta_19') + p('pregunta_20') + p('pregunta_21')
		)
		examen.correcion_interpretacion = (
			p('pregunta_3')  + p('pregunta_4')  + p('pregunta_6') +
			p('pregunta_7')  + p('pregunta_14') + p('pregunta_17')
		)
		examen.correcion_extraccion = (
			p('pregunta_1')  + p('pregunta_2')  + p('pregunta_5') + p('pregunta_9') +
			p('pregunta_12') + p('pregunta_13') + p('pregunta_15')
		)
		# Corrección escritura: preguntas compuestas 11 y 22
		examen.correcion_escritura = (
			p('pregunta_11_1') + p('pregunta_11_2') + p('pregunta_11_3') + p('pregunta_11_4') +
			p('pregunta_22_1') + p('pregunta_22_2') + p('pregunta_22_3')
		)
		examen.total_puntaje = (
			examen.correcion_reflexion +
			examen.correcion_interpretacion +
			examen.correcion_extraccion +
			examen.correcion_escritura
		)

	#========================== Fin de lógica para guardar resultados de preguntas cerradas: =============================

	examen = form.save(commit=False)
	examen.alumno = alumno
	if not examen.encargado_carga:
		examen.encargado_carga = 'DIRECTOR'
	_limpiar_preguntas_si_ausente(examen)

	if isinstance(examen, Matematica2026):
		_calcular_correcciones_matematica(examen)
	elif isinstance(examen, Lengua2026):
		_calcular_correcciones_lengua(examen)

	examen.save()
	return examen


def _obtener_estructura_preguntas_lengua():
	"""Retorna estructura de preguntas de Lengua con puntajes"""
	estructura = {
		'preguntas_simples': [
			{'num': i, 'puntajes': ['A', 'B', 'C', 'D', 'OMITIÓ']} 
			for i in range(1, 11)
		] + [
			{'num': i, 'puntajes': ['A', 'B', 'C', 'D', 'OMITIÓ']} 
			for i in range(12, 22)
		],
		'preguntas_compuestas': {
			11: {
				'titulo': 'Pregunta 11',
				'partes': {
					'11_1': {'label': '11.1. Elección de la opción', 'puntajes': [2, 0]},
					'11_2': {'label': '11.2. Justificación', 'puntajes': [5.65, 2.80, 0]},
					'11_3': {'label': '11.3. Normativa - Puntuación', 'puntajes': [2.30, 1.15, 0]},
					'11_4': {'label': '11.4. Normativa - Ortografía', 'puntajes': [2.30, 1.15, 0]},
				},
				'total': 13.25,
			},
			22: {
				'titulo': 'Pregunta 22',
				'partes': {
					'22_1': {'label': '22.1. Contenido, autores y obras', 'puntajes': [7.65, 3.80, 0]},
					'22_2': {'label': '22.2. Normativa - Puntuación', 'puntajes': [2.30, 1.15, 0]},
					'22_3': {'label': '22.3. Normativa - Ortografía', 'puntajes': [2.30, 1.15, 0]},
				},
				'total': 12.50,
			}
		},
		'total_puntos': 100
	}
	return estructura


def _obtener_estructura_preguntas_matematica():
	"""Retorna estructura de preguntas de Matemática con puntajes"""
	estructura = {
		'preguntas': [
			{'num': 1, 'puntajes': [6.5, 3.25, 0]},
			{'num': 2, 'puntajes': [6, 4, 2, 0]},
			{'num': 3, 'puntajes': ['A', 'B', 'C', 'OMITIÓ']},  # Respuesta libre, mostrar opciones
			{'num': 4, 'puntajes': [6, 3, 0]},
			{'num': 5, 'puntajes': [7, 3.5, 0]},
			{'num': 6, 'puntajes': [8, 4, 0]},
			{'num': 7, 'puntajes': [10, 5, 0]},
			{'num': 8, 'puntajes': ['A', 'B', 'C', 'OMITIÓ']},
			{'num': 9, 'puntajes': [11, 5.50, 0]},
			{'num': 10, 'puntajes': ['A', 'B', 'C', 'OMITIÓ']},
			{'num': 11, 'puntajes': [10.5, 7, 3.5, 0]},
			{'num': 12, 'puntajes': [9, 4.5, 0]},
		],
		'total_puntos': 100
	}
	return estructura


@login_required
def inicio(request):
	usuario = request.user
	name = usuario.username
	#--- logica para no permitir ingreso a no autorizados--------------
	cuil_con_caracter = f"{name[:2]}-{name[2:10]}-{name[10:]}"
	if not CapaUnicaOfertas.objects.filter(resploc_cuitcuil=cuil_con_caracter, oferta__icontains='Secundaria Completa req. 7 años').exists():
		raise PermissionDenied("No tienes permiso para acceder a esta sección.")
	user_cueanexos = utilidades.obtener_cueanexos(usuario.username)
	selected_cue = request.GET.get('cueanexo')
	if not selected_cue and user_cueanexos:
		selected_cue = str(user_cueanexos[0])

	if selected_cue not in [str(c) for c in user_cueanexos]:
		selected_cue = str(user_cueanexos[0]) if user_cueanexos else None

	print("CUEANEXOS del usuario:", user_cueanexos)
	print("CUE seleccionado:", selected_cue)

	search_query = request.GET.get('search', '').strip()
	pagina       = request.GET.get('pagina', 1)

	if selected_cue:
		lista_dnis = list(
			TablaTemporalAlumno.objects
			.filter(cueanexo=selected_cue)
			.values_list('numero_de_documento', flat=True)
		)
		lista = list(
			Alumno2026.objects
			.filter(~Q(dni__in=lista_dnis),seccion__año__Establecimiento__cueanexo=int(selected_cue))
			.select_related('seccion__año', 'seccion__año__Establecimiento')
			.values_list('dni', flat=True)
		)
		lista_dnis.extend(lista)

		alumnos_qs = Alumno2026.objects.filter(dni__in=lista_dnis)

		if search_query:
			alumnos_qs = alumnos_qs.filter(
				Q(nombre__icontains=search_query) |
				Q(apellido__icontains=search_query) |
				Q(dni__icontains=search_query)
			)

		alumnos_qs = alumnos_qs.order_by('apellido', 'nombre')
	else:
		alumnos_qs = Alumno2026.objects.none()

	print("Total alumnos encontrados:", alumnos_qs.count())

	# ── Paginación ANTES del loop para procesar solo 10 registros ─────────────
	paginator = Paginator(alumnos_qs, 10)
	
	try:
		page_obj = paginator.page(pagina)
	except Exception:
		page_obj = paginator.page(1)

	# ── Optimización: traer los exámenes de la página actual en 2 queries ─────
	#    en lugar de 2 queries por alumno (N*2 queries → 2 queries fijas)
	alumnos_pagina = list(page_obj.object_list)
	ids_pagina     = [a.pk for a in alumnos_pagina]

	ids_con_matematica = set(
		Matematica2026.objects.filter(alumno_id__in=ids_pagina)
		.values_list('alumno_id', flat=True)
	)
	ids_con_lengua = set(
		Lengua2026.objects.filter(alumno_id__in=ids_pagina)
		.values_list('alumno_id', flat=True)
	)

	lista_alumnos_procesada = []
	for alumno in alumnos_pagina:
		tiene_datos_completos = all([
			alumno.dni and len(alumno.dni) >= 7,
			alumno.nombre,
			alumno.apellido,
			alumno.discapacidad,
			alumno.comunidad_indigena,
		])
		tiene_matematica = alumno.pk in ids_con_matematica
		tiene_lengua     = alumno.pk in ids_con_lengua

		lista_alumnos_procesada.append({
			'objeto':          alumno,
			'datos_validados': tiene_datos_completos,
			'tiene_matematica': tiene_matematica,
			'tiene_lengua':     tiene_lengua,
			'examen_completo':  tiene_matematica and tiene_lengua,
		})

	# ── Secciones disponibles ─────────────────────────────────────────────────
	secciones_disponibles = {}
	if selected_cue:
		qs_secciones = Seccion2026.objects.filter(
			año__Establecimiento__cueanexo=selected_cue
		)
		secciones_disponibles = {
			'secciones': list(qs_secciones.values_list('seccion', flat=True).distinct()),
			'turnos':    list(qs_secciones.values_list('turno',   flat=True).distinct()),
		}

	context = {
		'alumnos':              lista_alumnos_procesada,
		'page_obj':             page_obj,
		'cue_escuela':          selected_cue,
		'user_cueanexos':       user_cueanexos,
		'selected_cue':         selected_cue,
		'search_query':         search_query,
		'opciones_seccion':     Seccion2026.OPCIONES_SECCION,
		'opciones_turno':       Seccion2026.OPCIONES_TURNO,
		'secciones_disponibles': secciones_disponibles,
		'opciones_comunidad_indigena': Alumno2026.OPCIONES_COMUNIDAD_INDIGENA,
		'opciones_discapacidad':       Alumno2026.OPCIONES_DISCAPACIDAD,   
	}

	return render(request, "diagnostico_2026/inicio.html", context)


@login_required
def realizar_carga(request):
	usuario = request.user
	user_cueanexos = utilidades.obtener_cueanexos(usuario.username)
	selected_cue = request.GET.get('cueanexo')
	if selected_cue not in [str(c) for c in user_cueanexos]:
		selected_cue = str(user_cueanexos[0]) if user_cueanexos else None

	return render(request, 'diagnostico_2026/realizar_carga.html', {
		'user_cueanexos': user_cueanexos,
		'selected_cue': selected_cue,
	})


@login_required
def examenes_lista(request, materia):
	usuario = request.user
	user_cueanexos = utilidades.obtener_cueanexos(usuario.username)
	selected_cue = request.GET.get('cueanexo')
	if selected_cue not in [str(c) for c in user_cueanexos]:
		selected_cue = str(user_cueanexos[0]) if user_cueanexos else None

	if materia == 'matematica':
		examen_model = Matematica2026
		materia_nombre = 'Matemática'
	elif materia == 'lengua':
		examen_model = Lengua2026
		materia_nombre = 'Lengua'
	else:
		return redirect('evaluaciones_educativas:diagnostico_2026:realizar_carga')
	estado_carga,numero = boton_completar_carga(selected_cue, materia_nombre)
	alumnos_qs = Alumno2026.objects.filter(
		seccion__año__Establecimiento__cueanexo=selected_cue
	).select_related('seccion__año').order_by('apellido', 'nombre') if selected_cue else Alumno2026.objects.none()

	pregunta_campos = [f for f in examen_model._meta.get_fields()
					   if hasattr(f, 'choices') and f.choices and f.name.startswith('pregunta_')]
	pregunta_campos = sorted(pregunta_campos, key=_orden_pregunta_field)
	pregunta_encabezados = [f.name.replace('_', ' ').title() for f in pregunta_campos]

	# ── Paginación ────────────────────────────────────────────────────────────
	try:
		pagina = int(request.GET.get('pagina', 1))
		if pagina < 1:
			pagina = 1
	except (ValueError, TypeError):
		pagina = 1

	paginator = Paginator(alumnos_qs, 10)
	page_obj  = paginator.get_page(pagina)

	# ── Traer exámenes solo de los alumnos de la página actual (1 query) ──────
	ids_pagina = [a.pk for a in page_obj.object_list]
	examenes_map = {
		e.alumno_id: e
		for e in examen_model.objects.filter(alumno_id__in=ids_pagina)
	}

	filas = []
	for alumno in page_obj.object_list:
		examen = examenes_map.get(alumno.pk)
		filas.append({
			'alumno':     alumno,
			'examen':     examen,
			'modelo':     examen.modelo    if examen else '',
			'ausentismo': examen.asistencia if examen else '',
			'preguntas':  [getattr(examen, campo.name) if examen else '' for campo in pregunta_campos],
		})

	return render(request, 'diagnostico_2026/examenes_lista.html', {
		'estado_carga':estado_carga,
		'numero':	numero,
		'filas':               filas,
		'page_obj':            page_obj,
		'materia_nombre':      materia_nombre,
		'materia':             materia,
		'selected_cue':        selected_cue,
		'pregunta_encabezados': pregunta_encabezados,
	})


@login_required
def descargar_examenes(request, materia):
	usuario = request.user
	user_cueanexos = utilidades.obtener_cueanexos(usuario.username)
	selected_cue = request.GET.get('cueanexo')
	if selected_cue not in [str(c) for c in user_cueanexos]:
		selected_cue = str(user_cueanexos[0]) if user_cueanexos else None

	if materia == 'matematica':
		examen_model = Matematica2026
		materia_nombre = 'Matemática'
	elif materia == 'lengua':
		examen_model = Lengua2026
		materia_nombre = 'Lengua'
	else:
		return redirect('evaluaciones_educativas:diagnostico_2026:realizar_carga')

	alumnos_qs = Alumno2026.objects.filter(
		seccion__año__Establecimiento__cueanexo=selected_cue
	).select_related('seccion__año').order_by('apellido', 'nombre') if selected_cue else Alumno2026.objects.none()

	pregunta_campos = [f for f in examen_model._meta.get_fields()
					   if hasattr(f, 'choices') and f.choices and f.name.startswith('pregunta_')]
	pregunta_campos = sorted(pregunta_campos, key=_orden_pregunta_field)
	
	pregunta_encabezados = []
	for f in pregunta_campos:
			nombre = f.name.replace('pregunta_', '')
			partes = nombre.split('_')
			if len(partes) == 1:
					encabezado = f'P{partes[0]}'
			else:
					encabezado = f'P{partes[0]}.{partes[1]}'
			pregunta_encabezados.append(encabezado)

	data = [
		['Apellido', 'Nombre', 'DNI', 'Sección', 'Turno', 'Modelo', 'Asistencia'] + pregunta_encabezados
	]

	for alumno in alumnos_qs:
		examen = examen_model.objects.filter(alumno=alumno).first()
		row = [
			alumno.apellido,
			alumno.nombre,
			alumno.dni,
			alumno.seccion.seccion if alumno.seccion else '',
			alumno.seccion.turno if alumno.seccion else '',
			examen.modelo if examen else '',
			examen.asistencia if examen else '',
		]
		row.extend([getattr(examen, campo.name) if examen else '' for campo in pregunta_campos])
		data.append(row)

	buffer = io.BytesIO()
	doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), leftMargin=20, rightMargin=20, topMargin=20, bottomMargin=20)
	styles = getSampleStyleSheet()
	story = []

	story.append(Paragraph(f"Lista de exámenes - {materia_nombre}", styles['Title']))
	story.append(Paragraph(f"CUE/ANEXO: {selected_cue or 'N/A'}", styles['Normal']))
	story.append(Spacer(1, 12))

	ancho_disponible = landscape(A4)[0] - 35
	ancho_fijos = 55 + 55 + 45 + 35 + 35 + 35 + 50
	ancho_preguntas = (ancho_disponible - ancho_fijos) / len(pregunta_campos)
	col_widths = [55, 55, 45, 35, 35, 35, 50] + [ancho_preguntas] * len(pregunta_campos)
	table = Table(data, colWidths=col_widths, repeatRows=1)
	table.setStyle(TableStyle([
    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#E9ECEF')),
    ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
    ('ALIGN', (0, 1), (-1, -1), 'CENTER'),
    ('FONTSIZE', (0, 0), (-1, 0), 7),
    ('FONTSIZE', (0, 1), (-1, -1), 6),
    ('LEFTPADDING', (0, 0), (-1, -1), 2),
    ('RIGHTPADDING', (0, 0), (-1, -1), 2),
    ('TOPPADDING', (0, 0), (-1, -1), 2),
    ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ('WORDWRAP', (0, 0), (-1, -1), True),
]))

	story.append(table)
	doc.build(story)
	buffer.seek(0)

	filename = f"examenes_{materia}_{selected_cue or 'todos'}.pdf"
	return FileResponse(buffer, as_attachment=True, filename=filename)


@login_required
def eliminar_examen(request, alumno_uuid, materia):
	alumno = get_object_or_404(Alumno2026, public_id=alumno_uuid)
	selected_cue = request.GET.get('cueanexo')

	if materia == 'matematica':
		examen = Matematica2026.objects.filter(alumno=alumno).first()
	elif materia == 'lengua':
		examen = Lengua2026.objects.filter(alumno=alumno).first()
	else:
		return redirect('evaluaciones_educativas:diagnostico_2026:realizar_carga')

	if examen:
		examen.delete()

	redirect_url = reverse('evaluaciones_educativas:diagnostico_2026:examenes_lista', kwargs={'materia': materia})
	if selected_cue:
		return redirect(f"{redirect_url}?cueanexo={selected_cue}")
	return redirect(redirect_url)


@login_required
def actualizar_seccion(request, alumno_uuid):
	"""Actualiza la sección, turno, comunidad_indigena y discapacidad de un alumno."""
	if request.method == 'POST':
		alumno = get_object_or_404(Alumno2026, public_id=alumno_uuid)

		nueva_seccion = request.POST.get('seccion')
		nuevo_turno   = request.POST.get('turno')
		comunidad     = request.POST.get('comunidad_indigena')
		discapacidad  = request.POST.get('discapacidad')

		# Actualizar sección y turno
		if nueva_seccion and nuevo_turno:
			if alumno.seccion:
					cueanexo = alumno.seccion.año.cueanexo
			else:
					cueanexo = request.POST.get('cueanexo')
					
			año_actual = Año2026.objects.get(cueanexo=cueanexo)
			seccion_obj = Seccion2026.objects.get(
					seccion=nueva_seccion,
					año=año_actual,
					turno=nuevo_turno
			)
			alumno.seccion = seccion_obj

		# Actualizar comunidad indígena (solo valores válidos)
		valores_comunidad = [v for v, _ in Alumno2026.OPCIONES_COMUNIDAD_INDIGENA]
		if comunidad in valores_comunidad:
			alumno.comunidad_indigena = comunidad

		# Actualizar discapacidad (solo valores válidos)
		valores_discapacidad = [v for v, _ in Alumno2026.OPCIONES_DISCAPACIDAD]
		if discapacidad in valores_discapacidad:
			alumno.discapacidad = discapacidad

		alumno.save()

	selected_cue = request.POST.get('cueanexo', '')
	url = reverse('evaluaciones_educativas:diagnostico_2026:inicio')
	return redirect(f"{url}?cueanexo={selected_cue}")


@login_required
def cargar_examen(request, alumno_uuid, materia):
	alumno = get_object_or_404(Alumno2026, public_id=alumno_uuid)
	return_cueanexo = request.GET.get('cueanexo') or request.POST.get('cueanexo')
	existing_examen = None

	if materia == 'matematica':
		existing_examen = Matematica2026.objects.filter(alumno=alumno).first()
		form_class = MatematicaForm
		template_materia = "Matemática"
		estructura_preguntas = _obtener_estructura_preguntas_matematica()
	elif materia == 'lengua':
		existing_examen = Lengua2026.objects.filter(alumno=alumno).first()
		form_class = LenguaForm
		template_materia = "Lengua"
		estructura_preguntas = _obtener_estructura_preguntas_lengua()
	else:
		return redirect('evaluaciones_educativas:diagnostico_2026:inicio')

	form = form_class(request.POST or None, instance=existing_examen)
	modo_edicion = bool(existing_examen)

	if request.method == 'POST':
		if form.is_valid():
			_guardar_examen(form, alumno)
			messages.success(request, f'Examen de {template_materia} guardado correctamente.')
			redirect_url = reverse('evaluaciones_educativas:diagnostico_2026:examenes_lista', kwargs={'materia': materia})
			if return_cueanexo:
				return redirect(f"{redirect_url}?cueanexo={return_cueanexo}")
			return redirect(redirect_url)
		messages.error(request, 'No se pudo guardar el examen. Revise los campos indicados.')

	if request.method == 'GET' and existing_examen:
		redirect_url = reverse('evaluaciones_educativas:diagnostico_2026:editar_examen', kwargs={'alumno_uuid': alumno_uuid, 'materia': materia})
		if return_cueanexo:
			return redirect(f"{redirect_url}?cueanexo={return_cueanexo}")
		return redirect(redirect_url)

	return render(request, 'diagnostico_2026/cargar_examen_v2.html', {
		'form': form,
		'materia': template_materia,
		'materia_slug': materia,
		'alumno': alumno,
		'return_cueanexo': return_cueanexo,
		'modo_edicion': modo_edicion,
		'estructura_preguntas': estructura_preguntas,
		'respuestas': _respuestas_formulario(form),
	})


@login_required
def editar_alumno(request, alumno_uuid):
	alumno = get_object_or_404(Alumno2026, public_id=alumno_uuid)
	return_cueanexo = request.GET.get('cueanexo') or request.POST.get('cueanexo')
	form = AlumnoForm(request.POST or None, instance=alumno)

	if request.method == 'POST' and form.is_valid():
		form.save()
		redirect_url = reverse('evaluaciones_educativas:diagnostico_2026:inicio')
		if return_cueanexo:
			return redirect(f"{redirect_url}?cueanexo={return_cueanexo}")
		return redirect(redirect_url)

	return render(request, 'diagnostico_2026/editar_alumno.html', {
		'form': form,
		'alumno': alumno,
		'return_cueanexo': return_cueanexo,
	})


@login_required
def agregar_alumno(request):
   # from ..models import Año2026
	usuario = request.user
	user_cueanexos = utilidades.obtener_cueanexos(usuario.username)
	
	# Obtener cueanexo del query parameter o usar el primero disponible
	selected_cue = request.GET.get('cueanexo') or request.POST.get('cueanexo')
	if selected_cue not in [str(c) for c in user_cueanexos]:
		selected_cue = str(user_cueanexos[0]) if user_cueanexos else None
	
	# Secciones disponibles para ese CUE
	secciones_qs = Seccion2026.objects.filter(
		año__Establecimiento__cueanexo=selected_cue
	).select_related('año').order_by('año__nombre_año', 'seccion')

	form = AlumnoForm(request.POST or None)

	if request.method == 'POST' and form.is_valid():
		seccion_id = request.POST.get('seccion_id')
		seccion_obj = Seccion2026.objects.filter(id=seccion_id).first()

		if seccion_obj:
			try:
				alumno = form.save(commit=False)
				alumno.seccion = seccion_obj
				alumno.save()
				redirect_url = reverse('evaluaciones_educativas:diagnostico_2026:inicio')
				if selected_cue:
					return redirect(f"{redirect_url}?cueanexo={selected_cue}")
				return redirect(redirect_url)
			except Exception as e:
				form.add_error(None, f'Error al guardar alumno: {str(e)}')
		else:
			form.add_error(None, 'Debes seleccionar una sección válida.')

	return render(request, 'diagnostico_2026/agregar_alumno.html', {
		'form': form,
		'secciones': secciones_qs,
		'selected_cue': selected_cue,
		'user_cueanexos': user_cueanexos,
	})


@login_required
def editar_examen(request, alumno_uuid, materia):
	alumno = get_object_or_404(Alumno2026, public_id=alumno_uuid)
	return_cueanexo = request.GET.get('cueanexo') or request.POST.get('cueanexo')

	if materia == 'matematica':
		examen = get_object_or_404(Matematica2026, alumno=alumno)
		form = MatematicaForm(request.POST or None, instance=examen)
		template_materia = "Matemática"
		estructura_preguntas = _obtener_estructura_preguntas_matematica()
	elif materia == 'lengua':
		examen = get_object_or_404(Lengua2026, alumno=alumno)
		form = LenguaForm(request.POST or None, instance=examen)
		template_materia = "Lengua"
		estructura_preguntas = _obtener_estructura_preguntas_lengua()
	else:
		return redirect('evaluaciones_educativas:diagnostico_2026:inicio')

	if request.method == 'POST':
		if form.is_valid():
			_guardar_examen(form, alumno)
			messages.success(request, f'Examen de {template_materia} actualizado correctamente.')
			redirect_url = reverse('evaluaciones_educativas:diagnostico_2026:examenes_lista', kwargs={'materia': materia})
			if return_cueanexo:
				return redirect(f"{redirect_url}?cueanexo={return_cueanexo}")
			return redirect(redirect_url)
		messages.error(request, 'No se pudo actualizar el examen. Revise los campos indicados.')

	return render(request, 'diagnostico_2026/cargar_examen_v2.html', {
		'form': form,
		'materia': template_materia,
		'materia_slug': materia,
		'alumno': alumno,
		'modo_edicion': True,
		'return_cueanexo': return_cueanexo,
		'estructura_preguntas': estructura_preguntas,
		'respuestas': _respuestas_formulario(form),
	})

def boton_completar_carga(cueanexo, materia_nombre):
	estado_carga=None
	lista_inicial_conteo=None
	lista_final_conteo=None
	numero=None
	lista_dnis = list(
			TablaTemporalAlumno.objects
			.filter(cueanexo=cueanexo)
			.values_list('numero_de_documento', flat=True)
		)
	lista = list(
			Alumno2026.objects
			.filter(~Q(dni__in=lista_dnis),seccion__año__Establecimiento__cueanexo=int(cueanexo))
			.select_related('seccion__año', 'seccion__año__Establecimiento')
			.values_list('dni', flat=True)
		)
	lista_dnis.extend(lista)
	alumnos_qs = Alumno2026.objects.filter(dni__in=lista_dnis)
	lista_inicial_conteo=alumnos_qs.count()
	if materia_nombre == 'Matemática':
		evaluaciones=Matematica2026.objects.filter(alumno__in=alumnos_qs).count()
		#evaluaciones_materia=evaluaciones
		lista_final_conteo=evaluaciones
	else:
		evaluaciones=Lengua2026.objects.filter(alumno__in=alumnos_qs).count()
		lista_final_conteo=evaluaciones
	#for i in alumnos_qs:
	if lista_inicial_conteo == lista_final_conteo:
		estado_carga=True
	else:
		estado_carga=False
		numero = lista_inicial_conteo - lista_final_conteo
	print(f'es numero{numero}')
	return estado_carga,numero


def monitoreo_evaluaciones_educativas(request):
	selected_dni = request.GET.get('dni')
	# establecimientos_cueanexo = Establecimientos2026.objects.values_list('cueanexo', flat=True)
	establecimientos_cueanexo = Establecimientos2026.objects.all()
	#alumnos_total= Alumno2026.objects.values_list('dni','nombre','apellido','seccion__seccion','seccion__año__cueanexo')
	if selected_dni:
		alumnos_query=EvaluacionDiagnostica2026.objects.filter(alumno__dni__icontains=selected_dni)
	else:
		alumnos_query=EvaluacionDiagnostica2026.objects.all()

	print(alumnos_query)
	alumnos_total = alumnos_query.values_list(
        'alumno__dni',
        'alumno__nombre',
        'alumno__apellido',
        'alumno__seccion__seccion',
        'alumno__seccion__año__cueanexo',
		'matematica2026',
		'lengua2026'
    )
	establecimientos_region= Establecimientos2026.objects.values_list('region', flat=True)
	monitoreo_total = []
	for i in establecimientos_cueanexo:
		lista_dnis = list(
			TablaTemporalAlumno.objects
			.filter(cueanexo=i.cueanexo)
			.values_list('numero_de_documento', flat=True)
		)
		lista = list(
			Alumno2026.objects
			.filter(~Q(dni__in=lista_dnis),seccion__año__Establecimiento__cueanexo=int(i.cueanexo))
			.select_related('seccion__año', 'seccion__año__Establecimiento')
			.values_list('dni', flat=True)
		)
		lista_dnis.extend(lista) 
		alumnos=Alumno2026.objects.filter(seccion__año__cueanexo=i)
		alumnos_conteo=len(lista_dnis)
		alumno_examen_matematica=Matematica2026.objects.filter(alumno__in=alumnos).count()
		alumno_examen_lengua= Lengua2026.objects.filter(alumno__in=alumnos).count()
		monitoreo_total.append({
					'cueanexo': i.cueanexo,
					'escuela': i.escuela,
					'region': i.region,
					'localidad': i.localidad,
					'departamento': i.departamento,
					'ambito':i.ambito,
					'sector': i.sector,
					'alumnos': alumnos_conteo,
					'matematica': alumno_examen_matematica,
					'lengua': alumno_examen_lengua
				})
		#print(f'cueanexo{i.cueanexo},Escuela:{i.escuela},Region:{i.region},Localidad{i.localidad},Departamento:{i.departamento}alumnos{alumnos_conteo},matematica{alumno_examen_matematica},lengua{alumno_examen_lengua}')
	contexto={'lista':monitoreo_total,
		   'regiones':establecimientos_region,
		   'alumnos_total':alumnos_total}
	return render(request, 'diagnostico_2026/monitoreo_diagnostico.html', contexto)