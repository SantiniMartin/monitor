from pathlib import Path

from django.test import SimpleTestCase

from apps.evaluaciones_educativas.views.omr_utils import procesar_imagen


SAMPLES = Path(__file__).parent / "static" / "evaluaciones_educativas" / "omr-mejorado"


class OMRProcessorTests(SimpleTestCase):
    expected_gomez = {
        "1": "C", "2": "A", "3": "B", "4": "D", "5": "A",
        "6": "B", "7": "C", "8": "D", "9": "C",
    }

    def _process(self, filename):
        return procesar_imagen((SAMPLES / filename).read_bytes())

    def test_reads_rotated_exam(self):
        result = self._process("WhatsApp Image 2026-08-11 at 04.17.30 (4).jpeg")
        self.assertEqual(
            {key: result["respuestas"][key] for key in self.expected_gomez},
            self.expected_gomez,
        )

    def test_reconstructs_grid_when_right_border_is_cropped(self):
        result = self._process("WhatsApp Image 2026-08-11 at 04.17.30 (5).jpeg")
        self.assertEqual(
            {key: result["respuestas"][key] for key in self.expected_gomez},
            self.expected_gomez,
        )
        self.assertEqual(result["detection_method"], "cells")

    def test_double_mark_is_reported_as_doubtful(self):
        result = self._process("WhatsApp Image 2026-08-11 at 04.17.28.jpeg")
        self.assertEqual(result["respuestas"]["7"], "")
        self.assertIn(7, result["items_dudosos"])

    def test_reads_faint_pencil_marks(self):
        expected = "DCDACACCB"
        for filename in (
            "WhatsApp Image 2026-08-11 at 04.49.11 (1).jpeg",
            "WhatsApp Image 2026-08-11 at 04.49.11 (2).jpeg",
        ):
            with self.subTest(filename=filename):
                result = self._process(filename)
                detected = "".join(result["respuestas"][str(item)] for item in range(1, 10))
                self.assertEqual(detected, expected)

    def test_reads_ticks_circles_double_marks_and_teacher_section(self):
        result = self._process("WhatsApp Image 2026-08-11 at 04.49.11.jpeg")
        detected = "".join(
            result["respuestas"][str(item)] or "-" for item in range(1, 13)
        )
        self.assertEqual(detected, "ADB--CDAAABD")
        self.assertIn(4, result["items_dudosos"])
        self.assertIn(5, result["items_dudosos"])

    def test_invalid_image_raises_value_error(self):
        with self.assertRaises(ValueError):
            procesar_imagen(b"not an image")
