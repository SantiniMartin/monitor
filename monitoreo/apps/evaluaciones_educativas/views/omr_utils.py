"""
views/omr_utils.py — Pipeline OMR con Python + OpenCV (backend)

Requiere: pip install opencv-python-headless numpy

Este módulo corre en el servidor Django, no en el navegador.
El docente solo envía la foto → el servidor devuelve el JSON con respuestas.
"""
import numpy as np
import cv2


# ─── Configuración ────────────────────────────────────────────────────────────
# Debe coincidir con CFG en omr_processor.js para que el overlay de debug
# del frontend sea consistente.

WORK_W, WORK_H = 900, 1200   # Canvas de trabajo (resize de la foto)
WARP_W, WARP_H = 900, 700    # Tamaño de la imagen rectificada por perspectiva

COLS         = 3             # Columnas de la tabla (ítems 1-9)
ROWS         = 3             # Filas de la tabla
OPTS         = 4             # Opciones por ítem (A/B/C/D)
LETTERS      = ['A', 'B', 'C', 'D']

MARK_THRESH  = 0.04          # Densidad mínima de px oscuros para "marcado" (reducida para garabatos)
CONF_LOW     = 40            # Confianza < 40 → ítem "dudoso"

HEADER_RATIO = 0.22          # Fracción del alto de celda ocupado por la cabecera (n° ítem)
CHECK_X_START = 0.20         # Zona del casillero: empieza aprox 20% (pasando la letra)
CHECK_X_END   = 0.40         # Termina en 40% (solo el ancho de la casilla [])
CHECK_Y_MARGIN = 0.15        # Margen vertical mayor para descartar los bordes negros de la casilla


# ─── Funciones privadas ───────────────────────────────────────────────────────

def _sort_corners(pts: np.ndarray) -> np.ndarray:
    """
    Ordena 4 puntos en el orden: TL (top-left), TR, BR, BL.
    Usa la técnica de suma/diferencia de coordenadas para máxima robustez.
    """
    pts = pts.reshape(4, 2).astype(np.float32)
    s   = pts.sum(axis=1)      # TL tiene menor suma, BR tiene mayor
    d   = np.diff(pts, axis=1).flatten()  # TR tiene menor diferencia, BL mayor

    return np.array([
        pts[np.argmin(s)],    # TL
        pts[np.argmin(d)],    # TR
        pts[np.argmax(s)],    # BR
        pts[np.argmax(d)],    # BL
    ], dtype=np.float32)


def _find_largest_rect(binary: np.ndarray, img_w: int, img_h: int):
    """
    Busca el contorno rectangular más grande en la imagen binaria.
    Retorna las 4 esquinas ordenadas (TL/TR/BR/BL) como ndarray float32,
    o None si no se encuentra ningún rectángulo válido.
    """
    min_area = img_w * img_h * 0.04
    max_area = img_w * img_h * 0.98

    contours, _ = cv2.findContours(binary, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)

    best_area = 0
    best_pts  = None

    for cnt in contours:
        area = cv2.contourArea(cnt)
        if not (min_area < area < max_area):
            continue

        peri   = cv2.arcLength(cnt, True)
        approx = cv2.approxPolyDP(cnt, 0.02 * peri, True)

        if len(approx) == 4 and area > best_area:
            # Ordenar esquinas para medir aspect ratio (ancho / alto)
            pts = _sort_corners(approx)
            w_rect = np.linalg.norm(pts[0] - pts[1])
            h_rect = np.linalg.norm(pts[0] - pts[3])
            aspect = w_rect / h_rect if h_rect > 0 else 0
            
            # La tabla OMR es más ancha que alta (aspect ratio > 1.1)
            # La hoja de papel en portrait es más alta que ancha (aspect ratio ~ 0.75)
            if aspect > 1.1:
                best_area = area
                best_pts  = approx

    if best_pts is None:
        return None

    return _sort_corners(best_pts)


def _measure_density(binary: np.ndarray, x: int, y: int, w: int, h: int) -> float:
    """
    Mide la proporción de píxeles marcados (255 en THRESH_BINARY_INV)
    dentro de la región (x, y, w, h), con un margen interno del 7%.
    """
    m  = 0.07
    x1 = max(0, int(x + w * m))
    y1 = max(0, int(y + h * m))
    x2 = min(binary.shape[1], int(x + w * (1 - m)))
    y2 = min(binary.shape[0], int(y + h * (1 - m)))

    if x2 <= x1 or y2 <= y1:
        return 0.0

    roi   = binary[y1:y2, x1:x2]
    dark  = int(np.count_nonzero(roi))
    total = (y2 - y1) * (x2 - x1)
    return dark / total if total > 0 else 0.0


