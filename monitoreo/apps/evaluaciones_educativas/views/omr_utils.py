# """
# views/omr_utils.py — Pipeline OMR con Python + OpenCV (backend)

# Requiere: pip install opencv-python-headless numpy

# Este módulo corre en el servidor Django, no en el navegador.
# El docente solo envía la foto → el servidor devuelve el JSON con respuestas.

# Diseñado para el examen "Evaluación Integral 2026" del Ministerio de Educación del Chaco:
#   - Ítems 1–9: Tabla 3×3, casillas cuadradas pequeñas (A/B/C/D), marcas = tachado diagonal
#   - Ítems 10–12: Sección docente separada (fila horizontal), siempre vacíos (completa el docente)
# """
# import numpy as np
# import cv2


# # ─── Configuración ────────────────────────────────────────────────────────────

# WORK_W, WORK_H = 900, 1200   # Canvas de trabajo (resize de la foto)
# WARP_W, WARP_H = 900, 700    # Tamaño de la imagen rectificada por perspectiva

# COLS         = 3             # Columnas de la tabla (ítems 1-9)
# ROWS         = 3             # Filas de la tabla
# OPTS         = 4             # Opciones por ítem (A/B/C/D)
# LETTERS      = ['A', 'B', 'C', 'D']

# # Umbral de densidad de píxeles oscuros para considerar un casillero como marcado.
# # Se reduce a 0.035 y se ajusta la ventana X para enfocar solo el cuadradito.
# MARK_THRESH  = 0.035

# # Confianza < CONF_LOW → ítem "dudoso" (requiere revisión manual)
# CONF_LOW     = 40

# # Fracción del alto de celda ocupada por la cabecera (número de ítem).
# # El examen tiene el número en la parte superior de cada celda.
# HEADER_RATIO = 0.20

# # Zona horizontal del casillero a analizar.
# # Ajustado para envolver exclusivamente el cuadradito y maximizar la densidad del tachado.
# CHECK_X_START  = 0.22
# CHECK_X_END    = 0.50

# # Margen vertical dentro de cada fila de opción
# CHECK_Y_MARGIN = 0.08        # antes: 0.05 — más margen para evitar ruido de bordes


# # ─── Funciones privadas ───────────────────────────────────────────────────────

# def _sort_corners(pts: np.ndarray) -> np.ndarray:
#     """
#     Ordena 4 puntos en el orden: TL (top-left), TR, BR, BL.
#     Usa la técnica de suma/diferencia de coordenadas para máxima robustez.
#     """
#     pts = pts.reshape(4, 2).astype(np.float32)
#     s   = pts.sum(axis=1)      # TL tiene menor suma, BR tiene mayor
#     d   = np.diff(pts, axis=1).flatten()  # TR tiene menor diferencia, BL mayor

#     return np.array([
#         pts[np.argmin(s)],    # TL
#         pts[np.argmin(d)],    # TR
#         pts[np.argmax(s)],    # BR
#         pts[np.argmax(d)],    # BL
#     ], dtype=np.float32)


# def _find_largest_rect(binary: np.ndarray, img_w: int, img_h: int):
#     """
#     Busca el contorno rectangular más grande en la imagen binaria.
#     Retorna las 4 esquinas ordenadas (TL/TR/BR/BL) como ndarray float32,
#     o None si no se encuentra ningún rectángulo válido.

#     Estrategia mejorada: prueba también con imagen de Canny edges para capturar
#     casos donde el threshold no delimita bien la tabla.
#     """
#     min_area = img_w * img_h * 0.04
#     max_area = img_w * img_h * 0.98

#     best_area = 0
#     best_pts  = None

#     for source in [binary]:
#         contours, _ = cv2.findContours(source, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)

#         for cnt in contours:
#             area = cv2.contourArea(cnt)
#             if not (min_area < area < max_area):
#                 continue

#             peri   = cv2.arcLength(cnt, True)
#             approx = cv2.approxPolyDP(cnt, 0.02 * peri, True)

