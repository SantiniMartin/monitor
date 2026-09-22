from pathlib import Path
from types import SimpleNamespace
from django.template.loader import render_to_string

context = {
    'alumno': SimpleNamespace(id_alumno='qa-camera', nombre='Prueba', apellido='Local'),
    'materia': 'contexto', 'materia_nombre': 'Contexto',
    'nombres_hojas': ['Hoja 1', 'Hoja 2'], 'total_hojas': 2,
    'items_por_hoja': [8, 9], 'opciones_contexto': [6] * 17,
    'items_multiples_contexto': [1, 4, 7, 8, 14],
    'modo_simulacion': True, 'csrf_token': 'local-test',
}
Path('../output/playwright/omr-portrait.html').write_text(
    render_to_string('omr_lector/lector.html', context), encoding='utf-8')
