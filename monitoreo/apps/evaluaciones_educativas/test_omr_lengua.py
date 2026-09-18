from decimal import Decimal
from pathlib import Path

from django.core.exceptions import ValidationError
from django.test import SimpleTestCase

from apps.evaluaciones_educativas.models.omr_lector import ExamenLengua
from apps.evaluaciones_educativas.views.omr_lector import (
    _campos_lectura,
    _validar_payload_lectura,
)
from apps.evaluaciones_educativas.views.omr_utils import procesar_imagen


SAMPLES = (
    Path(__file__).parent
    / "static"
    / "evaluaciones_educativas"
    / "imagenes-examen"
    / "examen-lengua"
)
MODEL_B_FILENAMES = {
    "WhatsApp Image 2026-09-18 at 07.44.09.jpeg",
    "WhatsApp Image 2026-09-18 at 07.44.09 (1).jpeg",
    "WhatsApp Image 2026-09-18 at 07.44.09 (2).jpeg",
    "WhatsApp Image 2026-09-18 at 07.44.10.jpeg",
    "WhatsApp Image 2026-09-18 at 07.44.10 (1).jpeg",
    "WhatsApp Image 2026-09-18 at 07.44.10 (2).jpeg",
    "WhatsApp Image 2026-09-18 at 07.44.10 (3).jpeg",
    "WhatsApp Image 2026-09-18 at 07.44.11 (2).jpeg",
}
BLANK_FILENAME = "WhatsApp Image 2026-09-18 at 07.44.13 (2).jpeg"
MODEL_B_RESPONSES = "ABACDADBCDDABCAABCAD"
MODEL_B_TEACHER = "ADCBDCA"
MODEL_A_TEACHER = "AB-ADBC"


class OMRLenguaTests(SimpleTestCase):
    def test_uses_a_separate_model_with_semantic_item_names(self):
        self.assertEqual(
            ExamenLengua._meta.db_table,
            '"diagnostico_ingreso_2026"."examenes_lengua"',
        )
        self.assertEqual(ExamenLengua().cantidad_items, 27)
        self.assertEqual(ExamenLengua.campo_item(24), "item_24")
        self.assertEqual(ExamenLengua.campo_item(25), "item_24_1")
        self.assertEqual(ExamenLengua.etiqueta_item(27), "24.3")

    def test_scores_model_key_and_teacher_rubric_up_to_100_points(self):
        exam = ExamenLengua(modelo_examen="A")
        for item, response in ExamenLengua.RESPUESTAS_CORRECTAS_LENGUA["A"].items():
            setattr(exam, ExamenLengua.campo_item(item), response)
        for item in range(21, 28):
            setattr(exam, ExamenLengua.campo_item(item), "A")

        exam.actualizar_puntajes()

        self.assertEqual(exam.puntaje_total, Decimal("100.00"))
        self.assertEqual(exam.puntajes_json["24.1"], 6.0)
        exam.item_1 = "A"
        self.assertEqual(exam.puntaje_item_lengua(1), Decimal("0"))

    def test_model_only_accepts_a_or_b(self):
        with self.assertRaises(ValidationError):
            ExamenLengua(modelo_examen="C").clean()

    def test_maps_27_answers_to_language_database_fields(self):
        responses = {
            str(item): "ABCD"[(item - 1) % 4] for item in range(1, 28)
        }
        payload = {
            "lecturas": {
                "imagen_1": {
                    "respuestas": responses,
                    "confianza": {str(item): 80 for item in range(1, 28)},
                },
            },
            "modelo_examen": "B",
            "revisado_manualmente": True,
        }
        normalized = _validar_payload_lectura(payload, (27,), "lengua")
        fields = _campos_lectura(normalized, "lengua", (27,), "12345678901")

        self.assertEqual(fields["modelo_examen"], "B")
        self.assertEqual(fields["item_24"], "D")
        self.assertEqual(fields["item_24_1"], "A")
        self.assertEqual(fields["item_24_3"], "C")
        self.assertEqual(len(fields["confianza_json"]), 27)
        self.assertNotIn("tipo_examen", fields)

    def test_requires_language_model_in_payload(self):
        payload = {
            "lecturas": {
                "imagen_1": {
                    "respuestas": {str(item): "A" for item in range(1, 28)},
                    "confianza": {str(item): 80 for item in range(1, 28)},
                },
            },
            "modelo_examen": "",
            "revisado_manualmente": True,
        }
        with self.assertRaisesRegex(ValueError, "modelo A o B"):
            _validar_payload_lectura(payload, (27,), "lengua")

    def test_accepts_and_maps_a_confirmed_blank_answer(self):
        responses = {str(item): "A" for item in range(1, 28)}
        responses["7"] = ""
        payload = {
            "lecturas": {
                "imagen_1": {
                    "respuestas": responses,
                    "confianza": {
                        str(item): 100 for item in range(1, 28)
                    },
                },
            },
            "modelo_examen": "A",
            "revisado_manualmente": True,
        }

        normalized = _validar_payload_lectura(payload, (27,), "lengua")
        fields = _campos_lectura(normalized, "lengua", (27,), "123456789")

        self.assertEqual(fields["item_7"], "")
        self.assertEqual(fields["confianza_json"]["7"], 100)
        exam = ExamenLengua(**fields)
        exam.clean()
        exam.actualizar_puntajes()
        self.assertEqual(exam.puntaje_item_lengua(7), Decimal("0"))

    def test_observations_are_not_part_of_the_save_contract(self):
        payload = {
            "lecturas": {
                "imagen_1": {
                    "respuestas": {str(item): "A" for item in range(1, 28)},
                    "confianza": {str(item): 100 for item in range(1, 28)},
                },
            },
            "modelo_examen": "A",
            "revisado_manualmente": True,
            "observaciones": "No debe aceptarse",
        }
        with self.assertRaisesRegex(ValueError, "Campos no permitidos"):
            _validar_payload_lectura(payload, (27,), "lengua")

    def test_reads_models_and_marks_from_all_available_photos(self):
        photos = sorted(SAMPLES.glob("*.jpeg"))
        if not photos:
            self.skipTest("No están disponibles las fotos locales de Lengua.")

        for photo in photos:
            with self.subTest(photo=photo.name):
                result = procesar_imagen(photo.read_bytes(), tipo_examen="lengua")
                main = "".join(
                    result["respuestas"][str(item)] or "-"
                    for item in range(1, 21)
                )
                teacher = "".join(
                    result["respuestas"][str(item)] or "-"
                    for item in range(21, 28)
                )
                if photo.name in MODEL_B_FILENAMES:
                    self.assertEqual(result["modelo_examen"], "B", result)
                    self.assertEqual(main, MODEL_B_RESPONSES, result)
                    self.assertEqual(teacher, MODEL_B_TEACHER, result)
                elif photo.name == BLANK_FILENAME:
                    self.assertEqual(result["modelo_examen"], "", result)
                    self.assertEqual(main, "-" * 20, result)
                    self.assertEqual(teacher, "-" * 7, result)
                else:
                    self.assertEqual(result["modelo_examen"], "A", result)
                    self.assertGreaterEqual(main.count("-"), 1, result)
                    # Las hojas A contienen dobles marcas intencionales; deben
                    # quedar vacías para revisión, no convertirse en aciertos.
                    self.assertGreaterEqual(20 - main.count("-"), 16, result)
                    self.assertEqual(teacher, MODEL_A_TEACHER, result)
