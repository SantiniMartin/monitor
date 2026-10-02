from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.urls import reverse, NoReverseMatch


@login_required
def dashboard(request):
    usuario = request.user
    rol = getattr(usuario, 'nivelacceso_id', None) or ''
    if hasattr(rol, 'strip'):
        rol = rol.strip()

    es_director = (rol == 'Director/a')
    es_regional = (rol == 'Regional')
    es_funcionario = rol in ['Funcionario', 'Ministro', 'Subse']
    if usuario.is_superuser and not (es_director or es_regional or es_funcionario):
        es_funcionario = True

    # ================================================================
    # OPERATIVOS
    # Jerarquía: Operativo ➔ Años ➔ Meses del Operativo ➔ Links
    #
    # Campos de cada link:
    #   titulo      → texto del botón
    #   icono       → clase Bootstrap Icon (ej: 'bi-bar-chart-line')
    #   roles       → lista de nivelacceso_id con permiso para ver el link
    #   url         → nombre de URL Django (mismo para todos los roles)
    #   url_director / url_regional / url_funcionario
    #               → cuando la URL destino cambia según el rol
    # ================================================================
    operativos = [

        # ── Fluidez Lectora ──────────────────────────────────────────
        {
            'id':          'fluidez',
            'titulo':      'Fluidez Lectora',
            'descripcion': 'Evaluación de fluidez y comprensión lectora',
            'icono':       'bi-book-half',
            'color':       '#00bcd4',
            'anios': [
                {
                    'anio': '2026',
                    'meses': [
                        {
                            'mes':         'Junio',
                            'descripcion': 'Evaluación — Junio 2026',
                            'icono':       'bi-calendar-event',
                            'links': [
                                {
                                    'titulo': 'Carga de datos',
                                    'icono':  'bi-pencil-square',
                                    'url':    'evaluaciones_educativas:fluidez_2026:lista',
                                    'roles':  ['Director/a'],
                                },
                                {
                                    'titulo':          'Análisis de Resultados',
                                    'icono':           'bi-bar-chart-line',
                                    'url_director':    'evaluaciones_educativas:fluidez_2026:analisis_evaluacion',
                                    'url_regional':    'evaluaciones_educativas:fluidez_2026:analisis_evaluacion_junio_2026',
                                    'url_funcionario': 'evaluaciones_educativas:fluidez_2026:analisis_completo_evaluacion_junio_2026',
                                    'roles':           ['Director/a', 'Regional', 'Funcionario', 'Ministro', 'Subse'],
                                },
                            ],
                        },
                    ],
                },
                {
                    'anio': '2025',
                    'meses': [
                        {
                            'mes':         'Mayo',
                            'descripcion': 'Evaluación — Mayo 2025',
                            'icono':       'bi-calendar-check',
                            'links': [
                                {
                                    'titulo': 'Análisis Mayo 2025',
                                    'icono':  'bi-calendar2-range',
                                    'url':    'evaluaciones_educativas:fluidez_2025:analisis_evaluacion_mayo_2025',
                                    'roles':  ['Director/a'],
                                },
                            ],
                        },
                        {
                            'mes':         'Noviembre',
                            'descripcion': 'Evaluación — Noviembre 2025',
                            'icono':       'bi-calendar-event',
                            'links': [
                                {
                                    'titulo': 'Carga de datos',
                                    'icono':  'bi-pencil-square',
                                    'url':    'evaluaciones_educativas:fluidez_2025:grados',
                                    'roles':  ['Director/a'],
                                },
                                {
                                    'titulo':          'Análisis Noviembre 2025',
                                    'icono':           'bi-bar-chart-steps',
                                    'url_director':    'evaluaciones_educativas:fluidez_2025:analisis_evaluacion',
                                    'url_regional':    'evaluaciones_educativas:fluidez_2025:analisis_evaluacion_noviembre_2025',
                                    'url_funcionario': 'evaluaciones_educativas:fluidez_2025:analisis_completo_evaluacion_noviembre_2025',
                                    'roles':           ['Director/a', 'Regional', 'Funcionario', 'Ministro', 'Subse'],
                                },
                            ],
                        },
                    ],
                },
            ],
        },

        # ── Diagnóstico ──────────────────────────────────────────────
        {
            'id':          'diagnostico',
            'titulo':      'Diagnóstico',
            'descripcion': 'Evaluación diagnóstica institucional',
            'icono':       'bi-journal-medical',
            'color':       '#6366f1',
            'anios': [
                {
                    'anio': '2026',
                    'meses': [
                        {
                            'mes':         'Diagnóstico 2026',
                            'descripcion': 'Evaluación diagnóstica — 2026',
                            'icono':       'bi-calendar-check',
                            'links': [
                                {
                                    'titulo': 'Carga de datos',
                                    'icono':  'bi-pencil-square',
                                    'url':    'evaluaciones_educativas:diagnostico_2026:inicio',
                                    'roles':  ['Director/a'],
                                },
                                {
                                    'titulo': 'Análisis de Resultados',
                                    'icono':  'bi-graph-up-arrow',
                                    'url':    'evaluaciones_educativas:diagnostico_2026:analisis_evaluacion',
                                    'roles':  ['Director/a', 'Regional', 'Funcionario', 'Ministro', 'Subse'],
                                },
                                # {
                                #     'titulo': 'Progreso de Alumnos',
                                #     'icono':  'bi-person-lines-fill',
                                #     'url':    'evaluaciones_educativas:diagnostico_2026:progreso_alumnos',
                                #     'roles':  ['Director/a', 'Regional', 'Funcionario', 'Ministro', 'Subse'],
                                # },
                            ],
                        },
                    ],
                },
                {
                    'anio': '2025',
                    'meses': [
                        {
                            'mes':         'Diagnóstico 2025',
                            'descripcion': 'Datos históricos — 2025',
                            'icono':       'bi-calendar2-check',
                            'links': [
                                {
                                    'titulo': 'Análisis de Resultados',
                                    'icono':  'bi-graph-up-arrow',
                                    'url':    'evaluaciones_educativas:diagnostico_2025:analisis_evaluacion',
                                    'roles':  ['Director/a', 'Regional', 'Funcionario', 'Ministro', 'Subse'],
                                },
                            ],
                        },
                    ],
                },
            ],
        },

        # ── Validaciones Aprender 2026 ───────────────────────────────
        # {
        #     'id':          'validaciones_2026',
        #     'titulo':      'Validaciones Aprender',
        #     'descripcion': 'Validar secciones, establecimientos y matrículas',
        #     'icono':       'bi-check2-circle',
        #     'color':       '#06b6d4',
        #     'anios': [
        #         {
        #             'anio': '2026',
        #             'meses': [
        #                 {
        #                     'mes':         'Aprender 2026',
        #                     'descripcion': 'Validaciones de matrícula y secciones',
        #                     'icono':       'bi-calendar-check',
        #                     'links': [
        #                         {
        #                             'titulo': 'Gestión de Validaciones',
        #                             'icono':  'bi-shield-check',
        #                             'url':    'evaluaciones_educativas:validaciones_2026:lista',
        #                             'roles':  ['Regional', 'Funcionario', 'Ministro', 'Subse'],
        #                         },
        #                     ],
        #                 },
        #             ],
        #         },
        #     ],
        # },

        # ── Fluidez Lectora Octubre 2026 (Tabuladores) ───────────────
        {
            'id':          'fluidez_octubre',
            'titulo':      'Fluidez Lectora — Octubre 2026',
            'descripcion': 'Gestión de tabuladores y asignación de establecimientos',
            'icono':       'bi-journal-text',
            'color':       '#f59e0b',
            'anios': [
                {
                    'anio': '2026',
                    'meses': [
                        {
                            'mes':         'Octubre',
                            'descripcion': 'Evaluación — Octubre 2026',
                            'icono':       'bi-calendar-event',
                            'links': [
                                {
                                    'titulo': 'Gestión de Tabuladores',
                                    'icono':  'bi-people-fill',
                                    'url':    'evaluaciones_educativas:fluidez_octubre_2026:gestion_tabuladores',
                                    'roles':  ['Regional'],
                                },
                            ],
                        },
                    ],
                },
            ],
        },

    ]

    # ── Filtrar por rol y resolver URLs ──────────────────────────────
    operativos_visibles = []
    for op in operativos:
        anios_visibles = []
        for anio_data in op.get('anios', []):
            meses_visibles = []
            for mes_data in anio_data.get('meses', []):
                links_visibles = []
                for link in mes_data.get('links', []):
                    # Verificar si el rol del usuario está autorizado para este link
                    rol_autorizado = (rol in link['roles']) or (
                        usuario.is_superuser and any(r in ['Funcionario', 'Ministro', 'Subse'] for r in link['roles'])
                    )
                    if not rol_autorizado:
                        continue

                    # Resolver URL según el rol del usuario
                    url_name = None
                    if 'url' in link:
                        url_name = link['url']
                    elif es_director and 'url_director' in link:
                        url_name = link['url_director']
                    elif es_regional and 'url_regional' in link:
                        url_name = link['url_regional']
                    elif es_funcionario and 'url_funcionario' in link:
                        url_name = link['url_funcionario']
                    else:
                        continue

                    try:
                        url_resuelta = reverse(url_name)
                    except NoReverseMatch:
                        continue

                    links_visibles.append({
                        'titulo': link['titulo'],
                        'icono':  link['icono'],
                        'url':    url_resuelta,
                    })

                if links_visibles:
                    meses_visibles.append({
                        'mes':         mes_data['mes'],
                        'descripcion': mes_data.get('descripcion', ''),
                        'icono':       mes_data.get('icono', 'bi-calendar3'),
                        'links':       links_visibles,
                    })

            if meses_visibles:
                anios_visibles.append({
                    'anio':  anio_data['anio'],
                    'meses': meses_visibles,
                })

        # Solo mostrar el operativo si tiene al menos un año con meses y links visibles
        if anios_visibles:
            operativos_visibles.append({
                'id':          op['id'],
                'titulo':      op['titulo'],
                'descripcion': op['descripcion'],
                'icono':       op['icono'],
                'color':       op['color'],
                'anios':       anios_visibles,
            })

    context = {
        'title':          'Evaluaciones Educativas',
        'usuario':        usuario,
        'rol':            rol,
        'es_director':    es_director,
        'es_regional':    es_regional,
        'es_funcionario': es_funcionario,
        'operativos':     operativos_visibles,
    }
    return render(request, 'evaluaciones_educativas/dashboard.html', context)
