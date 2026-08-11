"""Lectura OMR de la grilla de respuestas de los exámenes 2026.

El detector usa la geometría impresa de la grilla, no posiciones relativas a la
foto. Esto permite procesar fotos cercanas, hojas completas, perspectiva y giros
de 90/180 grados. Las respuestas 10-12 se proyectan usando la misma homografía.
"""

from __future__ import annotations

import io
from dataclasses import dataclass

import cv2
import numpy as np


LETTERS = ("A", "B", "C", "D")
CONF_LOW = 45
GRID_W, GRID_H = 1200, 900
EXTENDED_H = 1450
MAX_IMAGE_SIDE = 1800


@dataclass
class _GridDetection:
    corners: np.ndarray
    score: float
    method: str


def _decode_image(image_bytes: bytes) -> np.ndarray:
    """Aplica EXIF, decodifica y reduce fotos grandes conservando proporciones."""
    try:
        from PIL import Image, ImageOps

        pil = ImageOps.exif_transpose(Image.open(io.BytesIO(image_bytes))).convert("RGB")
        image = cv2.cvtColor(np.asarray(pil), cv2.COLOR_RGB2BGR)
    except Exception:
        image = cv2.imdecode(np.frombuffer(image_bytes, np.uint8), cv2.IMREAD_COLOR)

    if image is None:
        raise ValueError("No se pudo decodificar la imagen. Verificá el formato (JPG/PNG/WEBP).")

    height, width = image.shape[:2]
    scale = min(1.0, MAX_IMAGE_SIDE / max(height, width))
    if scale < 1.0:
        image = cv2.resize(image, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    return image


def _binarize(gray: np.ndarray) -> np.ndarray:
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    return cv2.adaptiveThreshold(
        blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV, 31, 7,
    )


def _sort_corners(points: np.ndarray) -> np.ndarray:
    points = points.reshape(4, 2).astype(np.float32)
    sums = points.sum(axis=1)
    diffs = np.diff(points, axis=1).ravel()
    return np.array([
        points[np.argmin(sums)], points[np.argmin(diffs)],
        points[np.argmax(sums)], points[np.argmax(diffs)],
    ], dtype=np.float32)


def _landscape_corners(points: np.ndarray) -> np.ndarray:
    """Ordena TL/TR/BR/BL y gira el cuadrilátero si aparece vertical."""
    points = _sort_corners(points)
    width = max(np.linalg.norm(points[1] - points[0]), np.linalg.norm(points[2] - points[3]))
    height = max(np.linalg.norm(points[3] - points[0]), np.linalg.norm(points[2] - points[1]))
    if height > width:
        points = np.array([points[3], points[0], points[1], points[2]], dtype=np.float32)
    return points


def _warp(gray: np.ndarray, corners: np.ndarray, height: int = GRID_H) -> tuple[np.ndarray, np.ndarray]:
    destination = np.array(
        [[0, 0], [GRID_W - 1, 0], [GRID_W - 1, GRID_H - 1], [0, GRID_H - 1]],
        dtype=np.float32,
    )
    matrix = cv2.getPerspectiveTransform(corners, destination)
    return cv2.warpPerspective(gray, matrix, (GRID_W, height), borderValue=255), matrix


def _grid_line_score(gray: np.ndarray, corners: np.ndarray) -> float:
    """Valida las cuatro líneas verticales y horizontales de una grilla 3x3."""
    warped, _ = _warp(gray, corners)
    binary = _binarize(warped)
    values: list[float] = []
    for x in (0, GRID_W // 3, 2 * GRID_W // 3, GRID_W - 1):
        strip = binary[:, max(0, x - 22):min(GRID_W, x + 23)]
        values.append(float(np.max(np.mean(strip > 0, axis=0))))
    for y in (0, GRID_H // 3, 2 * GRID_H // 3, GRID_H - 1):
        strip = binary[max(0, y - 22):min(GRID_H, y + 23), :]
        values.append(float(np.max(np.mean(strip > 0, axis=1))))
    return float(np.mean(values))


def _quad_from_contour(contour: np.ndarray) -> np.ndarray | None:
    perimeter = cv2.arcLength(contour, True)
    for epsilon in (0.005, 0.01, 0.015, 0.02, 0.03, 0.04):
        approx = cv2.approxPolyDP(contour, epsilon * perimeter, True)
        if len(approx) == 4 and cv2.isContourConvex(approx):
            return approx
    return None


def _find_grid(gray: np.ndarray) -> _GridDetection | None:
    """Busca primero la grilla completa y luego reconstruye sus celdas."""
    binary = _binarize(gray)
    image_area = float(binary.size)
    contours, _ = cv2.findContours(binary, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)

    best: _GridDetection | None = None
    cell_contours: list[tuple[float, np.ndarray]] = []

    for contour in contours:
        area = cv2.contourArea(contour)
        area_fraction = area / image_area
        if area_fraction < 0.012 or area_fraction > 0.92:
            continue

        rect = cv2.minAreaRect(contour)
        rect_w, rect_h = rect[1]
        if min(rect_w, rect_h) <= 0:
            continue
        aspect = max(rect_w, rect_h) / min(rect_w, rect_h)

        if 0.025 <= area_fraction <= 0.75 and 1.0 <= aspect <= 1.75:
            cell_contours.append((area_fraction, contour))

        if area_fraction < 0.075:
            continue
        quad = _quad_from_contour(contour)
        if quad is None:
            continue
        corners = _landscape_corners(quad)
        top = np.linalg.norm(corners[1] - corners[0])
        left = np.linalg.norm(corners[3] - corners[0])
        ratio = top / max(left, 1.0)
        if not 1.0 <= ratio <= 1.7:
            continue
        score = _grid_line_score(gray, corners)
        if score >= 0.52 and (best is None or score > best.score):
            best = _GridDetection(corners, score, "grid")

    if best is not None:
        return best

    # En primeros planos algunas líneas gruesas quedan abiertas y OpenCV sólo
    # encuentra 6-9 celdas. Su envolvente reconstruye el borde de la tabla.
    if len(cell_contours) >= 5:
        areas = np.array([area for area, _ in cell_contours])
        typical = float(np.median(areas[areas <= np.percentile(areas, 75)]))
        selected = [
            contour for area, contour in cell_contours
            if typical * 0.60 <= area <= typical * 3.40
        ]
        if len(selected) >= 5:
            all_points = np.vstack([contour.reshape(-1, 2) for contour in selected]).astype(np.float32)
            table_rect = cv2.minAreaRect(all_points)
            # Si el encuadre corta una columna, las celdas visibles permiten
            # extrapolar el ancho completo de las tres columnas.
            individuals = [
                contour for area, contour in cell_contours
                if typical * .60 <= area <= typical * 1.65
            ]
            if individuals:
                boxes = [cv2.boundingRect(contour) for contour in individuals]
                cell_width = float(np.median([box[2] for box in boxes]))
                cell_height = float(np.median([box[3] for box in boxes]))
                x, y, width, height = cv2.boundingRect(all_points)
                # El fallback corresponde a primeros planos casi alineados. La
                # orientación de una celda revela si falta una fila o columna.
                target_width = max(width, cell_width * 3)
                target_height = max(height, cell_height * 3)
                x2, y2 = x + int(target_width), y + int(target_height)
                x2, y2 = max(x + 2, x2), max(y + 2, y2)
                corners = _landscape_corners(np.array(
                    [[x, y], [x2, y], [x2, y2], [x, y2]], dtype=np.float32,
                ))
            else:
                corners = _landscape_corners(cv2.boxPoints(table_rect))
            score = _grid_line_score(gray, corners)
            if score >= 0.15:
                return _GridDetection(corners, score, "cells")
    return None


def _orientation_score(binary: np.ndarray) -> float:
    """El texto y los casilleros están en el tercio izquierdo de cada celda."""
    score = 0.0
    for row in range(3):
        for col in range(3):
            cell = binary[
                row * GRID_H // 3:(row + 1) * GRID_H // 3,
                col * GRID_W // 3:(col + 1) * GRID_W // 3,
            ]
            h, w = cell.shape
            left = np.mean(cell[int(h * .16):int(h * .94), int(w * .03):int(w * .40)] > 0)
            right = np.mean(cell[int(h * .16):int(h * .94), int(w * .60):int(w * .96)] > 0)
            score += float(left - right)
    return score


def _needs_rotation(warped: np.ndarray) -> bool:
    grid = warped[:GRID_H]
    binary = _binarize(grid)
    rotated_binary = _binarize(cv2.rotate(grid, cv2.ROTATE_180))
    return _orientation_score(rotated_binary) > _orientation_score(binary)


def _region_density(binary: np.ndarray, x1: float, y1: float, x2: float, y2: float) -> float:
    height, width = binary.shape
    ax, ay = max(0, int(x1)), max(0, int(y1))
    bx, by = min(width, int(x2)), min(height, int(y2))
    if bx <= ax or by <= ay:
        return 0.0
    return float(np.mean(binary[ay:by, ax:bx] > 0))


def _option_score(binary: np.ndarray, cell_x: float, cell_y: float, cell_w: float,
                  cell_h: float, option: int) -> float:
    """Combina tinta del renglón (acepta círculos) y relleno del casillero."""
    center_y = cell_y + cell_h * (0.30 + option * 0.18)
    band = _region_density(
        binary,
        cell_x + cell_w * .035, center_y - cell_h * .055,
        cell_x + cell_w * .385, center_y + cell_h * .055,
    )
    # Centro del cuadrado: casi no contiene tinta cuando está vacío.
    box_center = _region_density(
        binary,
        cell_x + cell_w * .195, center_y - cell_h * .038,
        cell_x + cell_w * .285, center_y + cell_h * .038,
    )
    return band + box_center * 0.95


def _decide(scores: list[float]) -> tuple[str, int]:
    order = np.argsort(scores)[::-1]
    first, second = float(scores[order[0]]), float(scores[order[1]])
    baseline = float(np.median(scores))
    contrast = first - second
    elevation = first - baseline

    third = float(scores[order[2]])
    double_mark = second / max(first, 1e-6) >= .82 and second - third >= .05

    # Dos opciones marcadas se devuelven vacías para obligar a revisión manual.
    marked = (
        not double_mark and elevation >= 0.030
        and contrast >= 0.050 and first >= 0.105
    )
    if not marked:
        confidence = int(np.clip(max(elevation, contrast) / 0.06 * 35, 0, 39))
        return "", confidence

    contrast_score = np.clip((contrast - 0.050) / 0.10, 0, 1)
    elevation_score = np.clip((elevation - 0.030) / 0.16, 0, 1)
    confidence = int(np.clip(55 + 30 * contrast_score + 15 * elevation_score, 0, 99))
    return LETTERS[int(order[0])], confidence


def _read_student(binary: np.ndarray) -> tuple[dict[int, str], dict[int, int]]:
    responses: dict[int, str] = {}
    confidence: dict[int, int] = {}
    cell_w, cell_h = GRID_W / 3, GRID_H / 3
    for row in range(3):
        for col in range(3):
            item = row * 3 + col + 1
            scores = [
                _option_score(binary, col * cell_w, row * cell_h, cell_w, cell_h, option)
                for option in range(4)
            ]
            responses[item], confidence[item] = _decide(scores)
    return responses, confidence


def _read_teacher(binary: np.ndarray) -> tuple[dict[int, str], dict[int, int]]:
    responses: dict[int, str] = {}
    confidence: dict[int, int] = {}
    x_centers = (.101, .177, .247, .318)
    y_centers = (1.310, 1.382, 1.454)
    for row, item in enumerate((10, 11, 12)):
        scores = []
        for x_center in x_centers:
            density = _region_density(
                binary,
                GRID_W * (x_center - .025), GRID_H * (y_centers[row] - .030),
                GRID_W * (x_center + .025), GRID_H * (y_centers[row] + .030),
            )
            scores.append(density)
        order = np.argsort(scores)[::-1]
        first, second = float(scores[order[0]]), float(scores[order[1]])
        # Esta sección tiene letras muy juntas. Sólo aceptamos un relleno claro;
        # tildes tenues quedan como dudosas para no inventar una respuesta.
        if first >= .40 and first - second >= .08:
            responses[item] = LETTERS[int(order[0])]
            confidence[item] = int(np.clip(60 + (first - second) * 180, 60, 99))
        else:
            responses[item] = ""
            confidence[item] = int(np.clip((first - second) * 100, 0, 39))
    return responses, confidence


def procesar_imagen(imagen_bytes: bytes) -> dict:
    """Procesa una foto y devuelve respuestas, confianza y diagnóstico OMR."""
    image = _decode_image(imagen_bytes)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    detection = _find_grid(gray)

    empty_responses = {str(item): "" for item in range(1, 13)}
    empty_confidence = {str(item): 0 for item in range(1, 13)}
    if detection is None:
        return {
            "respuestas": empty_responses,
            "confianza": empty_confidence,
            "items_dudosos": list(range(1, 13)),
            "used_warp": False,
            "detection_method": "not_found",
            "detection_score": 0,
        }

    corners = detection.corners.copy()
    warped, matrix = _warp(gray, corners, EXTENDED_H)
    rotated_180 = _needs_rotation(warped)
    if rotated_180:
        corners = np.roll(corners, 2, axis=0)
        warped, matrix = _warp(gray, corners, EXTENDED_H)
    binary = _binarize(warped)

    responses, confidence = _read_student(binary)
    teacher_responses, teacher_confidence = _read_teacher(binary)
    responses.update(teacher_responses)
    confidence.update(teacher_confidence)

    doubtful = [
        item for item in range(1, 13)
        if not responses[item] or confidence[item] < CONF_LOW
    ]
    inverse = np.linalg.inv(matrix)
    doc_canonical = np.array([[
        [0, GRID_H * 1.22], [GRID_W - 1, GRID_H * 1.22],
        [GRID_W - 1, GRID_H * 1.55], [0, GRID_H * 1.55],
    ]], dtype=np.float32)
    doc_source = cv2.perspectiveTransform(doc_canonical, inverse)[0]
    image_h, image_w = gray.shape
    doc_x, doc_y, doc_w, doc_h = cv2.boundingRect(doc_source)

    return {
        "respuestas": {str(key): value for key, value in responses.items()},
        "confianza": {str(key): value for key, value in confidence.items()},
        "items_dudosos": doubtful,
        "used_warp": True,
        "detection_method": detection.method,
        "detection_score": round(detection.score, 3),
        "rotated_180": rotated_180,
        "student_box": tuple(int(value) for value in cv2.boundingRect(corners)),
        "doc_box": (doc_x, doc_y, doc_w, doc_h),
        "image_size": (image_w, image_h),
    }
