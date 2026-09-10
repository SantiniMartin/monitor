"""Lectura OMR de la grilla de respuestas de los exámenes 2026.

El detector usa la geometría impresa de cada grilla, no posiciones relativas a
la foto. Admite el formulario de 12 ítems y el de Matemática con una tabla 5×4
más la sección docente de los ítems 21 a 24.
"""

from __future__ import annotations

import io
from dataclasses import dataclass

import cv2
import numpy as np

from apps.evaluaciones_educativas.models.omr_lector import LecturaOMR


# Mantiene el detector sincronizado con las respuestas permitidas por el modelo.
LETTERS = tuple(value for value, _ in LecturaOMR.OPCIONES_RESPUESTA if value)
CONF_LOW = 45
GRID_W, GRID_H = 1200, 900
EXTENDED_H = 1450
MATH_GRID_W, MATH_GRID_H = 1500, 1200
MATH_TEACHER_W, MATH_TEACHER_H = 1200, 360
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


def _warp_math(gray: np.ndarray, corners: np.ndarray,
               height: int = MATH_GRID_H) -> tuple[np.ndarray, np.ndarray]:
    destination = np.array(
        [[0, 0], [MATH_GRID_W - 1, 0],
         [MATH_GRID_W - 1, MATH_GRID_H - 1], [0, MATH_GRID_H - 1]],
        dtype=np.float32,
    )
    matrix = cv2.getPerspectiveTransform(corners, destination)
    return cv2.warpPerspective(
        gray, matrix, (MATH_GRID_W, height), borderValue=255,
    ), matrix


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


def _math_grid_line_score(gray: np.ndarray, corners: np.ndarray) -> float:
    """Valida las 6 líneas verticales y 5 horizontales de la tabla 5×4."""
    warped, _ = _warp_math(gray, corners)
    binary = _binarize(warped)
    values: list[float] = []
    for x in np.linspace(0, MATH_GRID_W - 1, 6):
        x = int(round(x))
        strip = binary[:, max(0, x - 24):min(MATH_GRID_W, x + 25)]
        values.append(float(np.max(np.mean(strip > 0, axis=0))))
    for y in np.linspace(0, MATH_GRID_H - 1, 5):
        y = int(round(y))
        strip = binary[max(0, y - 24):min(MATH_GRID_H, y + 25), :]
        values.append(float(np.max(np.mean(strip > 0, axis=1))))
    return float(np.mean(values))


def _math_orientation_score(warped: np.ndarray) -> float:
    """Prefiere encabezados arriba y casilleros a la derecha de cada letra."""
    grid = warped[:MATH_GRID_H]
    cell_w, cell_h = MATH_GRID_W // 5, MATH_GRID_H // 4
    header_contrast = 0.0
    side_contrast = 0.0
    binary = _binarize(grid)
    for row in range(4):
        for col in range(5):
            cell = grid[
                row * cell_h:(row + 1) * cell_h,
                col * cell_w:(col + 1) * cell_w,
            ]
            header = np.mean(cell[int(cell_h * .04):int(cell_h * .20)])
            footer = np.mean(cell[int(cell_h * .80):int(cell_h * .96)])
            header_contrast += float(footer - header) / 255

            binary_cell = binary[
                row * cell_h:(row + 1) * cell_h,
                col * cell_w:(col + 1) * cell_w,
            ]
            left = np.mean(binary_cell[int(cell_h * .27):int(cell_h * .94),
                                       int(cell_w * .08):int(cell_w * .34)] > 0)
            right = np.mean(binary_cell[int(cell_h * .27):int(cell_h * .94),
                                        int(cell_w * .66):int(cell_w * .92)] > 0)
            side_contrast += float(left - right)
    return header_contrast + side_contrast * 2.0


