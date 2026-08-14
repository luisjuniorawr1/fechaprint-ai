export function loadImageFile(file) {
  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(file);
    const img = new Image();
    img.onload = () => resolve({ img, url, width: img.naturalWidth, height: img.naturalHeight });
    img.onerror = () => {
      URL.revokeObjectURL(url);
      reject(new Error('Não foi possível ler a imagem. O arquivo pode estar corrompido.'));
    };
    img.src = url;
  });
}

function clamp(n, min, max) {
  return Math.min(max, Math.max(min, n));
}

export function placementFor({ srcW, srcH, dstX = 0, dstY = 0, dstW, dstH, mode = 'fill', zoom = 1, panX = 0, panY = 0 }) {
  const baseScale = mode === 'fit'
    ? Math.min(dstW / srcW, dstH / srcH)
    : Math.max(dstW / srcW, dstH / srcH);
  const scale = baseScale * zoom;
  const drawW = srcW * scale;
  const drawH = srcH * scale;
  const freeX = Math.max(0, Math.abs(dstW - drawW));
  const freeY = Math.max(0, Math.abs(dstH - drawH));
  const centerX = dstX + (dstW - drawW) / 2;
  const centerY = dstY + (dstH - drawH) / 2;
  const shiftX = clamp(panX, -1, 1) * freeX / 2;
  const shiftY = clamp(panY, -1, 1) * freeY / 2;
  return { x: centerX + shiftX, y: centerY + shiftY, w: drawW, h: drawH, scale };
}

export function renderComposition(ctx, options) {
  const {
    image, width, height, trimRect = { x: 0, y: 0, w: width, h: height },
    mode = 'fill', zoom = 1, panX = 0, panY = 0,
    background = 'white', backgroundColor = '#ffffff', clip = true,
  } = options;

  ctx.save();
  if (clip) {
    ctx.beginPath();
    ctx.rect(0, 0, width, height);
    ctx.clip();
  }

  ctx.fillStyle = background === 'black' ? '#000000' : backgroundColor || '#ffffff';
  ctx.fillRect(0, 0, width, height);

  if (mode === 'fit' && background === 'blur') {
    const blurPlacement = placementFor({ srcW: image.naturalWidth, srcH: image.naturalHeight, dstW: width, dstH: height, mode: 'fill', zoom: 1 });
    ctx.save();
    ctx.filter = `blur(${Math.max(8, Math.round(Math.min(width, height) * 0.025))}px)`;
    ctx.globalAlpha = 0.92;
    ctx.drawImage(image, blurPlacement.x, blurPlacement.y, blurPlacement.w, blurPlacement.h);
    ctx.restore();
    ctx.fillStyle = 'rgba(0,0,0,.05)';
    ctx.fillRect(0, 0, width, height);
  }

  const targetRect = mode === 'fill' ? { x: 0, y: 0, w: width, h: height } : trimRect;
  const placement = placementFor({
    srcW: image.naturalWidth,
    srcH: image.naturalHeight,
    dstX: targetRect.x,
    dstY: targetRect.y,
    dstW: targetRect.w,
    dstH: targetRect.h,
    mode,
    zoom,
    panX,
    panY,
  });
  ctx.drawImage(image, placement.x, placement.y, placement.w, placement.h);
  ctx.restore();
  return placement;
}

export async function compositionToJpegBlob(options, quality = 0.92) {
  const canvas = document.createElement('canvas');
  canvas.width = options.width;
  canvas.height = options.height;
  const ctx = canvas.getContext('2d', { alpha: false });
  renderComposition(ctx, options);
  const blob = await new Promise((resolve) => canvas.toBlob(resolve, 'image/jpeg', quality));
  if (!blob) throw new Error('O navegador não conseguiu codificar a imagem final em JPEG.');
  return blob;
}