#             if len(approx) == 4 and area > best_area:
#                 best_area = area
#                 best_pts  = approx

#     if best_pts is None:
#         return None

#     return _sort_corners(best_pts)


# def _find_rect_with_canny(gray: np.ndarray, img_w: int, img_h: int):
#     """
#     Intenta detectar el rectángulo de la tabla usando Canny edges + dilatación.
#     Útil cuando el threshold adaptativo no cierra bien los contornos de la tabla.
#     """
#     min_area = img_w * img_h * 0.04
#     max_area = img_w * img_h * 0.98

#     edges = cv2.Canny(gray, 50, 150)
#     kernel = np.ones((5, 5), np.uint8)
#     dilated = cv2.dilate(edges, kernel, iterations=2)

#     contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

#     best_area = 0
#     best_pts  = None

#     for cnt in contours:
#         area = cv2.contourArea(cnt)
#         if not (min_area < area < max_area):
#             continue

#         peri   = cv2.arcLength(cnt, True)
#         approx = cv2.approxPolyDP(cnt, 0.025 * peri, True)

#         if len(approx) == 4 and area > best_area:
#             best_area = area
#             best_pts  = approx

#     if best_pts is None:
#         return None

#     return _sort_corners(best_pts)


# def _measure_density(binary: np.ndarray, x: int, y: int, w: int, h: int) -> float:
#     """
#     Mide la proporción de píxeles marcados (255 en THRESH_BINARY_INV)
#     dentro de la región (x, y, w, h), con un margen interno del 8%.
#     """
#     m  = 0.08
#     x1 = max(0, int(x + w * m))
#     y1 = max(0, int(y + h * m))
#     x2 = min(binary.shape[1], int(x + w * (1 - m)))
#     y2 = min(binary.shape[0], int(y + h * (1 - m)))

#     if x2 <= x1 or y2 <= y1:
#         return 0.0

#     roi   = binary[y1:y2, x1:x2]
#     dark  = int(np.count_nonzero(roi))
#     total = (y2 - y1) * (x2 - x1)
#     return dark / total if total > 0 else 0.0


# def _compute_confidence(max_dens: float, second_dens: float, is_marked: bool) -> int:
#     """
#     Calcula la confianza de la detección (0–100).

#     Fórmula mejorada: penaliza más cuando la diferencia entre la mayor y segunda
#     densidad es pequeña (ambiguedad), y cuando la marca está justo en el umbral.
#     """
#     if max_dens <= 0:
#         return 0

#     # Ratio de diferencia entre 1er y 2do candidato
#     diff_ratio = (max_dens - second_dens) / (max_dens + 1e-6)

#     if is_marked:
#         # Bonus por margen claro (diff_ratio alto = menos ambigüedad)
#         conf = int(diff_ratio * 85 + min(max_dens * 200, 15))
#         conf = min(100, max(conf, 0))
#     else:
#         # Sin marca: confianza baja (el ítem está vacío)
#         conf = int(diff_ratio * 25)
#         conf = min(35, max(conf, 0))

#     return conf


# def _analyze_grid(binary: np.ndarray, img_w: int, img_h: int) -> tuple[dict, dict]:
#     """
#     Divide la imagen en grilla fija ROWS × COLS y mide densidad de marcas
#     en la zona de cada casillero (A/B/C/D) de cada ítem.

#     Retorna:
#         respuestas: {1: 'A', 2: '', 3: 'C', ...}
#         confianza:  {1: 85, 2: 0, 3: 72, ...}
#     """
#     cell_w   = img_w / COLS
#     cell_h   = img_h / ROWS
#     header_h = cell_h * HEADER_RATIO
#     opt_h    = (cell_h - header_h) / OPTS

#     respuestas: dict[int, str] = {}
#     confianza:  dict[int, int] = {}

#     for row in range(ROWS):
#         for col in range(COLS):
#             item_num = row * COLS + col + 1
#             cx = col * cell_w
#             cy = row * cell_h

