/** Cliente liviano para el procesamiento OMR en Django. */
'use strict';

const OMRProcessor = (() => {
  const MAX_FILE_BYTES = 12 * 1024 * 1024;
  const MAX_IMAGE_SIDE = 1800;
  const JPEG_QUALITY = 0.85;
  let apiUrl = null;
  let csrfToken = null;

  class OMRClientError extends Error {
    constructor(message, code = 'PROCESSING_ERROR') {
      super(message);
      this.name = 'OMRClientError';
      this.code = code;
    }
  }

  function init(url, token) {
    apiUrl = url;
    csrfToken = token;
  }

  function canvasToBlob(canvas) {
    return new Promise((resolve, reject) => {
      canvas.toBlob(
        blob => blob ? resolve(blob) : reject(new OMRClientError('No se pudo preparar la imagen.', 'INVALID_IMAGE')),
        'image/jpeg',
        JPEG_QUALITY,
      );
    });
  }

  async function prepararImagen(file, canvasPreview) {
    if (!(file instanceof Blob) || file.size === 0) {
      throw new OMRClientError('Seleccioná una imagen válida.', 'INVALID_IMAGE');
    }
    if (file.size > MAX_FILE_BYTES) {
      throw new OMRClientError('La imagen es demasiado grande. El límite es 12 MB.', 'IMAGE_TOO_LARGE');
    }

    const objectUrl = URL.createObjectURL(file);
    const image = new Image();
    try {
      await new Promise((resolve, reject) => {
        image.onload = resolve;
        image.onerror = () => reject(new OMRClientError('El archivo no es una imagen válida.', 'INVALID_IMAGE'));
        image.src = objectUrl;
      });
      if (image.naturalWidth * image.naturalHeight > 25_000_000) {
        throw new OMRClientError('La imagen tiene dimensiones demasiado grandes.', 'IMAGE_TOO_LARGE');
      }

      const largestSide = Math.max(image.naturalWidth, image.naturalHeight);
      const scale = Math.min(1, MAX_IMAGE_SIDE / largestSide);
      const width = Math.max(1, Math.round(image.naturalWidth * scale));
      const height = Math.max(1, Math.round(image.naturalHeight * scale));
      const workCanvas = document.createElement('canvas');
      workCanvas.width = width;
      workCanvas.height = height;
      workCanvas.getContext('2d', { alpha: false }).drawImage(image, 0, 0, width, height);

      if (canvasPreview) {
        canvasPreview.width = width;
        canvasPreview.height = height;
        canvasPreview.getContext('2d', { alpha: false }).drawImage(workCanvas, 0, 0);
      }

      const blob = await canvasToBlob(workCanvas);
      workCanvas.width = 1;
      workCanvas.height = 1;
      return new File([blob], 'examen-omr.jpg', { type: 'image/jpeg' });
    } finally {
      image.src = '';
      URL.revokeObjectURL(objectUrl);
    }
  }

  async function procesarExamen(file, canvasPreview = null, options = {}) {
    if (!apiUrl) {
      throw new OMRClientError('El lector no está configurado correctamente.', 'CONFIGURATION_ERROR');
    }

    const imagenOptimizada = await prepararImagen(file, canvasPreview);
    const formData = new FormData();
    formData.append('imagen', imagenOptimizada);
    formData.append('tipo_examen', options.tipoExamen || 'lengua');

    let response;
    try {
      response = await fetch(apiUrl, {
        method: 'POST',
        headers: { 'X-CSRFToken': csrfToken },
        body: formData,
        signal: options.signal,
      });
    } catch (error) {
      if (error.name === 'AbortError') throw error;
      throw new OMRClientError('No se pudo conectar con el servidor. Revisá la conexión.', 'NETWORK_ERROR');
    }

    let data;
    try {
      data = await response.json();
    } catch (_) {
      throw new OMRClientError('El servidor devolvió una respuesta inválida.', 'SERVER_ERROR');
    }
    if (!response.ok || !data.ok) {
      throw new OMRClientError(data.error || 'No se pudo analizar la imagen.', data.code || 'PROCESSING_ERROR');
    }

    const respuestas = {};
    const confianza = {};
    const cantidadItems = Number(options.cantidadItems) || 12;
    for (let item = 1; item <= cantidadItems; item++) {
      respuestas[item] = data.respuestas?.[String(item)] || '';
      confianza[item] = Number(data.confianza?.[String(item)] || 0);
    }

    return {
      respuestas,
      confianza,
      itemsDudosos: (data.items_dudosos || []).map(Number),
      used_warp: Boolean(data.used_warp),
      detection_method: data.detection_method || '',
      detection_score: data.detection_score || 0,
    };
  }

  return { init, procesarExamen, OMRClientError };
})();

if (typeof module !== 'undefined' && module.exports) module.exports = OMRProcessor;