def _analyze_grid(binary: np.ndarray, img_w: int, img_h: int) -> tuple[dict, dict]:
    """
    Divide la imagen en grilla fija ROWS × COLS y mide densidad de marcas
    en la zona de cada casillero (A/B/C/D) de cada ítem.

    Retorna:
        respuestas: {1: 'A', 2: '', 3: 'C', ...}
        confianza:  {1: 85, 2: 0, 3: 72, ...}
    """
    cell_w   = img_w / COLS
    cell_h   = img_h / ROWS
    header_h = cell_h * HEADER_RATIO
    opt_h    = (cell_h - header_h) / OPTS

    respuestas: dict[int, str] = {}
    confianza:  dict[int, int] = {}

    for row in range(ROWS):
        for col in range(COLS):
            item_num = row * COLS + col + 1
            cx = col * cell_w
            cy = row * cell_h

            densities = []
            for opt in range(OPTS):
                opt_y    = cy + header_h + opt * opt_h
                check_x  = cx + cell_w * CHECK_X_START
                check_w  = cell_w * (CHECK_X_END - CHECK_X_START)
                check_y  = opt_y + opt_h * CHECK_Y_MARGIN
                check_h  = opt_h * (1 - 2 * CHECK_Y_MARGIN)

                sx = max(0, min(int(check_x), img_w - 2))
                sy = max(0, min(int(check_y), img_h - 2))
                sw = max(1, min(int(check_w), img_w - sx - 1))
                sh = max(1, min(int(check_h), img_h - sy - 1))

                densities.append(_measure_density(binary, sx, sy, sw, sh))

            max_dens    = max(densities)
            sorted_desc = sorted(densities, reverse=True)
            second_dens = sorted_desc[1] if len(sorted_desc) > 1 else 0.0
            max_idx     = densities.index(max_dens)

            is_marked = max_dens >= MARK_THRESH
            respuestas[item_num] = LETTERS[max_idx] if is_marked else ''

            if max_dens > 0:
                conf = min(100, int(((max_dens - second_dens) / (max_dens + 1e-6)) * 100))
                if not is_marked:
                    conf = int(conf * 0.4)
            else:
                conf = 0
            confianza[item_num] = conf

    return respuestas, confianza


# ─── API pública ──────────────────────────────────────────────────────────────

def procesar_imagen(imagen_bytes: bytes) -> dict:
    """
    Procesa los bytes de la imagen de un examen OMR y retorna las respuestas detectadas.

    Pipeline:
      1. Decodificar → resize a WORK_W × WORK_H
      2. Grayscale → GaussianBlur (reduce ruido de cámara)
      3. adaptiveThreshold (tolera sombras e iluminación irregular)
      4. morphologyEx CLOSE (une bordes interrumpidos)
      5. findContours + approxPolyDP → detectar tabla (CLAVE DE RESPUESTAS)
      6. warpPerspective → rectificar perspectiva de fotos torcidas
      7. Grilla fija 3×3 → medir densidad de marcas por ítem
      8. Ítems 10-12 → vacíos (sección docente, se completa manualmente)

    Returns:
        {
            'respuestas':    {'1': 'A', '2': 'C', ...},
            'confianza':     {'1': 85,  '2': 40,  ...},
            'items_dudosos': [3, 7],
            'used_warp':     True | False,
        }

    Raises:
        ValueError: si la imagen no se puede decodificar
        ImportError: si opencv-python-headless no está instalado
    """
    # ── 1. Decodificar ────────────────────────────────────────────────────────
    nparr = np.frombuffer(imagen_bytes, np.uint8)
    img   = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if img is None:
        raise ValueError('No se pudo decodificar la imagen. Verificá el formato (JPG/PNG/WEBP).')

    img = cv2.resize(img, (WORK_W, WORK_H), interpolation=cv2.INTER_AREA)

    # ── 2-4. Preprocessing ────────────────────────────────────────────────────
    gray    = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (7, 7), 0)

    binary = cv2.adaptiveThreshold(
        blurred, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        21, 5,
    )

    kernel = np.ones((3, 3), np.uint8)
    closed = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)

    # ── 5. Detectar tabla ─────────────────────────────────────────────────────
    corners   = _find_largest_rect(closed, WORK_W, WORK_H)
    used_warp = False

    if corners is not None:
        # ── 6. Corrección de perspectiva ──────────────────────────────────────
        dst_pts = np.array([
            [0,      0      ],
            [WARP_W, 0      ],
            [WARP_W, WARP_H ],
            [0,      WARP_H ],
        ], dtype=np.float32)

        M           = cv2.getPerspectiveTransform(corners, dst_pts)
        warped_gray = cv2.warpPerspective(gray, M, (WARP_W, WARP_H))
        warped_blur = cv2.GaussianBlur(warped_gray, (7, 7), 0)
        warped_bin  = cv2.adaptiveThreshold(
            warped_blur, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV,
            21, 5,
        )

        analysis_mat = warped_bin
        analysis_w   = WARP_W
        analysis_h   = WARP_H
        used_warp    = True

    else:
        # Fallback: recorte heurístico basado en el layout conocido del examen
        rx = int(WORK_W * 0.04)
        ry = int(WORK_H * 0.28)
        rw = int(WORK_W * 0.92)
        rh = int(WORK_H * 0.42)
        analysis_mat = binary[ry:ry + rh, rx:rx + rw]
        analysis_w   = rw
        analysis_h   = rh

    # ── 7. Analizar grilla ────────────────────────────────────────────────────
    respuestas, confianza = _analyze_grid(analysis_mat, analysis_w, analysis_h)

    # ── 8. Ítems 10-12 (sección docente) → vacíos por defecto ────────────────
    for i in range(10, 13):
        respuestas[i] = ''
        confianza[i]  = 0

    items_dudosos = [k for k, v in confianza.items() if v < CONF_LOW]

    return {
        'respuestas':    {str(k): v for k, v in respuestas.items()},
        'confianza':     {str(k): v for k, v in confianza.items()},
        'items_dudosos': items_dudosos,
        'used_warp':     used_warp,
    }
