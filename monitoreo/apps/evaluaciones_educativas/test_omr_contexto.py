from pathlib import Path

import cv2
import numpy as np
from django.core.exceptions import ValidationError
from django.test import SimpleTestCase

from apps.evaluaciones_educativas.models.omr_lector import (
    ExamenContexto,
    ExamenMatematica,
)
from apps.evaluaciones_educativas.services.omr_catalogo import (
    ITEMS_MULTIPLES_CONTEXTO,
    SIMULATION_MODE,
)
from apps.evaluaciones_educativas.views.omr_lector import (
    _campos_lectura,
    _validar_payload_lectura,
)
from apps.evaluaciones_educativas.views.omr_utils import (
    CONTEXT_H,
    CONTEXT_W,
    _context_checkboxes,
    _decode_image,
    _find_context_frame,
    _warp_context,
    procesar_imagen,
)


SAMPLES = (
    Path(__file__).parent
    / "static"
    / "evaluaciones_educativas"
    / "imagenes-examen"
    / "examen-contexto"
)


class OMRContextoTests(SimpleTestCase):
    def _mark_context_boxes(self, filename_suffix, selected_indexes):
        photo = next(iter(sorted(SAMPLES.rglob(f"*{filename_suffix}"))), None)
        if photo is None:
            self.skipTest("No está disponible la plantilla local de Contexto.")
        image = _decode_image(photo.read_bytes())
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        detection = _find_context_frame(gray)
        boxes = _context_checkboxes(_warp_context(gray, detection.corners))
        canonical = np.array(
            [[0, 0], [CONTEXT_W - 1, 0], [CONTEXT_W - 1, CONTEXT_H - 1], [0, CONTEXT_H - 1]],
            dtype=np.float32,
        )
        inverse = cv2.getPerspectiveTransform(canonical, detection.corners)
        for index in selected_indexes:
            _, _, _, x, y, width, height = boxes[index]
            polygon = np.array([[
                [x + 3, y + 3], [x + width - 3, y + 3],
                [x + width - 3, y + height - 3], [x + 3, y + height - 3],
            ]], dtype=np.float32)
            source_polygon = cv2.perspectiveTransform(polygon, inverse)[0].astype(np.int32)
            cv2.fillConvexPoly(image, source_polygon, (0, 0, 0))
        encoded, data = cv2.imencode('.jpg', image)
        self.assertTrue(encoded)
        return procesar_imagen(data.tobytes(), tipo_examen='contexto')

    def test_contexto_uses_a_separate_database_model(self):
        self.assertFalse(SIMULATION_MODE)
        self.assertEqual(ITEMS_MULTIPLES_CONTEXTO, {1, 4, 7, 8, 14})
        self.assertEqual(ExamenMatematica._meta.model_name, 'examenmatematica')
        self.assertEqual(ExamenContexto._meta.model_name, 'examencontexto')
        self.assertEqual(ExamenContexto._meta.get_field('item_1').max_length, 11)
        self.assertEqual(ExamenContexto._meta.get_field('item_4').max_length, 11)
        self.assertEqual(ExamenContexto._meta.get_field('item_14').max_length, 11)
        self.assertEqual(ExamenContexto._meta.get_field('item_2').max_length, 1)
        self.assertEqual(ExamenContexto._meta.get_field('item_17').max_length, 1)
        self.assertEqual(ExamenContexto().cantidad_items, 17)

    def test_identifies_both_sheets_without_depending_on_upload_order(self):
        photos = sorted(SAMPLES.rglob("*.jpeg"))
        if not photos:
            self.skipTest("No están disponibles las fotos locales de Contexto.")

        detected = [
            procesar_imagen(photo.read_bytes(), tipo_examen="contexto")
            for photo in reversed(photos)
        ]
        expected_pages = [
            1 if photo.parent.name == 'primer-parte' else 2
            for photo in reversed(photos)
        ]
        self.assertEqual(
            [result["numero_hoja"] for result in detected],
            expected_pages,
        )
        for result in detected:
            expected_items = 8 if result["numero_hoja"] == 1 else 9
            self.assertEqual(result["cantidad_items"], expected_items)
            self.assertEqual(len(result["respuestas"]), expected_items)

    def test_reads_the_real_marked_photos_from_both_sheets(self):
        first = SAMPLES / 'primer-parte' / 'WhatsApp Image 2026-09-15 at 09.36.55.jpeg'
        second = SAMPLES / 'segunda-parte' / 'WhatsApp Image 2026-09-15 at 09.36.55.jpeg'
        if not first.exists() or not second.exists():
            self.skipTest("No están disponibles las fotos marcadas de Contexto.")
        first_result = procesar_imagen(first.read_bytes(), tipo_examen='contexto')
        second_result = procesar_imagen(second.read_bytes(), tipo_examen='contexto')
        self.assertEqual(first_result['numero_hoja'], 1)
        self.assertEqual(
            list(first_result['respuestas'].values()),
            ['A', 'B', 'B', 'C', 'A', 'B', 'A,C', 'A,C,D'],
        )
        self.assertEqual(second_result['numero_hoja'], 2)
        self.assertEqual(
            list(second_result['respuestas'].values()),
            ['A', '', 'A', 'B', 'A', 'A', 'B', 'D', 'B'],
        )

    def test_reads_marked_photos_with_angles_and_shadows(self):
        expected_by_page = {
            'primer-parte': ['A', 'B', 'B', 'C', 'A', 'B', 'A,C', 'A,C,D'],
            'segunda-parte': ['A', '', 'A', 'B', 'A', 'A', 'B', 'D', 'B'],
        }
        photos = sorted(SAMPLES.rglob('WhatsApp Image 2026-09-15 at 12.*.jpeg'))
        if not photos:
            self.skipTest("No están disponibles las fotos con ángulos y sombras.")
        for photo in photos:
            with self.subTest(photo=photo.name, sheet=photo.parent.name):
                result = procesar_imagen(photo.read_bytes(), tipo_examen='contexto')
                expected_page = 1 if photo.parent.name == 'primer-parte' else 2
                self.assertEqual(result['numero_hoja'], expected_page)
                self.assertEqual(
                    list(result['respuestas'].values()),
                    expected_by_page[photo.parent.name],
                )

    def test_reads_single_and_multiple_marks(self):
        result = self._mark_context_boxes('10.25.33.jpeg', (0, 2, 7, 34))
        self.assertEqual(result['numero_hoja'], 1)
        self.assertEqual(result['respuestas']['1'], 'A,C')
        self.assertEqual(result['respuestas']['2'], 'B')
        self.assertEqual(result['respuestas']['8'], 'F')

    def test_reads_a_fully_answered_first_sheet(self):
        # Trece marcas intensas dejan solo 22 contornos visibles.
        result = self._mark_context_boxes(
            '10.25.33.jpeg',
            (0, 2, 5, 7, 8, 16, 21, 24, 26, 28, 29, 31, 33),
        )
        self.assertEqual(result['numero_hoja'], 1)
        self.assertEqual(
            list(result['respuestas'].values()),
            ['A,C,F', 'B', 'A', 'F', 'E', 'C', 'B,D', 'A,C,E'],
        )

    def test_reads_a_fully_answered_second_sheet(self):
        result = self._mark_context_boxes(
            '10.25.34.jpeg',
            (2, 8, 10, 12, 17, 18, 21, 22, 26, 28, 33),
        )
        self.assertEqual(result['numero_hoja'], 2)
        self.assertEqual(
            list(result['respuestas'].values()),
            ['C', 'F', 'B', 'A', 'C', 'A,D,E', 'D', 'B', 'C'],
        )

    def test_accepts_the_maximum_allowed_marks_on_first_sheet(self):
        result = self._mark_context_boxes(
            '10.25.33.jpeg',
            tuple(range(6)) + (6, 8, 11, 17, 22)
            + tuple(range(25, 29)) + tuple(range(29, 35)),
        )
        self.assertEqual(result['numero_hoja'], 1)
        self.assertEqual(
            list(result['respuestas'].values()),
            ['A,B,C,D,E,F', 'A', 'A', 'A', 'A', 'A',
             'A,B,C,D', 'A,B,C,D,E,F'],
        )

    def test_accepts_context_options_and_multiple_answers(self):
        first = ['A,C,F', 'B', 'C', 'A,F', 'E', 'A', 'B,D', 'A,C,E']
        second = ['C', 'F', 'B', 'A', 'C', 'A,D', 'D', 'B', 'C']
        payload = {
            'lecturas': {
                'imagen_1': {
                    'respuestas': {str(i): value for i, value in enumerate(first, 1)},
                    'confianza': {str(i): 90 for i in range(1, 9)},
                },
                'imagen_2': {
                    'respuestas': {str(i): value for i, value in enumerate(second, 1)},
                    'confianza': {str(i): 90 for i in range(1, 10)},
                },
            },
            'modelo_examen': '',
            'revisado_manualmente': True,
        }
        normalized = _validar_payload_lectura(payload, (8, 9), 'contexto')
        fields = _campos_lectura(normalized, 'contexto', (8, 9), '12345678901')
        self.assertEqual(fields['item_1'], 'A,C,F')
        self.assertEqual(fields['item_4'], 'A,F')
        self.assertEqual(fields['item_8'], 'A,C,E')
        self.assertEqual(fields['item_9'], 'C')
        self.assertEqual(fields['item_17'], 'C')

    def test_rejects_an_option_not_printed_for_the_question(self):
        first = ['A', 'F', 'A', 'A', 'A', 'A', 'A', 'A']
        second = ['A'] * 9
        payload = {
            'lecturas': {
                'imagen_1': {
                    'respuestas': {str(i): value for i, value in enumerate(first, 1)},
                    'confianza': {str(i): 90 for i in range(1, 9)},
                },
                'imagen_2': {
                    'respuestas': {str(i): value for i, value in enumerate(second, 1)},
                    'confianza': {str(i): 90 for i in range(1, 10)},
                },
            },
            'modelo_examen': '',
            'revisado_manualmente': True,
        }
        with self.assertRaisesRegex(ValueError, 'ítem 2'):
            _validar_payload_lectura(payload, (8, 9), 'contexto')

    def test_model_enforces_multiple_and_single_answers(self):
        valid = ExamenContexto(
            item_1='A,C', item_4='B,D,F', item_7='A,C',
            item_8='A,D', item_14='B,E', item_2='B',
        )
        valid.clean()

        invalid = ExamenContexto(item_2='A,B')
        with self.assertRaises(ValidationError) as error:
            invalid.clean()
        self.assertIn('item_2', error.exception.message_dict)