#             densities = []
#             for opt in range(OPTS):
#                 opt_y    = cy + header_h + opt * opt_h
#                 check_x  = cx + cell_w * CHECK_X_START
#                 check_w  = cell_w * (CHECK_X_END - CHECK_X_START)
#                 check_y  = opt_y + opt_h * CHECK_Y_MARGIN
#                 check_h  = opt_h * (1 - 2 * CHECK_Y_MARGIN)

#                 sx = max(0, min(int(check_x), img_w - 2))
#                 sy = max(0, min(int(check_y), img_h - 2))
#                 sw = max(1, min(int(check_w), img_w - sx - 1))
#                 sh = max(1, min(int(check_h), img_h - sy - 1))

#                 densities.append(_measure_density(binary, sx, sy, sw, sh))

#             max_dens    = max(densities)
#             sorted_desc = sorted(densities, reverse=True)
#             second_dens = sorted_desc[1] if len(sorted_desc) > 1 else 0.0
#             max_idx     = densities.index(max_dens)

#             is_marked = max_dens >= MARK_THRESH
#             respuestas[item_num] = LETTERS[max_idx] if is_marked else ''
#             confianza[item_num]  = _compute_confidence(max_dens, second_dens, is_marked)

#     return respuestas, confianza


# def _preprocess(gray: np.ndarray) -> np.ndarray:
#     """
#     Preprocesa la imagen en escala de grises para mejorar la detección de marcas.

#     Pipeline:
#       1. Normalización CLAHE (equalización local de histograma) — compensa
#          fotos oscuras, sobreexpuestas o con luz no uniforme.
#       2. GaussianBlur — reduce ruido de sensor.
#       3. adaptiveThreshold — binariza respetando variaciones locales de iluminación.
#       4. morphologyEx CLOSE — une bordes interrumpidos del casillero.
#     """
#     # 1. CLAHE: ecualización adaptativa del histograma (mejor que normalize() para OMR)
#     clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
#     enhanced = clahe.apply(gray)

#     # 2. Blur suave para reducir ruido
#     blurred = cv2.GaussianBlur(enhanced, (5, 5), 0)

#     # 3. Threshold adaptativo (bloque 19x19 para casillas pequeñas)
#     binary = cv2.adaptiveThreshold(
#         blurred, 255,
#         cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
#         cv2.THRESH_BINARY_INV,
#         19, 6,
#     )

#     # 4. Cierre morfológico para unir trazos interrumpidos del tachado
#     kernel = np.ones((2, 2), np.uint8)
#     closed = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)

#     return closed


# # ─── API pública ──────────────────────────────────────────────────────────────

# def procesar_imagen(imagen_bytes: bytes) -> dict:
#     """
#     Procesa los bytes de la imagen de un examen OMR y retorna las respuestas detectadas.

#     Diseñado para el examen "Evaluación Integral 2026" del Ministerio de Educación del Chaco:
#     - Ítems 1–9: tabla 3×3 con casillas cuadradas (marcas = tachado diagonal/cruzado)
#     - Ítems 10–12: sección docente separada — siempre vacíos (se completan a mano)

#     Pipeline:
#       1. Decodificar → resize a WORK_W × WORK_H
#       2. Grayscale → CLAHE → GaussianBlur → adaptiveThreshold → CLOSE
#       3. Detección de tabla: intenta con threshold primero, luego Canny como fallback
#       4. warpPerspective → rectificar perspectiva si se encontró la tabla
#       5. Grilla fija 3×3 → medir densidad de marcas por ítem (1–9)
#       6. Ítems 10–12 → vacíos (sección docente, se completa manualmente)

#     Returns:
#         {
#             'respuestas':    {'1': 'A', '2': 'C', ...},
#             'confianza':     {'1': 85,  '2': 40,  ...},
#             'items_dudosos': [3, 7],
#             'used_warp':     True | False,
#         }

