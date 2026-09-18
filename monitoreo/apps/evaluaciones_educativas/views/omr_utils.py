"""Lectura OMR de la grilla de respuestas de los exámenes 2026.

El detector usa la geometría impresa de cada grilla, no posiciones relativas a
la foto. Admite Matemática, Lengua (incluida su rúbrica docente) y las dos hojas
del examen de Contexto.
"""

from __future__ import annotations

import io
from dataclasses import dataclass

import cv2
import numpy as np

from apps.evaluaciones_educativas.models.omr_lector import ExamenLengua, ExamenMatematica
from apps.evaluaciones_educativas.services.omr_catalogo import (
    ITEMS_MULTIPLES_CONTEXTO,
    OPCIONES_POR_ITEM_CONTEXTO,
)


# Mantiene el detector sincronizado con las respuestas permitidas por el modelo.
LETTERS = tuple(value for value, _ in ExamenMatematica.OPCIONES_RESPUESTA if value)
CONF_LOW = 45
GRID_W, GRID_H = 1200, 900
EXTENDED_H = 1450
MATH_GRID_W, MATH_GRID_H = 1500, 1200
MATH_TEACHER_W, MATH_TEACHER_H = 1200, 360
LANG_TEACHER_W, LANG_TEACHER_H = 1400, 360
MATH_HEADER_H = 420
CONTEXT_W, CONTEXT_H = 1200, 1700
CONTEXT_Y_TEMPLATES = {
    1: (194, 228, 260, 293, 325, 358, 440, 474, 556, 589, 623,
        705, 739, 772, 806, 840, 873, 979, 1012, 1046, 1079, 1112,
        1194, 1227, 1260, 1340, 1374, 1407, 1440, 1520, 1552, 1585,
        1619, 1652, 1686),
    2: (68, 104, 140, 256, 292, 328, 363, 398, 434, 520, 556, 592,
        680, 716, 750, 838, 874, 910, 996, 1032, 1068, 1106, 1141,
        1230, 1266, 1301, 1336, 1422, 1458, 1494, 1528, 1613, 1648, 1683),
}
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


def _warp_math_header(gray: np.ndarray, corners: np.ndarray) -> np.ndarray:
    """Rectifica el sector ubicado encima de la grilla principal."""
    destination = np.array(
        [[0, MATH_HEADER_H], [MATH_GRID_W - 1, MATH_HEADER_H],
         [MATH_GRID_W - 1, MATH_HEADER_H + MATH_GRID_H - 1],
         [0, MATH_HEADER_H + MATH_GRID_H - 1]],
        dtype=np.float32,
    )
    matrix = cv2.getPerspectiveTransform(corners, destination)
    return cv2.warpPerspective(
        gray, matrix, (MATH_GRID_W, MATH_HEADER_H), borderValue=255,
    )


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


