/**
 * omr_processor.js — v2 REESCRITURA COMPLETA
 *
 * Estrategia mejorada:
 *  1. Escala de grises + mejora de contraste por bloques (CLAHE-lite)
 *  2. Umbralización de Otsu → imagen binaria limpia
 *  3. Proyecciones para detectar la tabla (CLAVE DE RESPUESTAS)
 *  4. GRILLA FIJA: en lugar de detectar células dinámicamente,
 *     una vez encontrada la tabla la dividimos en una grilla 3×3 conocida.
 *     Esto elimina el bug de la v1 donde los 12 casilleros de la misma
 *     columna X se agrupaban incorrectamente.
 *  5. Por cada celda de la grilla: subdivide en 1 fila de cabecera + 4 filas
 *     de opción (A/B/C/D), mide densidad de píxeles oscuros en zona del casillero.
 *  6. Overlay de debug en el canvas de preview para verificar detección.
 */

'use strict';

const OMRProcessor = (() => {

  // ─── Configuración ────────────────────────────────────────────────────────────
  const CFG = {
    W: 900,           // ancho de trabajo del canvas
    H: 1200,          // alto de trabajo del canvas
    COLS: 3,          // columnas en la tabla de respuestas (ítems 1-9)
    ROWS: 3,          // filas en la tabla de respuestas (ítems 1-9)
    OPTS: 4,          // opciones por ítem (A/B/C/D)
    ITEMS: 12,        // total de ítems
    LETTERS: ['A','B','C','D'],
    MARK_THRESH: 0.07,       // densidad mínima para considerar "marcado" (7%)
    CONF_LOW: 45,            // umbral de confianza baja → ítem "dudoso"
    HEADER_RATIO: 0.22,      // fracción de cada celda que ocupa la cabecera (n° ítem)
    CHECK_X_START: 0.15,     // desde qué fracción del ancho de la celda empieza zona de casillero
    CHECK_X_END:   0.75,     // hasta qué fracción termina la zona de casillero
    CHECK_Y_MARGIN: 0.06,    // margen vertical interno en zona de casillero
    BLOCK_SIZE: 72,          // tamaño de bloque para normalización local de contraste
  };

  // ─── Carga de imagen ──────────────────────────────────────────────────────────
  function loadImage(file) {
    return new Promise((resolve, reject) => {
      const img = new Image();
      img.onload = () => resolve(img);
      img.onerror = reject;
      img.src = URL.createObjectURL(file);
    });
  }

  // ─── Preprocesamiento ─────────────────────────────────────────────────────────

  /** Escala de grises usando pesos perceptuales */
  function rgb2gray(imageData) {
    const { data, width, height } = imageData;
    const gray = new Uint8Array(width * height);
    for (let i = 0; i < gray.length; i++) {
      const p = i * 4;
      gray[i] = Math.round(0.299 * data[p] + 0.587 * data[p+1] + 0.114 * data[p+2]);
    }
    return gray;
  }

  /**
   * Mejora de contraste por bloques (similar a CLAHE).
   * Normaliza el histograma dentro de cada bloque de CFG.BLOCK_SIZE × CFG.BLOCK_SIZE.
   * Esto compensa sombras locales e iluminación no uniforme.
   */
  function localContrastEnhance(gray, width, height) {
    const out = new Uint8Array(gray.length);
    const bs = CFG.BLOCK_SIZE;

    for (let by = 0; by < height; by += bs) {
      for (let bx = 0; bx < width; bx += bs) {
        const y2 = Math.min(by + bs, height);
        const x2 = Math.min(bx + bs, width);

        // Min/max del bloque
        let min = 255, max = 0;
        for (let y = by; y < y2; y++) {
          for (let x = bx; x < x2; x++) {
            const v = gray[y * width + x];
            if (v < min) min = v;
            if (v > max) max = v;
          }
        }
        const range = (max - min) || 1;

        for (let y = by; y < y2; y++) {
          for (let x = bx; x < x2; x++) {
            out[y * width + x] = Math.round(((gray[y * width + x] - min) / range) * 255);
          }
        }
      }
    }
    return out;
  }

  /**
   * Umbralización de Otsu — calcula el umbral óptimo que maximiza
   * la varianza inter-clase en el histograma de grises.
   */
  function otsuThreshold(gray) {
    const hist = new Int32Array(256);
    for (let i = 0; i < gray.length; i++) hist[gray[i]]++;

    const N = gray.length;
    let sum = 0;
    for (let i = 0; i < 256; i++) sum += i * hist[i];

    let sumB = 0, wB = 0, maxVar = 0, thresh = 128;

    for (let i = 0; i < 256; i++) {
      wB += hist[i];
      if (!wB) continue;
      const wF = N - wB;
      if (!wF) break;
      sumB += i * hist[i];
      const mB = sumB / wB;
      const mF = (sum - sumB) / wF;
      const v = wB * wF * (mB - mF) ** 2;
      if (v > maxVar) { maxVar = v; thresh = i; }
    }
    return thresh;
  }

  /** Binariza la imagen (0 = oscuro/marcado, 255 = claro/fondo) */
  function binarize(gray, thresh) {
    const bin = new Uint8Array(gray.length);
    for (let i = 0; i < gray.length; i++) {
      bin[i] = gray[i] < thresh ? 0 : 255;
    }
    return bin;
  }

  // ─── Detección de la tabla ────────────────────────────────────────────────────

  /** Proyección horizontal: cantidad de píxeles oscuros por fila */
  function hProjection(bin, width, height) {
    const proj = new Int32Array(height);
    for (let y = 0; y < height; y++) {
      for (let x = 0; x < width; x++) {
        if (bin[y * width + x] === 0) proj[y]++;
      }
    }
    return proj;
  }

  /** Proyección vertical: cantidad de píxeles oscuros por columna */
  function vProjection(bin, width, height) {
    const proj = new Int32Array(width);
    for (let x = 0; x < width; x++) {
      for (let y = 0; y < height; y++) {
        if (bin[y * width + x] === 0) proj[x]++;
      }
    }
    return proj;
  }

  /**
   * Suaviza una proyección con ventana deslizante para eliminar ruido.
   */
  function smoothProjection(proj, window = 5) {
    const out = new Float32Array(proj.length);
    const half = Math.floor(window / 2);
    for (let i = 0; i < proj.length; i++) {
      let sum = 0, count = 0;
      for (let j = Math.max(0, i-half); j <= Math.min(proj.length-1, i+half); j++) {
        sum += proj[j]; count++;
      }
      out[i] = sum / count;
    }
    return out;
  }

  /**
   * Encuentra los límites de la tabla CLAVE DE RESPUESTAS.
   *
   * Estrategia:
   *  - Analizar proyecciones para encontrar zonas con muchos píxeles oscuros
   *    (líneas de la tabla)
   *  - El límite exterior de la tabla corresponde al rango de filas/columnas
   *    donde aparecen picos de oscuridad > umbral
   *
   * Si la detección falla, usa valores heurísticos basados en el layout
   * conocido de este tipo de examen.
   */
  function detectTable(bin, width, height) {
    const hProj = smoothProjection(hProjection(bin, width, height), 7);
    const vProj = smoothProjection(vProjection(bin, width, height), 7);

    // Encontrar picos horizontales significativos (líneas que cruzan > 25% del ancho)
    const hThresh = width * 0.25;
    const hPeaks = [];
    let inPeak = false, peakY0 = 0;
    for (let y = 0; y < height; y++) {
      if (hProj[y] >= hThresh && !inPeak) {
        inPeak = true; peakY0 = y;
      } else if (hProj[y] < hThresh && inPeak) {
        hPeaks.push(Math.round((peakY0 + y - 1) / 2));
        inPeak = false;
      }
    }
    if (inPeak) hPeaks.push(Math.round((peakY0 + height - 1) / 2));

    // Picos verticales (columnas que cruzan > 8% del alto)
    const vThresh = height * 0.08;
    const vPeaks = [];
    inPeak = false;
    let peakX0 = 0;
    for (let x = 0; x < width; x++) {
      if (vProj[x] >= vThresh && !inPeak) {
        inPeak = true; peakX0 = x;
      } else if (vProj[x] < vThresh && inPeak) {
        vPeaks.push(Math.round((peakX0 + x - 1) / 2));
        inPeak = false;
      }
    }
    if (inPeak) vPeaks.push(Math.round((peakX0 + width - 1) / 2));

    // Filtrar picos muy cercanos al borde (< 5%) — son ruido de borde de hoja
    const hFiltered = hPeaks.filter(y => y > height * 0.05 && y < height * 0.95);
    const vFiltered = vPeaks.filter(x => x > width * 0.03 && x < width * 0.97);

    // Fallback heurístico basado en el layout del examen Chaco
    // (CLAVE DE RESPUESTAS ocupa aprox. el tercio central de la hoja)
    const fallback = {
      x: Math.round(width * 0.04),
      y: Math.round(height * 0.28),
      w: Math.round(width * 0.92),
      h: Math.round(height * 0.42),
    };

    if (hFiltered.length < 2 || vFiltered.length < 2) {
      console.warn('[OMR] Proyección insuficiente, usando bounds heurísticos');
      return { ...fallback, fallback: true };
    }

    // La tabla va desde el primer al último pico con longitud mínima razonable
    const y1 = hFiltered[0];
    const y2 = hFiltered[hFiltered.length - 1];
    const x1 = vFiltered[0];
    const x2 = vFiltered[vFiltered.length - 1];

    const w = x2 - x1;
    const h = y2 - y1;

    // Validación: la tabla debe tener proporciones razonables
    if (w < width * 0.30 || h < height * 0.10 || w > width || h > height * 0.80) {
      console.warn('[OMR] Bounds detectados inválidos, usando heurísticos', {x1,y1,x2,y2,w,h});
      return { ...fallback, fallback: true };
    }

    return { x: x1, y: y1, w, h, fallback: false };
  }

  // ─── Análisis de la grilla fija ───────────────────────────────────────────────

  /**
   * Mide la densidad de píxeles oscuros (marcas) en una región rectangular.
   *
   * @param {Uint8Array} bin — imagen binaria
   * @param {number} width
   * @param {number} rx,ry,rw,rh — región de análisis (puede tener decimales)
   * @param {number} margin — margen interno proporcional (0-0.5)
   * @returns {number} densidad 0.0-1.0
   */
  function measureDensity(bin, width, rx, ry, rw, rh, margin = 0.08) {
    const x1 = Math.round(rx + rw * margin);
    const y1 = Math.round(ry + rh * margin);
    const x2 = Math.round(rx + rw * (1 - margin));
    const y2 = Math.round(ry + rh * (1 - margin));
    const maxY = Math.floor(bin.length / width);

    if (x2 <= x1 || y2 <= y1) return 0;

    let dark = 0, total = 0;
    for (let y = y1; y < Math.min(y2, maxY); y++) {
      for (let x = x1; x < Math.min(x2, width); x++) {
        if (bin[y * width + x] === 0) dark++;
        total++;
      }
    }
    return total > 0 ? dark / total : 0;
  }

  /**
   * Análisis por grilla fija 3×3.
   *
   * Una vez detectados los bounds de la tabla, la dividimos con proporciones
   * iguales en 3 columnas × 3 filas. Dentro de cada celda (ítem), se
   * identifica la zona de la cabecera y las 4 filas de opciones A/B/C/D.
   *
   * Dentro de cada fila de opción se analiza la zona del casillero cuadrado
   * (definida por CHECK_X_START/END en proporción al ancho de la celda).
   */
  function analyzeFixedGrid(bin, width, table) {
    const { x: tx, y: ty, w: tw, h: th } = table;

    const cellW = tw / CFG.COLS;
    const cellH = th / CFG.ROWS;
    const headerH = cellH * CFG.HEADER_RATIO;
    const optH = (cellH - headerH) / CFG.OPTS;

    const respuestas = {};
    const confianza = {};
    // Guardar datos de debug (densidades crudas)
    const debug = {};

    for (let row = 0; row < CFG.ROWS; row++) {
      for (let col = 0; col < CFG.COLS; col++) {
        const itemNum = row * CFG.COLS + col + 1;
        const cx = tx + col * cellW;
        const cy = ty + row * cellH;

        const densities = new Array(CFG.OPTS);

        for (let opt = 0; opt < CFG.OPTS; opt++) {
          // Coordenadas de la fila de opción (A/B/C/D)
          const optY = cy + headerH + opt * optH;

          // Zona del casillero: fracción del ancho de la celda
          const checkX = cx + cellW * CFG.CHECK_X_START;
          const checkW = cellW * (CFG.CHECK_X_END - CFG.CHECK_X_START);
          const checkH = optH * (1 - 2 * CFG.CHECK_Y_MARGIN);
          const checkY = optY + optH * CFG.CHECK_Y_MARGIN;

          densities[opt] = measureDensity(bin, width, checkX, checkY, checkW, checkH);
        }

        debug[itemNum] = densities.map(d => d.toFixed(4));

        // La opción con mayor densidad
        const maxDens = Math.max(...densities);
        const sorted = [...densities].sort((a, b) => b - a);
        const secondDens = sorted[1] ?? 0;
        const maxIdx = densities.indexOf(maxDens);

        // ¿Está marcada? Solo si supera el umbral mínimo
        const isMarked = maxDens >= CFG.MARK_THRESH;
        respuestas[itemNum] = isMarked ? CFG.LETTERS[maxIdx] : '';

        // Confianza: separación relativa entre la más alta y la segunda
        let conf = 0;
        if (maxDens > 0) {
          conf = Math.min(100, Math.round(((maxDens - secondDens) / (maxDens + 1e-6)) * 100));
          // Si no supera el umbral de marcado, la confianza es baja
          if (!isMarked) conf = Math.round(conf * 0.4);
        }
        confianza[itemNum] = conf;
      }
    }

    console.log('[OMR] Densidades por ítem:', debug);
    return { respuestas, confianza };
  }

  /**
   * Intenta detectar también los ítems 10-12 (sección "Solo para el Docente").
   * Estos aparecen DEBAJO de la tabla principal en formato horizontal:
   *   10) A□  B□  C□  D□
   *
   * Si no se detectan, devuelve vacíos para que el docente los complete.
   */
  function analyzeTeacherSection(bin, width, height, mainTable) {
    const respuestas = {};
    const confianza = {};

    // La sección docente empieza aproximadamente a un 15% de altura después de la tabla
    const sectionY = mainTable.y + mainTable.h + height * 0.05;
    const sectionH = height * 0.14;
    const sectionX = mainTable.x;
    const sectionW = mainTable.w;

    if (sectionY + sectionH > height) {
      // Fuera de imagen
      for (let i = 10; i <= 12; i++) { respuestas[i] = ''; confianza[i] = 0; }
      return { respuestas, confianza };
    }

    // Cada ítem (10, 11, 12) ocupa ~1/3 del alto de la sección
    const itemH = sectionH / 3;
    // Dentro de cada ítem, las 4 opciones están distribuidas horizontalmente
    // Estimamos que los 4 casilleros ocupan el 75% del ancho a partir del 20%
    const optW = (sectionW * 0.75) / 4;
    const optsStartX = sectionX + sectionW * 0.20;

    for (let i = 0; i < 3; i++) {
      const itemNum = 10 + i;
      const itemY = sectionY + i * itemH;
      const densities = [];

      for (let opt = 0; opt < CFG.OPTS; opt++) {
        const ox = optsStartX + opt * optW;
        densities.push(measureDensity(bin, width, ox, itemY, optW, itemH * 0.85));
      }

      const maxDens = Math.max(...densities);
      const sorted = [...densities].sort((a, b) => b - a);
      const secondDens = sorted[1] ?? 0;
      const maxIdx = densities.indexOf(maxDens);

      const isMarked = maxDens >= CFG.MARK_THRESH;
      respuestas[itemNum] = isMarked ? CFG.LETTERS[maxIdx] : '';

      let conf = 0;
      if (maxDens > 0) {
        conf = Math.min(100, Math.round(((maxDens - secondDens) / (maxDens + 1e-6)) * 100));
        if (!isMarked) conf = Math.round(conf * 0.4);
      }
      confianza[itemNum] = conf;
    }

    return { respuestas, confianza };
  }

  // ─── Overlay de debug ─────────────────────────────────────────────────────────

  /**
   * Dibuja sobre el canvas de preview las zonas de análisis detectadas,
   * con colores según resultado: verde = marcado, azul = no marcado, rojo = sin marca.
   */
  function drawDebugOverlay(canvas, table, respuestas, confianza) {
    const ctx = canvas.getContext('2d');
    const { x: tx, y: ty, w: tw, h: th } = table;

    // Rectángulo exterior de la tabla
    ctx.strokeStyle = table.fallback ? 'rgba(255,165,0,0.9)' : 'rgba(0,255,100,0.9)';
    ctx.lineWidth = 3;
    ctx.strokeRect(tx, ty, tw, th);

    const cellW = tw / CFG.COLS;
    const cellH = th / CFG.ROWS;
    const headerH = cellH * CFG.HEADER_RATIO;
    const optH = (cellH - headerH) / CFG.OPTS;

    for (let row = 0; row < CFG.ROWS; row++) {
      for (let col = 0; col < CFG.COLS; col++) {
        const itemNum = row * CFG.COLS + col + 1;
        const cx = tx + col * cellW;
        const cy = ty + row * cellH;
        const resp = respuestas[itemNum];

        // Dibujar separadores de celda
        ctx.strokeStyle = 'rgba(0,200,255,0.4)';
        ctx.lineWidth = 1;
        ctx.strokeRect(cx, cy, cellW, cellH);

        for (let opt = 0; opt < CFG.OPTS; opt++) {
          const optY = cy + headerH + opt * optH;
          const checkX = cx + cellW * CFG.CHECK_X_START;
          const checkW = cellW * (CFG.CHECK_X_END - CFG.CHECK_X_START);
          const checkY = optY + optH * CFG.CHECK_Y_MARGIN;
          const checkH = optH * (1 - 2 * CFG.CHECK_Y_MARGIN);

          const isSelected = resp === CFG.LETTERS[opt];
          const isLowConf = confianza[itemNum] < CFG.CONF_LOW;

          ctx.strokeStyle = isSelected
            ? (isLowConf ? 'rgba(255,165,0,0.95)' : 'rgba(255,60,60,0.95)')
            : 'rgba(0,200,255,0.25)';
          ctx.lineWidth = isSelected ? 2.5 : 1;
          ctx.strokeRect(checkX, checkY, checkW, checkH);
        }

        // Etiqueta de resultado en la esquina de la celda
        ctx.font = 'bold 13px sans-serif';
        ctx.fillStyle = resp ? 'rgba(255,230,0,0.95)' : 'rgba(255,80,80,0.85)';
        ctx.fillText(`${itemNum}:${resp || '?'}`, cx + 4, cy + 16);
      }
    }
  }

  // ─── API pública ──────────────────────────────────────────────────────────────

  /**
   * procesarExamen — función principal.
   *
   * @param {File}              file          Imagen del examen
   * @param {HTMLCanvasElement} canvasPreview Canvas de preview (opcional, recibe overlay debug)
   * @returns {Promise<{respuestas, confianza, itemsDudosos, totalDetectados, error}>}
   */
  async function procesarExamen(file, canvasPreview = null) {
    try {
      const img = await loadImage(file);

      // Crear canvas de trabajo normalizado
      const canvas = document.createElement('canvas');
      canvas.width = CFG.W;
      canvas.height = CFG.H;
      const ctx = canvas.getContext('2d');
      ctx.drawImage(img, 0, 0, CFG.W, CFG.H);
      URL.revokeObjectURL(img.src);

      // Mostrar imagen en preview (sin procesar)
      if (canvasPreview) {
        canvasPreview.width = CFG.W;
        canvasPreview.height = CFG.H;
        canvasPreview.getContext('2d').drawImage(canvas, 0, 0);
      }

      const imageData = ctx.getImageData(0, 0, CFG.W, CFG.H);

      // Pipeline de procesamiento
      const gray = rgb2gray(imageData);
      const enhanced = localContrastEnhance(gray, CFG.W, CFG.H);
      const thresh = otsuThreshold(enhanced);
      const binary = binarize(enhanced, thresh);

      console.log('[OMR] Umbral Otsu:', thresh);

      // Detectar tabla
      const table = detectTable(binary, CFG.W, CFG.H);
      console.log('[OMR] Tabla detectada:', table);

      // Analizar grilla fija (ítems 1-9)
      const { respuestas: resp1_9, confianza: conf1_9 } = analyzeFixedGrid(binary, CFG.W, table);

      // Analizar sección docente (ítems 10-12)
      const { respuestas: resp10_12, confianza: conf10_12 } = analyzeTeacherSection(binary, CFG.W, CFG.H, table);

      const respuestas = { ...resp1_9, ...resp10_12 };
      const confianza  = { ...conf1_9, ...conf10_12 };

      // Asegurar que todos los ítems existen
      for (let i = 1; i <= CFG.ITEMS; i++) {
        if (!(i in respuestas)) { respuestas[i] = ''; confianza[i] = 0; }
      }

      // Debug overlay
      if (canvasPreview) {
        drawDebugOverlay(canvasPreview, table, respuestas, confianza);
      }

      const itemsDudosos = Object.entries(confianza)
        .filter(([, v]) => v < CFG.CONF_LOW)
        .map(([k]) => parseInt(k));

      const totalDetectados = Object.values(respuestas).filter(Boolean).length;

      return { respuestas, confianza, itemsDudosos, totalDetectados, error: null };

    } catch (err) {
      console.error('[OMR] Error crítico:', err);
      const respuestas = {}, confianza = {};
      for (let i = 1; i <= 12; i++) { respuestas[i] = ''; confianza[i] = 0; }
      return {
        respuestas, confianza,
        itemsDudosos: Array.from({ length: 12 }, (_, i) => i + 1),
        totalDetectados: 0,
        error: err.message,
      };
    }
  }

  return { procesarExamen, CFG };
})();

// CommonJS compat
if (typeof module !== 'undefined' && module.exports) {
  module.exports = OMRProcessor;
}
