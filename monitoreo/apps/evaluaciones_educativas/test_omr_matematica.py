from pathlib import Path

from django.test import SimpleTestCase

from apps.evaluaciones_educativas.views.omr_lector import _campos_lectura
from apps.evaluaciones_educativas.views.omr_utils import procesar_imagen


SAMPLES = (
    Path(__file__).parent
    / "static"
    / "evaluaciones_educativas"
    / "imagenes-examen"
    / "examan-matematica"
)
EXPECTED = "ABCDABCDABCDABCDABCDABCD"


class OMRMatematicaTests(SimpleTestCase):
    def test_reads_new_24_item_form_from_all_available_photos(self):
        photos = sorted(SAMPLES.glob("*.jpeg"))
        if not photos:
            self.skipTest("No están disponibles las fotos locales de Matemática.")

        for photo in photos:
            with self.subTest(photo=photo.name):
                result = procesar_imagen(photo.read_bytes(), tipo_examen="matematica")
                detected = "".join(
                    result["respuestas"][str(item)] or "-"
                    for item in range(1, 25)
                )
                self.assertEqual(detected, EXPECTED, result)

    def test_rejects_unknown_exam_type(self):
        photo = next(iter(sorted(SAMPLES.glob("*.jpeg"))), None)
        if photo is None:
            self.skipTest("No están disponibles las fotos locales de Matemática.")
        with self.assertRaisesRegex(ValueError, "tipo de examen"):
            procesar_imagen(photo.read_bytes(), tipo_examen="desconocido")

    def test_maps_all_24_answers_to_database_fields(self):
        responses = {
            str(item): EXPECTED[item - 1] for item in range(1, 25)
        }
        payload = {
            "lecturas": {
                "imagen_1": {
                    "respuestas": responses,
                    "confianza": {str(item): 80 for item in range(1, 25)},
                },
            },
            "modelo_examen": "B",
            "revisado_manualmente": True,
            "observaciones": "",
        }
        fields = _campos_lectura(payload, "matematica", (24,), "12345678901")
        self.assertEqual(fields["tipo_examen"], "matematica")
        self.assertEqual(fields["item_1"], "A")
        self.assertEqual(fields["item_24"], "D")
        self.assertEqual(len(fields["confianza_json"]), 24)
        self.assertEqual(fields["encargado_carga"], "123456789")
