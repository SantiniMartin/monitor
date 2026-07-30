/**
 * omr_processor.js — v4 Backend API Client
 *
 * El procesamiento pesado (OpenCV) corre en el servidor Django.
 * Este archivo solo:
 *   1. Envía la imagen al endpoint /omr/procesar-imagen/ via FormData
 *   2. Recibe el JSON con las respuestas detectadas
 *   3. Si el backend no tiene OpenCV instalado, avisa al usuario
 *
 * NO hay librerías externas. NO hay WASM. NO hay tiempos de carga.
 * La página carga al instante.
 */

'use strict';

const OMRProcessor = (() => {

  // URL del endpoint — se setea desde el template Django
  let _apiUrl  = null;
  let _csrfToken = null;

  /**
   * Inicializa el procesador con la URL del endpoint y el CSRF token.
   * Debe llamarse desde el template antes de cualquier llamada a procesarExamen().
   *
   * @param {string} apiUrl      URL del endpoint /omr/procesar-imagen/
   * @param {string} csrfToken   Django CSRF token
   */
  function init(apiUrl, csrfToken) {
    _apiUrl     = apiUrl;
    _csrfToken  = csrfToken;
  }

  /**
   * Muestra la imagen en el canvas de preview.
   * @param {File}              file
   * @param {HTMLCanvasElement} canvasPreview
   */
  function mostrarPreview(file, canvasPreview) {
    return new Promise((resolve, reject) => {
      const url = URL.createObjectURL(file);
      const img = new Image();
      img.onload = () => {
        canvasPreview.width  = img.naturalWidth;
        canvasPreview.height = img.naturalHeight;
        canvasPreview.getContext('2d').drawImage(img, 0, 0);
        URL.revokeObjectURL(url);
        resolve();
      };
      img.onerror = reject;
      img.src = url;
    });
  }

  /**
   * Envía la imagen al backend Django para procesamiento OMR.
   *
   * @param {File}              file           Imagen del examen
   * @param {HTMLCanvasElement} canvasPreview  Canvas para mostrar la imagen (opcional)
   *
   * @returns {Promise<{respuestas, confianza, itemsDudosos, totalDetectados, error, used_warp}>}
   */
  async function procesarExamen(file, canvasPreview = null) {
    if (!_apiUrl) {
      console.error('[OMR] init() no fue llamado. Falta _apiUrl.');
      return _errorResult('Configuración faltante en OMRProcessor.init()');
    }

    // Mostrar preview inmediato de la imagen sin procesar
    if (canvasPreview) {
      try { await mostrarPreview(file, canvasPreview); } catch (_) {}
    }

    // Preparar FormData
    const formData = new FormData();
    formData.append('imagen', file);

    try {
      const response = await fetch(_apiUrl, {
        method: 'POST',
        headers: { 'X-CSRFToken': _csrfToken },
        body: formData,
      });

      const data = await response.json();

      if (!data.ok) {
        // Backend sin opencv instalado
        if (data.cv_not_installed) {
          alert('ATENCIÓN: El servidor no tiene OpenCV instalado.\n\nPara que el escáner funcione, abrí una terminal y ejecutá:\npip install opencv-python-headless numpy');
          return _errorResult('El servidor no tiene OpenCV instalado.');
        }
        alert('Error en el servidor: ' + (data.error || 'Desconocido'));
        return _errorResult(data.error || 'Error desconocido en el servidor');
      }

      // Normalizar claves de respuestas/confianza a enteros
      const respuestas = {};
      const confianza  = {};
      for (let i = 1; i <= 12; i++) {
        respuestas[i] = data.respuestas[String(i)] ?? '';
        confianza[i]  = data.confianza[String(i)]  ?? 0;
      }

      const itemsDudosos    = (data.items_dudosos || []).map(Number);
      const totalDetectados = Object.values(respuestas).filter(Boolean).length;

      // Overlay de debug: marcar las celdas detectadas sobre el preview
      if (canvasPreview && canvasPreview.width > 0) {
        _drawOverlay(canvasPreview, respuestas, confianza, data.used_warp);
      }

      return {
        respuestas,
        confianza,
        itemsDudosos,
        totalDetectados,
        used_warp: data.used_warp,
        error: null,
      };

    } catch (err) {
      console.error('[OMR] Error de red o parsing:', err);
      alert('Error crítico de red o de código al procesar la imagen: ' + err.message);
      return _errorResult(`Error de red: ${err.message}`);
    }
  }

  // ── Helpers privados ────────────────────────────────────────────────────────

  function _errorResult(message) {
    const respuestas = {}, confianza = {};
    for (let i = 1; i <= 12; i++) { respuestas[i] = ''; confianza[i] = 0; }
    return {
      respuestas,
      confianza,
      itemsDudosos: Array.from({ length: 12 }, (_, i) => i + 1),
      totalDetectados: 0,
      used_warp: false,
      error: message,
    };
  }

  /**
   * Dibuja un overlay de debug sobre el canvas de preview.
   * Muestra la grilla 3×3 con etiquetas de los ítems detectados.
   * Si el backend aplicó corrección de perspectiva (used_warp = true),
   * la imagen en el canvas ya está rectificada, así que la grilla
   * se dibuja directamente encima.
   */
  function _drawOverlay(canvas, respuestas, confianza, usedWarp) {
    const ctx  = canvas.getContext('2d');
    const W    = canvas.width;
    const H    = canvas.height;
    const COLS = 3, ROWS = 3, CONF_LOW = 40;

    // Si la imagen fue rectificada, la grilla cubre todo el canvas
    // Si no (fallback), la grilla es la región heurística (04% → 96% × 28% → 70%)
    let gx = 0, gy = 0, gw = W, gh = H;
    if (!usedWarp) {
      gx = W * 0.04; gy = H * 0.28;
      gw = W * 0.92; gh = H * 0.42;
      // Dibujar aviso de que no se corrigió perspectiva
      ctx.fillStyle = 'rgba(255, 165, 0, 0.85)';
      ctx.font = 'bold 13px sans-serif';
      ctx.fillText('⚠ Sin corrección de perspectiva — usá bounds heurísticos', gx, gy - 8);
      ctx.strokeStyle = 'rgba(255, 165, 0, 0.7)';
      ctx.lineWidth = 2;
      ctx.strokeRect(gx, gy, gw, gh);
    } else {
      // Borde verde = perspectiva corregida OK
      ctx.strokeStyle = 'rgba(0, 255, 100, 0.6)';
      ctx.lineWidth = 2;
      ctx.strokeRect(1, 1, W - 2, H - 2);
    }

    const cellW = gw / COLS;
    const cellH = gh / ROWS;

    for (let row = 0; row < ROWS; row++) {
      for (let col = 0; col < COLS; col++) {
        const itemNum = row * COLS + col + 1;
        const cx = gx + col * cellW;
        const cy = gy + row * cellH;
        const resp = respuestas[itemNum] || '';
        const conf = confianza[itemNum] ?? 0;
        const isDudoso = conf < CONF_LOW;

        // Borde de celda
        ctx.strokeStyle = 'rgba(0, 200, 255, 0.4)';
        ctx.lineWidth = 1;
        ctx.strokeRect(cx, cy, cellW, cellH);

        // Etiqueta del resultado
        const color = resp
          ? (isDudoso ? 'rgba(255,165,0,0.98)' : 'rgba(0,255,100,0.98)')
          : 'rgba(255,80,80,0.95)';
        ctx.fillStyle = color;
        ctx.font = `bold ${Math.round(cellW * 0.12)}px sans-serif`;
        ctx.fillText(`${itemNum}: ${resp || '?'}  (${conf}%)`, cx + 6, cy + 22);
      }
    }
  }

  return { init, procesarExamen };
})();

if (typeof module !== 'undefined' && module.exports) {
  module.exports = OMRProcessor;
}