#     Raises:
#         ValueError: si la imagen no se puede decodificar
#         ImportError: si opencv-python-headless no está instalado
#     """
#     # ── 1. Decodificar ────────────────────────────────────────────────────────
#     nparr = np.frombuffer(imagen_bytes, np.uint8)
#     img   = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

#     if img is None:
#         raise ValueError('No se pudo decodificar la imagen. Verificá el formato (JPG/PNG/WEBP).')

#     img = cv2.resize(img, (WORK_W, WORK_H), interpolation=cv2.INTER_AREA)

#     # ── 2. Preprocessing ──────────────────────────────────────────────────────
#     gray   = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
#     binary = _preprocess(gray)

#     # Para detección de contornos usamos un threshold con bloque más grande (detecta mejor bordes de tabla)
#     blurred_big = cv2.GaussianBlur(gray, (7, 7), 0)
#     binary_big  = cv2.adaptiveThreshold(
#         blurred_big, 255,
#         cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
#         cv2.THRESH_BINARY_INV,
#         21, 5,
#     )
#     kernel_big = np.ones((3, 3), np.uint8)
#     closed_big = cv2.morphologyEx(binary_big, cv2.MORPH_CLOSE, kernel_big)

#     # ── 3. Detectar tabla: threshold primero, luego Canny como fallback ───────
#     corners   = _find_largest_rect(closed_big, WORK_W, WORK_H)
#     used_warp = False

#     if corners is None:
#         # Segundo intento: Canny edges (más robusto con fotos de bajo contraste)
#         corners = _find_rect_with_canny(gray, WORK_W, WORK_H)

#     if corners is not None:
#         # ── 4. Corrección de perspectiva ──────────────────────────────────────
#         dst_pts = np.array([
#             [0,      0      ],
#             [WARP_W, 0      ],
#             [WARP_W, WARP_H ],
#             [0,      WARP_H ],
#         ], dtype=np.float32)

#         M           = cv2.getPerspectiveTransform(corners, dst_pts)
#         warped_gray = cv2.warpPerspective(gray, M, (WARP_W, WARP_H))
#         analysis_mat = _preprocess(warped_gray)
#         analysis_w   = WARP_W
#         analysis_h   = WARP_H
#         used_warp    = True

#     else:
#         # ── Fallback: recorte heurístico basado en el layout del examen Chaco 2026
#         # La tabla "CLAVE DE RESPUESTAS" ocupa aproximadamente:
#         #   - horizontal: 3% → 97% del ancho
#         #   - vertical:   25% → 72% del alto de la página
#         rx = int(WORK_W * 0.03)
#         ry = int(WORK_H * 0.25)
#         rw = int(WORK_W * 0.94)
#         rh = int(WORK_H * 0.47)
#         analysis_mat = binary[ry:ry + rh, rx:rx + rw]
#         analysis_w   = rw
#         analysis_h   = rh

#     # ── 5. Analizar grilla 3×3 (ítems 1–9) ───────────────────────────────────
#     respuestas, confianza = _analyze_grid(analysis_mat, analysis_w, analysis_h)

#     # ── 6. Ítems 10–12 (sección docente) → vacíos por defecto ─────────────────
#     # Esta sección está reservada para el "Docente Aplicador" y se completa
#     # manualmente desde el panel de resultados.
#     for i in range(10, 13):
#         respuestas[i] = ''
#         confianza[i]  = 0

#     # ── 7. Calcular ítems dudosos ─────────────────────────────────────────────
#     # Solo marcar como dudosos los ítems 1–9 (los docente son siempre 0)
#     items_dudosos = [k for k, v in confianza.items() if k <= 9 and v < CONF_LOW]

#     return {
#         'respuestas':    {str(k): v for k, v in respuestas.items()},
#         'confianza':     {str(k): v for k, v in confianza.items()},
#         'items_dudosos': items_dudosos,
#         'used_warp':     used_warp,
#         'corners':       corners.tolist() if corners is not None else None,
#     }