def _find_math_grid(gray: np.ndarray) -> _GridDetection | None:
    """Encuentra la tabla principal 5×4 del formulario de Matemática."""
    binary = _binarize(gray)
    height, width = binary.shape
    horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (max(25, width // 28), 1))
    vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, max(25, height // 34)))
    line_mask = cv2.bitwise_or(
        cv2.morphologyEx(binary, cv2.MORPH_OPEN, horizontal_kernel),
        cv2.morphologyEx(binary, cv2.MORPH_OPEN, vertical_kernel),
    )

    image_area = float(binary.size)
    candidates: list[tuple[float, np.ndarray]] = []
    for source in (line_mask, binary):
        contours, _ = cv2.findContours(source, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        for contour in contours:
            area_fraction = cv2.contourArea(contour) / image_area
            if not .055 <= area_fraction <= .82:
                continue
            quad = _quad_from_contour(contour)
            if quad is None:
                continue
            corners = _sort_corners(quad)
            top = np.linalg.norm(corners[1] - corners[0])
            left = np.linalg.norm(corners[3] - corners[0])
            ratio = top / max(left, 1.0)
            if not .62 <= ratio <= 1.38:
                continue
            candidates.append((area_fraction, corners))

    best: _GridDetection | None = None
    seen: set[tuple[int, ...]] = set()
    for _, base_corners in sorted(candidates, key=lambda candidate: candidate[0], reverse=True):
        signature = tuple(np.round(base_corners / 12).astype(int).ravel())
        if signature in seen:
            continue
        seen.add(signature)
        for rotation in range(4):
            corners = np.roll(base_corners, -rotation, axis=0)
            line_score = _math_grid_line_score(gray, corners)
            if line_score < .38:
                continue
            warped, _ = _warp_math(gray, corners)
            orientation = _math_orientation_score(warped)
            score = line_score + max(-.2, min(.2, orientation / 25))
            if best is None or score > best.score:
                best = _GridDetection(corners.copy(), score, "math_grid")
    return best


def _warp_math_teacher(gray: np.ndarray,
                       corners: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    destination = np.array(
        [[0, 0], [MATH_TEACHER_W - 1, 0],
         [MATH_TEACHER_W - 1, MATH_TEACHER_H - 1], [0, MATH_TEACHER_H - 1]],
        dtype=np.float32,
    )
    matrix = cv2.getPerspectiveTransform(corners, destination)
    return cv2.warpPerspective(
        gray, matrix, (MATH_TEACHER_W, MATH_TEACHER_H), borderValue=255,
    ), matrix


def _math_teacher_line_score(gray: np.ndarray, corners: np.ndarray) -> float:
    warped, _ = _warp_math_teacher(gray, corners)
    binary = _binarize(warped)
    values = []
    for x in np.linspace(0, MATH_TEACHER_W - 1, 5):
        x = int(round(x))
        strip = binary[:, max(0, x - 20):min(MATH_TEACHER_W, x + 21)]
        values.append(float(np.max(np.mean(strip > 0, axis=0))))
    for y in (0, MATH_TEACHER_H - 1):
        strip = binary[max(0, y - 20):min(MATH_TEACHER_H, y + 21), :]
        values.append(float(np.max(np.mean(strip > 0, axis=1))))
    return float(np.mean(values))


def _find_math_teacher_grid(gray: np.ndarray) -> _GridDetection | None:
    """Detecta por separado la tabla horizontal de los ítems 21 a 24."""
    binary = _binarize(gray)
    height, width = binary.shape
    horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (max(25, width // 30), 1))
    vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, max(20, height // 45)))
    line_mask = cv2.bitwise_or(
        cv2.morphologyEx(binary, cv2.MORPH_OPEN, horizontal_kernel),
        cv2.morphologyEx(binary, cv2.MORPH_OPEN, vertical_kernel),
    )
    image_area = float(binary.size)
    best: _GridDetection | None = None
    for source in (line_mask, binary):
        contours, _ = cv2.findContours(source, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        for contour in contours:
            area_fraction = cv2.contourArea(contour) / image_area
            if not .015 <= area_fraction <= .32:
                continue
            quad = _quad_from_contour(contour)
            if quad is None:
                continue
            corners = _landscape_corners(quad)
            top = np.linalg.norm(corners[1] - corners[0])
            left = np.linalg.norm(corners[3] - corners[0])
            ratio = top / max(left, 1.0)
            if not 2.4 <= ratio <= 5.2:
                continue
            for rotation in (0, 2):
                oriented = np.roll(corners, -rotation, axis=0)
                line_score = _math_teacher_line_score(gray, oriented)
                warped, _ = _warp_math_teacher(gray, oriented)
                header = np.mean(warped[int(MATH_TEACHER_H * .04):int(MATH_TEACHER_H * .20)])
                footer = np.mean(warped[int(MATH_TEACHER_H * .80):int(MATH_TEACHER_H * .96)])
                score = line_score + float(footer - header) / 255
                if line_score >= .36 and (best is None or score > best.score):
                    best = _GridDetection(oriented.copy(), score, "math_teacher_grid")
    return best


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


def _checkbox_darkness_scores(gray_cell: np.ndarray, binary_cell: np.ndarray) -> list[float | None]:
    """Mide el interior del cuadrado real, incluso con lápiz muy tenue.

    Se localizan los cuatro bordes impresos en vez de asumir una coordenada X
    fija. La media de oscuridad del interior ignora el borde del casillero.
    """
    cell_h, cell_w = binary_cell.shape
    contours, _ = cv2.findContours(binary_cell, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    scores: list[float | None] = []

    for option in range(4):
        expected_y = cell_h * (.30 + option * .18)
        candidates = []
        for contour in contours:
            x, y, width, height = cv2.boundingRect(contour)
            aspect = width / max(height, 1)
            center_y = y + height / 2
            if (
                cell_w * .085 <= width <= cell_w * .14
                and cell_h * .11 <= height <= cell_h * .19
                and .68 <= aspect <= 1.38
                and cell_w * .10 <= x <= cell_w * .38
                and abs(center_y - expected_y) <= cell_h * .10
            ):
                candidates.append((cv2.contourArea(contour), x, y, width, height))

        if not candidates:
            scores.append(None)
            continue

        _, x, y, width, height = max(candidates)
        margin = .25
        x1, x2 = int(x + width * margin), int(x + width * (1 - margin))
        y1, y2 = int(y + height * margin), int(y + height * (1 - margin))
        interior = gray_cell[y1:y2, x1:x2]
        if interior.size == 0:
            scores.append(None)
        else:
            scores.append(float(np.mean(255 - interior) / 255))
    return scores


def _decide_checkbox(scores: list[float | None]) -> tuple[str, int] | None:
    """Decide por relleno interior o devuelve None para usar otro detector."""
    if sum(score is not None for score in scores) < 3:
        return None

    numeric = [score if score is not None else 0.0 for score in scores]
    order = np.argsort(numeric)[::-1]
    first, second, third = (float(numeric[index]) for index in order[:3])
    present = [float(score) for score in scores if score is not None]
    baseline = float(np.median(present))

    # Dos interiores claramente más oscuros representan una respuesta múltiple.
    if first - second < .10 and second - third >= .10:
        return "", 39

    if first - baseline >= .10 and first - second >= .085:
        confidence = int(np.clip(58 + (first - second) * 180, 58, 99))
        return LETTERS[int(order[0])], confidence
    return None


def _letter_circle_scores(binary_cell: np.ndarray) -> list[float]:
    """Detecta círculos o trazos hechos sobre la letra, fuera del cuadrado."""
    cell_h, cell_w = binary_cell.shape
    scores = []
    for option in range(4):
        center_y = cell_h * (.30 + option * .18)
        scores.append(_region_density(
            binary_cell,
            cell_w * .01, center_y - cell_h * .073,
            cell_w * .19, center_y + cell_h * .073,
        ))
    return scores


def _decide_letter_circle(scores: list[float]) -> tuple[str, int] | None:
    order = np.argsort(scores)[::-1]
    first, second = float(scores[order[0]]), float(scores[order[1]])
    baseline = float(np.median(scores))
    if first - second >= .045 and first - baseline >= .045:
        confidence = int(np.clip(55 + (first - second) * 260, 55, 90))
        return LETTERS[int(order[0])], confidence
    return None


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


def _read_student(gray: np.ndarray, binary: np.ndarray) -> tuple[dict[int, str], dict[int, int]]:
    responses: dict[int, str] = {}
    confidence: dict[int, int] = {}
    cell_w, cell_h = GRID_W / 3, GRID_H / 3
    for row in range(3):
        for col in range(3):
            item = row * 3 + col + 1
            y1, y2 = row * GRID_H // 3, (row + 1) * GRID_H // 3
            x1, x2 = col * GRID_W // 3, (col + 1) * GRID_W // 3
            box_decision = _decide_checkbox(_checkbox_darkness_scores(
                gray[y1:y2, x1:x2], binary[y1:y2, x1:x2],
            ))
            if box_decision is not None:
                responses[item], confidence[item] = box_decision
                continue

            circle_decision = _decide_letter_circle(
                _letter_circle_scores(binary[y1:y2, x1:x2])
            )
            if circle_decision is not None:
                responses[item], confidence[item] = circle_decision
                continue

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
        if first >= .29 and first - second >= .07:
            responses[item] = LETTERS[int(order[0])]
            confidence[item] = int(np.clip(60 + (first - second) * 180, 60, 99))
        else:
            responses[item] = ""
            confidence[item] = int(np.clip((first - second) * 100, 0, 39))
    return responses, confidence


def _math_checkbox_scores(gray_cell: np.ndarray, binary_cell: np.ndarray,
                          y_start: float = .39,
                          y_step: float = .155) -> list[float | None]:
    """Localiza los cuatro casilleros del nuevo formulario de Matemática."""
    cell_h, cell_w = binary_cell.shape
    contours, _ = cv2.findContours(binary_cell, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    scores: list[float | None] = []
    for option in range(4):
        expected_y = cell_h * (y_start + option * y_step)
        candidates = []
        for contour in contours:
            x, y, width, height = cv2.boundingRect(contour)
            aspect = width / max(height, 1)
            center_y = y + height / 2
            if (
                cell_w * .055 <= width <= cell_w * .16
                and cell_h * .065 <= height <= cell_h * .15
                and .62 <= aspect <= 1.45
                and cell_w * .43 <= x <= cell_w * .72
                and abs(center_y - expected_y) <= cell_h * .09
            ):
                candidates.append((cv2.contourArea(contour), x, y, width, height))
        if not candidates:
            scores.append(None)
            continue
        _, x, y, width, height = max(candidates)
        margin = .24
        interior = gray_cell[
            int(y + height * margin):int(y + height * (1 - margin)),
            int(x + width * margin):int(x + width * (1 - margin)),
        ]
        scores.append(
            None if interior.size == 0
            else float(np.mean(255 - interior) / 255)
        )
    return scores


def _math_circle_scores(binary_cell: np.ndarray, y_start: float = .39,
                        y_step: float = .155) -> list[float]:
    cell_h, cell_w = binary_cell.shape
    return [
        _region_density(
            binary_cell,
            cell_w * .12, cell_h * (y_start + option * y_step - .065),
            cell_w * .47, cell_h * (y_start + option * y_step + .065),
        )
        for option in range(4)
    ]


def _decide_math_checkbox(scores: list[float | None]) -> tuple[str, int] | None:
    """Tolera el lápiz tenue observado en los ítems inferiores de Matemática."""
    missing = [index for index, score in enumerate(scores) if score is None]
    present = [float(score) for score in scores if score is not None]
    # Una cruz o un relleno sólido puede unir el casillero con el trazo y hacer
    # que deje de reconocerse como cuadrado. Si los otros tres casilleros sí
    # aparecen y tienen oscuridad pareja, el ausente es la marca realizada.
    if (
        len(missing) == 1 and len(present) == 3
        and min(present) >= .10 and max(present) - min(present) <= .12
    ):
        return LETTERS[missing[0]], 68
    if sum(score is not None for score in scores) < 3:
        return None
    numeric = [score if score is not None else 0.0 for score in scores]
    order = np.argsort(numeric)[::-1]
    first, second, third = (float(numeric[index]) for index in order[:3])
    baseline = float(np.median(present))
    if first - second < .055 and second - third >= .065:
        return "", 39
    elevation = first - baseline
    contrast = first - second
    if elevation >= .052 and contrast >= .040:
        confidence = int(np.clip(50 + contrast * 220 + elevation * 90, 50, 99))
        return LETTERS[int(order[0])], confidence
    return None


def _math_fallback_scores(binary_cell: np.ndarray, y_start: float = .39,
                          y_step: float = .155) -> list[float]:
    cell_h, cell_w = binary_cell.shape
    scores = []
    for option in range(4):
        center_y = cell_h * (y_start + option * y_step)
        band = _region_density(
            binary_cell,
            cell_w * .12, center_y - cell_h * .05,
            cell_w * .72, center_y + cell_h * .05,
        )
        box_center = _region_density(
            binary_cell,
            cell_w * .49, center_y - cell_h * .035,
            cell_w * .64, center_y + cell_h * .035,
        )
        scores.append(band + box_center)
    return scores


def _read_math_cell(gray_cell: np.ndarray,
                    binary_cell: np.ndarray, y_start: float = .39,
                    y_step: float = .155) -> tuple[str, int]:
    checkbox = _decide_math_checkbox(
        _math_checkbox_scores(gray_cell, binary_cell, y_start, y_step)
    )
    if checkbox is not None:
        return checkbox
    circle_scores = _math_circle_scores(binary_cell, y_start, y_step)
    order = np.argsort(circle_scores)[::-1]
    first, second = float(circle_scores[order[0]]), float(circle_scores[order[1]])
    circle = (
        _decide_letter_circle(circle_scores)
        if first - second >= .060 else None
    )
    if circle is not None:
        return circle
    return _decide(_math_fallback_scores(binary_cell, y_start, y_step))


def _read_math_main(gray: np.ndarray,
                    binary: np.ndarray) -> tuple[dict[int, str], dict[int, int]]:
    responses: dict[int, str] = {}
    confidence: dict[int, int] = {}
    for row in range(4):
        for col in range(5):
            item = row * 5 + col + 1
            y1, y2 = row * MATH_GRID_H // 4, (row + 1) * MATH_GRID_H // 4
            x1, x2 = col * MATH_GRID_W // 5, (col + 1) * MATH_GRID_W // 5
            responses[item], confidence[item] = _read_math_cell(
                gray[y1:y2, x1:x2], binary[y1:y2, x1:x2],
                y_start=.32, y_step=.18,
            )
    return responses, confidence


def _read_math_teacher(gray: np.ndarray,
                       binary: np.ndarray) -> tuple[dict[int, str], dict[int, int]]:
    responses: dict[int, str] = {}
    confidence: dict[int, int] = {}
    for col in range(4):
        x1, x2 = col * MATH_TEACHER_W // 4, (col + 1) * MATH_TEACHER_W // 4
        item = 21 + col
        responses[item], confidence[item] = _read_math_cell(
            gray[:, x1:x2], binary[:, x1:x2], y_start=.39, y_step=.17,
        )
    return responses, confidence


def _procesar_matematica(image: np.ndarray) -> dict:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    detection = _find_math_grid(gray)
    empty_responses = {str(item): "" for item in range(1, 25)}
    empty_confidence = {str(item): 0 for item in range(1, 25)}
    if detection is None:
        return {
            "respuestas": empty_responses,
            "confianza": empty_confidence,
            "items_dudosos": list(range(1, 25)),
            "used_warp": False,
            "detection_method": "not_found",
            "detection_score": 0,
        }

    warped, _ = _warp_math(gray, detection.corners)
    binary = _binarize(warped)
    responses, confidence = _read_math_main(
        warped, binary,
    )
    teacher_detection = _find_math_teacher_grid(gray)
    if teacher_detection is not None:
        teacher_warped, _ = _warp_math_teacher(gray, teacher_detection.corners)
        teacher_responses, teacher_confidence = _read_math_teacher(
            teacher_warped, _binarize(teacher_warped),
        )
    else:
        teacher_responses = {item: "" for item in range(21, 25)}
        teacher_confidence = {item: 0 for item in range(21, 25)}
    responses.update(teacher_responses)
    confidence.update(teacher_confidence)
    doubtful = [
        item for item in range(1, 25)
        if not responses[item] or confidence[item] < CONF_LOW
    ]

    image_h, image_w = gray.shape
    teacher_box = (
        tuple(int(value) for value in cv2.boundingRect(teacher_detection.corners))
        if teacher_detection is not None else None
    )
    return {
        "respuestas": {str(key): value for key, value in responses.items()},
        "confianza": {str(key): value for key, value in confidence.items()},
        "items_dudosos": doubtful,
        "used_warp": True,
        "detection_method": detection.method,
        "detection_score": round(min(1.0, detection.score), 3),
        "student_box": tuple(int(value) for value in cv2.boundingRect(detection.corners)),
        "doc_box": teacher_box,
        "image_size": (image_w, image_h),
    }


def procesar_imagen(imagen_bytes: bytes, tipo_examen: str = "lengua") -> dict:
    """Procesa una foto y devuelve respuestas, confianza y diagnóstico OMR."""
    image = _decode_image(imagen_bytes)
    if tipo_examen == "matematica":
        return _procesar_matematica(image)
    if tipo_examen not in {"lengua", "contexto"}:
        raise ValueError("El tipo de examen no es válido.")
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

    responses, confidence = _read_student(warped[:GRID_H], binary)
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