def _warp_language_teacher(gray: np.ndarray,
                           corners: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    destination = np.array(
        [[0, 0], [LANG_TEACHER_W - 1, 0],
         [LANG_TEACHER_W - 1, LANG_TEACHER_H - 1], [0, LANG_TEACHER_H - 1]],
        dtype=np.float32,
    )
    matrix = cv2.getPerspectiveTransform(corners, destination)
    return cv2.warpPerspective(
        gray, matrix, (LANG_TEACHER_W, LANG_TEACHER_H), borderValue=255,
    ), matrix


def _language_teacher_line_score(gray: np.ndarray, corners: np.ndarray) -> float:
    warped, _ = _warp_language_teacher(gray, corners)
    binary = _binarize(warped)
    values = []
    for x in np.linspace(0, LANG_TEACHER_W - 1, 8):
        x = int(round(x))
        strip = binary[:, max(0, x - 16):min(LANG_TEACHER_W, x + 17)]
        values.append(float(np.max(np.mean(strip > 0, axis=0))))
    for y in (0, LANG_TEACHER_H - 1):
        strip = binary[max(0, y - 18):min(LANG_TEACHER_H, y + 19), :]
        values.append(float(np.max(np.mean(strip > 0, axis=1))))
    return float(np.mean(values))


def _find_language_teacher_grid(
    gray: np.ndarray, main_corners: np.ndarray,
) -> _GridDetection | None:
    """Detecta la tabla docente de siete columnas de Lengua."""
    binary = _binarize(gray)
    height, width = binary.shape
    horizontal_kernel = cv2.getStructuringElement(
        cv2.MORPH_RECT, (max(25, width // 30), 1),
    )
    vertical_kernel = cv2.getStructuringElement(
        cv2.MORPH_RECT, (1, max(20, height // 45)),
    )
    line_mask = cv2.bitwise_or(
        cv2.morphologyEx(binary, cv2.MORPH_OPEN, horizontal_kernel),
        cv2.morphologyEx(binary, cv2.MORPH_OPEN, vertical_kernel),
    )
    image_area = float(binary.size)
    canonical_main = np.array(
        [[0, 0], [MATH_GRID_W - 1, 0],
         [MATH_GRID_W - 1, MATH_GRID_H - 1], [0, MATH_GRID_H - 1]],
        dtype=np.float32,
    )
    main_projection = cv2.getPerspectiveTransform(
        main_corners.astype(np.float32), canonical_main,
    )
    best: _GridDetection | None = None
    for source in (line_mask, binary):
        contours, _ = cv2.findContours(source, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        for contour in contours:
            area_fraction = cv2.contourArea(contour) / image_area
            if not .015 <= area_fraction <= .38:
                continue
            quad = _quad_from_contour(contour)
            if quad is None:
                continue
            corners = _landscape_corners(quad)
            top = np.linalg.norm(corners[1] - corners[0])
            left = np.linalg.norm(corners[3] - corners[0])
            ratio = top / max(left, 1.0)
            if not 2.7 <= ratio <= 5.8:
                continue
            # La tabla docente está inmediatamente debajo de la grilla 5×4.
            # Proyectarla al sistema de la grilla principal evita confundirla
            # con tablas internas, encabezados o bordes de la hoja inclinada.
            projected = cv2.perspectiveTransform(
                corners.reshape(1, -1, 2).astype(np.float32),
                main_projection,
            )[0]
            projected_center = np.mean(projected, axis=0)
            projected_width = float(
                max(np.linalg.norm(projected[1] - projected[0]),
                    np.linalg.norm(projected[2] - projected[3]))
            )
            if not (
                -.30 * MATH_GRID_W <= projected_center[0] <= 1.30 * MATH_GRID_W
                and .86 * MATH_GRID_H <= projected_center[1] <= 2.20 * MATH_GRID_H
                and projected_width >= .68 * MATH_GRID_W
            ):
                continue
            for rotation in (0, 2):
                oriented = np.roll(corners, -rotation, axis=0)
                line_score = _language_teacher_line_score(gray, oriented)
                warped, _ = _warp_language_teacher(gray, oriented)
                header = np.mean(
                    warped[int(LANG_TEACHER_H * .04):int(LANG_TEACHER_H * .20)]
                )
                footer = np.mean(
                    warped[int(LANG_TEACHER_H * .80):int(LANG_TEACHER_H * .96)]
                )
                score = line_score + float(footer - header) / 255
                if line_score >= .40 and (best is None or score > best.score):
                    best = _GridDetection(oriented.copy(), score, "language_teacher_grid")
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
                          y_step: float = .155,
                          x_min: float = .43,
                          x_max: float = .72) -> list[float | None]:
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
                and cell_w * x_min <= x <= cell_w * x_max
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


def _read_language_teacher(gray: np.ndarray,
                           binary: np.ndarray) -> tuple[dict[int, str], dict[int, int]]:
    responses: dict[int, str] = {}
    confidence: dict[int, int] = {}
    for col in range(7):
        x1, x2 = col * LANG_TEACHER_W // 7, (col + 1) * LANG_TEACHER_W // 7
        item = 21 + col
        gray_cell = gray[:, x1:x2]
        binary_cell = binary[:, x1:x2]
        checkbox_scores = _math_checkbox_scores(
            gray_cell, binary_cell, y_start=.39, y_step=.17,
            x_min=.54, x_max=.78,
        )
        checkbox = _decide_math_checkbox(checkbox_scores)
        if checkbox is not None:
            responses[item], confidence[item] = checkbox
        elif sum(score is not None for score in checkbox_scores) >= 3:
            # En Lengua esta tabla siempre usa cuadrados. No recurrir al texto
            # impreso como respaldo: en una hoja vacía las letras A-D pueden
            # parecer marcas bajo sombras fuertes o desenfoque.
            responses[item], confidence[item] = "", 0
        else:
            responses[item], confidence[item] = _read_math_cell(
                gray_cell, binary_cell, y_start=.39, y_step=.17,
            )
    return responses, confidence


def _normalize_model_glyph(glyph: np.ndarray, size: int = 64) -> np.ndarray:
    points = cv2.findNonZero(glyph)
    normalized = np.zeros((size, size), dtype=np.uint8)
    if points is None:
        return normalized
    x, y, width, height = cv2.boundingRect(points)
    cropped = glyph[y:y + height, x:x + width]
    scale = min((size - 10) / max(width, 1), (size - 10) / max(height, 1))
    resized = cv2.resize(
        cropped,
        (max(1, round(width * scale)), max(1, round(height * scale))),
        interpolation=cv2.INTER_AREA,
    )
    offset_x = (size - resized.shape[1]) // 2
    offset_y = (size - resized.shape[0]) // 2
    normalized[
        offset_y:offset_y + resized.shape[0],
        offset_x:offset_x + resized.shape[1],
    ] = resized
    return cv2.dilate(normalized, np.ones((2, 2), np.uint8))


def _model_template_scores(
    glyph: np.ndarray, allowed_letters: tuple[str, ...] = LETTERS,
) -> dict[str, float]:
    normalized = _normalize_model_glyph(glyph)
    scores = {letter: 0.0 for letter in allowed_letters}
    fonts = (
        cv2.FONT_HERSHEY_SIMPLEX,
        cv2.FONT_HERSHEY_DUPLEX,
        cv2.FONT_HERSHEY_COMPLEX,
        cv2.FONT_HERSHEY_TRIPLEX,
    )
    for letter in allowed_letters:
        for font in fonts:
            for thickness in (2, 3, 4):
                template = np.zeros((100, 100), dtype=np.uint8)
                cv2.putText(
                    template, letter, (12, 82), font, 2.5, 255,
                    thickness, cv2.LINE_AA,
                )
                candidate = _normalize_model_glyph(template)
                union = np.count_nonzero((normalized > 0) | (candidate > 0))
                if union:
                    intersection = np.count_nonzero(
                        (normalized > 0) & (candidate > 0)
                    )
                    scores[letter] = max(scores[letter], intersection / union)
    return scores


def _classify_model_glyph(
    glyph: np.ndarray, allowed_letters: tuple[str, ...] = LETTERS,
) -> tuple[str, int]:
    closed = cv2.morphologyEx(
        glyph, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8), iterations=1,
    )
    contours, hierarchy = cv2.findContours(
        closed, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE,
    )
    glyph_area = max(1, glyph.size)
    holes = 0
    if hierarchy is not None:
        for index, contour in enumerate(contours):
            if hierarchy[0][index][3] >= 0 and cv2.contourArea(contour) >= glyph_area * .012:
                holes += 1
    # La B manuscrita del formulario conserva dos contraformas incluso con
    # trazos tenues, una señal más estable que comparar tipografías.
    if holes >= 2 and "B" in allowed_letters:
        return "B", 92
    # En Lengua solo se imprimen modelos A/B. Una contraforma triangular es
    # una señal muy fuerte de A; si una B pierde un lóbulo, la clave de sus
    # respuestas todavía puede corregir esta estimación más adelante.
    if set(allowed_letters) == {"A", "B"} and holes == 1:
        return "A", 85

    scores = _model_template_scores(closed, allowed_letters)
    # En tinta fina, los dos lóbulos de la B pueden quedar abiertos y parecer
    # una D. Se compensa esa diferencia conocida sin forzar lecturas dudosas.
    if "B" in scores and len(allowed_letters) > 2:
        scores["B"] += .065
    ordered = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    (letter, first), (_, second) = ordered[:2]
    minimum_score = .20 if len(allowed_letters) == 2 else .25
    minimum_margin = .010 if len(allowed_letters) == 2 else .018
    if first < minimum_score or first - second < minimum_margin:
        return "", int(np.clip(first * 100, 0, 44))
    return letter, int(np.clip(50 + (first - second) * 240, 50, 88))


def _read_math_model(
    gray: np.ndarray, corners: np.ndarray,
    allowed_letters: tuple[str, ...] = LETTERS,
) -> tuple[str, int]:
    """Lee el carácter manuscrito del recuadro de modelo sobre la grilla."""
    header = _warp_math_header(gray, corners)
    binary = _binarize(header)
    contours, _ = cv2.findContours(binary, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    candidates: list[tuple[float, tuple[int, int, int, int]]] = []
    for contour in contours:
        x, y, width, height = cv2.boundingRect(contour)
        aspect = width / max(height, 1)
        if not (
            MATH_GRID_W * .055 <= width <= MATH_GRID_W * .30
            and MATH_HEADER_H * .07 <= height <= MATH_HEADER_H * .42
            and 1.8 <= aspect <= 6.5
            and MATH_GRID_W * .15 <= x <= MATH_GRID_W * .62
        ):
            continue
        rectangularity = cv2.contourArea(contour) / max(width * height, 1)
        score = (
            rectangularity
            - abs(aspect - 3.2) * .035
            - abs((x + width / 2) / MATH_GRID_W - .37) * .25
            - abs((y + height / 2) / MATH_HEADER_H - .56) * .20
        )
        candidates.append((score, (x, y, width, height)))
    if not candidates:
        return "", 0

    _, (x, y, width, height) = max(candidates, key=lambda item: item[0])
    margin_x = max(4, round(width * .07))
    margin_y = max(4, round(height * .13))
    inner = binary[
        y + margin_y:y + height - margin_y,
        x + margin_x:x + width - margin_x,
    ]
    if inner.size == 0:
        return "", 0

    horizontal_lines = cv2.morphologyEx(
        inner,
        cv2.MORPH_OPEN,
        np.ones((1, max(15, inner.shape[1] // 3)), np.uint8),
    )
    inner = cv2.bitwise_and(inner, cv2.bitwise_not(horizontal_lines))

    count, _, stats, _ = cv2.connectedComponentsWithStats(inner, 8)
    components: list[tuple[int, int, int, int]] = []
    for label in range(1, count):
        component_x, component_y, component_w, component_h, area = stats[label]
        if (
            area >= inner.size * .008
            and component_h >= inner.shape[0] * .30
            and component_w >= 3
        ):
            components.append(
                (component_x, component_y, component_w, component_h)
            )
    if not components:
        return "", 0

    # Si hubo una corrección (por ejemplo, A tachada y luego B), se considera
    # el último carácter legible escrito de izquierda a derecha.
    component_x, component_y, component_w, component_h = max(
        components, key=lambda item: item[0] + item[2],
    )
    padding = 3
    # Conserva trazos cercanos del mismo carácter: con desenfoque, el asta y
    # los lóbulos de una B pueden quedar como componentes separados.
    left_padding = max(padding, round(component_h * .35))
    x1, y1 = max(0, component_x - left_padding), max(0, component_y - padding)
    x2 = min(inner.shape[1], component_x + component_w + padding)
    y2 = min(inner.shape[0], component_y + component_h + padding)
    glyph = inner[y1:y2, x1:x2].copy()
    return _classify_model_glyph(glyph, allowed_letters)


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
            "modelo_examen": "",
            "modelo_confianza": 0,
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
    model, model_confidence = _read_math_model(gray, detection.corners)
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
        "modelo_examen": model,
        "modelo_confianza": model_confidence,
        "student_box": tuple(int(value) for value in cv2.boundingRect(detection.corners)),
        "doc_box": teacher_box,
        "image_size": (image_w, image_h),
    }


def _infer_language_model(responses: dict[int, str]) -> tuple[str, int]:
    answered = {
        item: response for item, response in responses.items()
        if item <= 20 and response in LETTERS
    }
    if len(answered) < 12:
        return "", 0
    ranked = []
    for model, answer_key in ExamenLengua.RESPUESTAS_CORRECTAS_LENGUA.items():
        matches = sum(answered[item] == answer_key[item] for item in answered)
        ranked.append((matches / len(answered), model))
    ranked.sort(reverse=True)
    (first, model), (second, _) = ranked[:2]
    if first < .75 or first - second < .25:
        return "", 0
    return model, int(np.clip(55 + first * 40, 55, 95))


def _procesar_lengua(image: np.ndarray) -> dict:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    detection = _find_math_grid(gray)
    empty_responses = {str(item): "" for item in range(1, 28)}
    empty_confidence = {str(item): 0 for item in range(1, 28)}
    if detection is None:
        return {
            "respuestas": empty_responses,
            "confianza": empty_confidence,
            "items_dudosos": list(range(1, 28)),
            "used_warp": False,
            "detection_method": "not_found",
            "detection_score": 0,
            "modelo_examen": "",
            "modelo_confianza": 0,
        }

    warped, _ = _warp_math(gray, detection.corners)
    responses, confidence = _read_math_main(warped, _binarize(warped))
    teacher_detection = _find_language_teacher_grid(gray, detection.corners)
    if teacher_detection is not None:
        teacher_warped, _ = _warp_language_teacher(
            gray, teacher_detection.corners,
        )
        teacher_light = cv2.GaussianBlur(
            teacher_warped, (0, 0), sigmaX=28, sigmaY=28,
        )
        teacher_warped = cv2.divide(
            teacher_warped, np.maximum(teacher_light, 1), scale=235,
        )
        teacher_responses, teacher_confidence = _read_language_teacher(
            teacher_warped, _binarize(teacher_warped),
        )
    else:
        teacher_responses = {item: "" for item in range(21, 28)}
        teacher_confidence = {item: 0 for item in range(21, 28)}
    responses.update(teacher_responses)
    confidence.update(teacher_confidence)

    model, model_confidence = _read_math_model(
        gray, detection.corners, ("A", "B"),
    )
    inferred_model, inferred_confidence = _infer_language_model(responses)
    if inferred_model and (
        not model or inferred_confidence > model_confidence
    ):
        model, model_confidence = inferred_model, inferred_confidence

    doubtful = [
        item for item in range(1, 28)
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
        "modelo_examen": model,
        "modelo_confianza": model_confidence,
        "student_box": tuple(int(value) for value in cv2.boundingRect(detection.corners)),
        "doc_box": teacher_box,
        "image_size": (image_w, image_h),
    }


def _find_context_frame(gray: np.ndarray) -> _GridDetection | None:
    """Localiza el marco vertical del cuestionario o, como respaldo, la hoja."""
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blurred, 45, 140)
    edges = cv2.morphologyEx(
        edges, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8), iterations=2,
    )
    contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    image_area = float(gray.size)
    best: _GridDetection | None = None
    for contour in contours:
        area_fraction = cv2.contourArea(contour) / image_area
        if not .20 <= area_fraction <= .98:
            continue
        quad = _quad_from_contour(contour)
        if quad is None:
            continue
        corners = _sort_corners(quad)
        width = max(
            np.linalg.norm(corners[1] - corners[0]),
            np.linalg.norm(corners[2] - corners[3]),
        )
        height = max(
            np.linalg.norm(corners[3] - corners[0]),
            np.linalg.norm(corners[2] - corners[1]),
        )
        ratio = width / max(height, 1)
        if not .48 <= ratio <= .88:
            continue
        score = area_fraction - abs(ratio - .68) * .12
        if best is None or score > best.score:
            best = _GridDetection(corners, score, "context_frame")
    return best


def _warp_context(gray: np.ndarray, corners: np.ndarray) -> np.ndarray:
    destination = np.array(
        [[0, 0], [CONTEXT_W - 1, 0],
         [CONTEXT_W - 1, CONTEXT_H - 1], [0, CONTEXT_H - 1]],
        dtype=np.float32,
    )
    matrix = cv2.getPerspectiveTransform(corners, destination)
    return cv2.warpPerspective(
        gray, matrix, (CONTEXT_W, CONTEXT_H), borderValue=255,
    )


def _context_checkboxes(gray: np.ndarray) -> list[tuple[float, float, float, int, int, int, int]]:
    """Devuelve la columna de casilleros incluso con perspectiva y sombras."""
    image_h, image_w = gray.shape
    # Dividir por una estimación suave de la iluminación quita sombras amplias
    # sin borrar ni los bordes finos ni los casilleros pintados.
    background_light = cv2.GaussianBlur(gray, (0, 0), sigmaX=35, sigmaY=35)
    normalized = cv2.divide(gray, np.maximum(background_light, 1), scale=235)
    binary = _binarize(normalized)
    candidates: list[tuple[float, float, float, int, int, int, int]] = []
    contours, _ = cv2.findContours(binary, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    for contour in contours:
        x, y, width, height = cv2.boundingRect(contour)
        aspect = width / max(height, 1)
        if not (
            image_w * .006 <= width <= image_w * .038
            and image_h * .0045 <= height <= image_h * .031
            and .60 <= aspect <= 1.50
            and x <= image_w * .32
        ):
            continue
        area = cv2.contourArea(contour)
        quad = _quad_from_contour(contour)
        if quad is None or area / max(width * height, 1) < .65:
            continue
        center_x, center_y = x + width / 2, y + height / 2
        if any(
            abs(center_x - current[0]) < max(width, current[5]) * .55
            and abs(center_y - current[1]) < max(height, current[6]) * .55
            for current in candidates
        ):
            continue
        margin = .24
        interior = normalized[
            round(y + height * margin):round(y + height * (1 - margin)),
            round(x + width * margin):round(x + width * (1 - margin)),
        ]
        left = normalized[
            round(y + height * .15):round(y + height * .85),
            max(0, round(x - width * 1.35)):max(1, round(x - width * .30)),
        ]
        right = normalized[
            round(y + height * .15):round(y + height * .85),
            min(image_w - 1, round(x + width * 1.30)):
            min(image_w, round(x + width * 2.15)),
        ]
        surroundings = [region.ravel() for region in (left, right) if region.size]
        darkness = (
            float((np.median(np.concatenate(surroundings)) - np.mean(interior)) / 255)
            if interior.size and surroundings else 0.0
        )
        candidates.append((center_x, center_y, darkness, x, y, width, height))
    if not candidates:
        return []

    # La columna puede quedar diagonal cuando la hoja ocupa toda la foto y no
    # hay marco suficiente para rectificarla. Se busca x = pendiente*y+corte
    # en lugar de exigir una X constante. Las letras y números no sostienen
    # una misma recta a lo largo de toda la hoja.
    tolerance = max(12.0, image_w * .012)
    plausible_lines: list[tuple[float, float]] = [(0.0, box[0]) for box in candidates]
    for first_index, first in enumerate(candidates):
        for second in candidates[first_index + 1:]:
            delta_y = second[1] - first[1]
            if abs(delta_y) < image_h * .22:
                continue
            slope = (second[0] - first[0]) / delta_y
            if abs(slope) <= .40:
                plausible_lines.append((slope, first[0] - slope * first[1]))

    def line_score(line: tuple[float, float]) -> tuple[int, float]:
        slope, intercept = line
        matches = [
            box for box in candidates
            if abs(box[0] - (slope * box[1] + intercept)) <= tolerance
        ]
        coverage = (
            (max(box[1] for box in matches) - min(box[1] for box in matches)) / image_h
            if len(matches) > 1 else 0.0
        )
        return len(matches), coverage

    slope, intercept = max(plausible_lines, key=line_score)
    column = [
        box for box in candidates
        if abs(box[0] - (slope * box[1] + intercept)) <= tolerance
    ]
    return sorted(column, key=lambda box: (box[1], box[0]))


def _fit_context_projection(template_y: np.ndarray, observed_y: np.ndarray) -> np.ndarray:
    """Ajusta una proyección vertical que contempla la perspectiva de la foto."""
    matrix = np.column_stack((template_y, np.ones(len(template_y)), -template_y * observed_y))
    return np.linalg.lstsq(matrix, observed_y, rcond=None)[0]


def _project_context_y(projection: np.ndarray, template_y: np.ndarray) -> np.ndarray:
    denominator = projection[2] * template_y + 1
    if np.any(np.abs(denominator) < .08):
        return np.full_like(template_y, np.nan, dtype=float)
    return (projection[0] * template_y + projection[1]) / denominator


def _match_context_template(
    boxes: list[tuple], page: int, canonical: bool = False,
) -> tuple[float, list[tuple | None], np.ndarray]:
    """Alinea la secuencia con inserciones/ausencias y perspectiva vertical."""
    template_y = np.asarray(CONTEXT_Y_TEMPLATES[page], dtype=float)
    observed_y = np.asarray([box[1] for box in boxes], dtype=float)
    template_count, observed_count = len(template_y), len(observed_y)
    minimum_boxes = 14 if canonical else template_count - 4
    if observed_count < minimum_boxes or observed_count > template_count + 4:
        return float("inf"), [None] * template_count, np.full(template_count, np.nan)

    seeds: list[np.ndarray] = []
    if canonical:
        seeds.append(np.array([1.0, 0.0, 0.0]))
    difference = abs(template_count - observed_count)
    endpoint_budget = min(difference, 4)
    for leading_skip in range(endpoint_budget + 1):
        for trailing_skip in range(endpoint_budget - leading_skip + 1):
            if observed_count <= template_count:
                template_indexes = np.rint(np.linspace(
                    leading_skip,
                    template_count - 1 - trailing_skip,
                    observed_count,
                )).astype(int)
                observed_indexes = np.arange(observed_count)
            else:
                template_indexes = np.arange(template_count)
                observed_indexes = np.rint(np.linspace(
                    leading_skip,
                    observed_count - 1 - trailing_skip,
                    template_count,
                )).astype(int)
            seeds.append(_fit_context_projection(
                template_y[template_indexes], observed_y[observed_indexes],
            ))

    best_score = float("inf")
    best_aligned: list[tuple | None] = [None] * template_count
    best_prediction = np.full(template_count, np.nan)
    for seed in seeds:
        projection = seed
        path: list[tuple[int, int]] = []
        valid = True
        # Reajustar después de cada alineación evita que una casilla ausente
        # corra toda la secuencia y permite fotos tomadas en diagonal.
        for _ in range(4):
            predicted_y = _project_context_y(projection, template_y)
            if not np.all(np.isfinite(predicted_y)) or np.any(np.diff(predicted_y) <= 0):
                valid = False
                break
            row_step = max(8.0, float(np.median(np.diff(predicted_y))))
            costs = np.full((template_count + 1, observed_count + 1), np.inf)
            moves = np.zeros((template_count + 1, observed_count + 1), dtype=np.int8)
            costs[0, 0] = 0
            for template_index in range(template_count + 1):
                for observed_index in range(observed_count + 1):
                    current = costs[template_index, observed_index]
                    if not np.isfinite(current):
                        continue
                    if template_index < template_count and observed_index < observed_count:
                        match_cost = min(
                            abs(observed_y[observed_index] - predicted_y[template_index]) / row_step,
                            4.0,
                        )
                        if current + match_cost < costs[template_index + 1, observed_index + 1]:
                            costs[template_index + 1, observed_index + 1] = current + match_cost
                            moves[template_index + 1, observed_index + 1] = 1
                    if template_index < template_count and current + .9 < costs[template_index + 1, observed_index]:
                        costs[template_index + 1, observed_index] = current + .9
                        moves[template_index + 1, observed_index] = 2
                    if observed_index < observed_count and current + 1.1 < costs[template_index, observed_index + 1]:
                        costs[template_index, observed_index + 1] = current + 1.1
                        moves[template_index, observed_index + 1] = 3

            template_index, observed_index = template_count, observed_count
            path = []
            while template_index or observed_index:
                move = moves[template_index, observed_index]
                if move == 1:
                    path.append((template_index - 1, observed_index - 1))
                    template_index -= 1
                    observed_index -= 1
                elif move == 2:
                    template_index -= 1
                elif move == 3:
                    observed_index -= 1
                else:
                    valid = False
                    break
            if not valid:
                break
            path.reverse()
            if len(path) < minimum_boxes:
                valid = False
                break
            template_indexes = np.asarray([pair[0] for pair in path])
            observed_indexes = np.asarray([pair[1] for pair in path])
            projection = _fit_context_projection(
                template_y[template_indexes], observed_y[observed_indexes],
            )
        if not valid:
            continue

        predicted_y = _project_context_y(projection, template_y)
        row_step = max(8.0, float(np.median(np.diff(predicted_y))))
        errors = np.asarray([
            abs(observed_y[observed_index] - predicted_y[template_index]) / row_step
            for template_index, observed_index in path
        ])
        score = (
            .7 * float(np.median(errors))
            + .3 * float(np.mean(np.minimum(errors, 4)))
            + (template_count - len(path)) * .12
            + (observed_count - len(path)) * .18
        )
        if score < best_score:
            best_score = score
            best_prediction = predicted_y
            best_aligned = [None] * template_count
            for template_index, observed_index in path:
                best_aligned[template_index] = boxes[observed_index]
    return best_score, best_aligned, best_prediction


def _identify_context_page(boxes: list[tuple], canonical: bool = False) -> int | None:
    ranked = sorted(
        (_match_context_template(boxes, page, canonical)[0], page)
        for page in CONTEXT_Y_TEMPLATES
    )
    maximum_score = 2.50 if canonical else 1.20
    if not ranked or ranked[0][0] > maximum_score:
        return None
    if len(ranked) > 1 and ranked[1][0] - ranked[0][0] < .18:
        return None
    return ranked[0][1]


def _align_context_boxes(
    boxes: list[tuple], page: int, canonical: bool = False,
    gray: np.ndarray | None = None,
) -> list[tuple | None]:
    _, aligned, predicted_y = _match_context_template(boxes, page, canonical)
    if gray is None or not boxes or not any(box is None for box in aligned):
        return aligned

    image_h, image_w = gray.shape
    widths = np.asarray([box[5] for box in boxes], dtype=float)
    heights = np.asarray([box[6] for box in boxes], dtype=float)
    width = max(4, int(round(float(np.median(widths)))))
    height = max(4, int(round(float(np.median(heights)))))
    observed_y = np.asarray([box[1] for box in boxes], dtype=float)
    observed_x = np.asarray([box[0] for box in boxes], dtype=float)
    illumination = cv2.GaussianBlur(gray, (0, 0), sigmaX=35, sigmaY=35)
    normalized = cv2.divide(gray, np.maximum(illumination, 1), scale=235)
    for index, box in enumerate(aligned):
        if box is not None or not np.isfinite(predicted_y[index]):
            continue
        center_y = float(predicted_y[index])
        # Interpolar vecinos sigue la leve curvatura óptica de la columna y es
        # más preciso que proyectar una recta global cerca de los extremos.
        center_x = float(np.interp(center_y, observed_y, observed_x))
        x = int(round(center_x - width / 2))
        y = int(round(center_y - height / 2))
        if x < 1 or y < 1 or x + width >= image_w or y + height >= image_h:
            continue
        interior = normalized[
            round(y + height * .24):round(y + height * .76),
            round(x + width * .24):round(x + width * .76),
        ]
        left = normalized[
            round(y + height * .15):round(y + height * .85),
            max(0, round(x - width * 1.35)):max(1, round(x - width * .30)),
        ]
        right = normalized[
            round(y + height * .15):round(y + height * .85),
            min(image_w - 1, round(x + width * 1.30)):
            min(image_w, round(x + width * 2.15)),
        ]
        surroundings = [region.ravel() for region in (left, right) if region.size]
        darkness = (
            float((np.median(np.concatenate(surroundings)) - np.mean(interior)) / 255)
            if interior.size and surroundings else 0.0
        )
        aligned[index] = (center_x, center_y, darkness, x, y, width, height)
    return aligned


def _procesar_contexto(image: np.ndarray) -> dict:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    detection = _find_context_frame(gray)
    if detection is None:
        image_h, image_w = gray.shape
        corners = np.array(
            [[0, 0], [image_w - 1, 0], [image_w - 1, image_h - 1], [0, image_h - 1]],
            dtype=np.float32,
        )
        detection = _GridDetection(corners, .25, "context_full_image")
        warped = gray
        used_warp = False
    else:
        warped = _warp_context(gray, detection.corners)
        used_warp = True
    boxes = _context_checkboxes(warped)
    page = _identify_context_page(boxes, canonical=used_warp)
    if page is None:
        return {
            "respuestas": {}, "confianza": {}, "items_dudosos": [],
            "numero_hoja": None, "cantidad_items": 0,
            "used_warp": used_warp, "detection_method": "not_found",
            "detection_score": 0,
        }

    option_counts = (
        OPCIONES_POR_ITEM_CONTEXTO[:8]
        if page == 1 else OPCIONES_POR_ITEM_CONTEXTO[8:]
    )
    aligned_boxes = _align_context_boxes(
        boxes, page, canonical=used_warp, gray=warped,
    )
    # Los casilleros comparten columna. Partir por las cantidades impresas es
    # más estable ante encabezados y separadores de sección que usar distancias.
    responses: dict[int, str] = {}
    confidence: dict[int, int] = {}
    doubtful: list[int] = []
    # La base se calcula con contornos realmente observados. Los casilleros
    # reconstruidos pueden estar todos pintados y no deben elevar el umbral.
    baseline = float(np.median([box[2] for box in boxes])) if boxes else 0
    threshold = max(.10, baseline + .060)
    cursor = 0
    global_start = 1 if page == 1 else 9
    for local_item, option_count in enumerate(option_counts, start=1):
        option_boxes = aligned_boxes[cursor:cursor + option_count]
        cursor += option_count
        selected = [
            LETTERS[index] if index < len(LETTERS) else chr(65 + index)
            for index, box in enumerate(option_boxes)
            if box is not None and box[2] >= threshold
        ]
        responses[local_item] = ','.join(selected)
        global_item = global_start + local_item - 1
        if selected:
            marked_boxes = [
                box for box in option_boxes
                if box is not None and box[2] >= threshold
            ]
            confidence[local_item] = 68 if not marked_boxes else int(np.clip(
                55 + (min(box[2] for box in marked_boxes) - threshold) * 220,
                55, 99,
            ))
            if global_item not in ITEMS_MULTIPLES_CONTEXTO and len(selected) > 1:
                confidence[local_item] = 35
                doubtful.append(local_item)
        else:
            confidence[local_item] = 0
            doubtful.append(local_item)

    return {
        "respuestas": {str(key): value for key, value in responses.items()},
        "confianza": {str(key): value for key, value in confidence.items()},
        "items_dudosos": doubtful,
        "numero_hoja": page,
        "cantidad_items": len(option_counts),
        "used_warp": used_warp,
        "detection_method": detection.method,
        "detection_score": round(min(1.0, detection.score), 3),
        "student_box": tuple(int(value) for value in cv2.boundingRect(detection.corners)),
        "image_size": (gray.shape[1], gray.shape[0]),
    }


def procesar_imagen(imagen_bytes: bytes, tipo_examen: str = "lengua") -> dict:
    """Procesa una foto y devuelve respuestas, confianza y diagnóstico OMR."""
    image = _decode_image(imagen_bytes)
    if tipo_examen == "matematica":
        return _procesar_matematica(image)
    if tipo_examen == "contexto":
        return _procesar_contexto(image)
    if tipo_examen == "lengua":
        return _procesar_lengua(image)
    raise ValueError("El tipo de examen no es válido.")
