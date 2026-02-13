// ================================================================
// Matrix Transform Studio - Web Version
// ================================================================

const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

// ================================================================
// State
// ================================================================

let originalImage = null;   // HTMLImageElement
let currentImageData = null; // ImageData (transformed result)

const matrices = {
  scale:    [[1,0],[0,1]],
  rotation: [[1,0],[0,1]],
  shear:    [[1,0],[0,1]],
};
let transformOrder = ['scale', 'rotation', 'shear'];
let combinedMatrix3x3 = [[1,0,0],[0,1,0],[0,0,1]];

// View
let viewZoom = 1.0;
let viewOffsetX = 0;
let viewOffsetY = 0;
let dragStartX = 0, dragStartY = 0;
let isDragging = false;
let suppressSlider = false;

// Canvas
const canvas = $('#preview');
const ctx = canvas.getContext('2d');

// ================================================================
// √ Parser
// ================================================================

function parseExpr(text) {
  text = text.trim();
  if (!text) return 0;
  // √N → Math.sqrt(N)
  text = text.replace(/√(\d+\.?\d*)/g, 'sqrt($1)');
  try {
    const fn = new Function('sqrt', 'pi', `"use strict"; return (${text});`);
    return fn(Math.sqrt, Math.PI);
  } catch (e) {
    throw new Error(`式の解析に失敗: "${text}"`);
  }
}

function formatVal(v) {
  if (Math.abs(v - Math.round(v)) < 1e-9) return String(Math.round(v));
  return v.toFixed(4);
}

// ================================================================
// Matrix math (3x3)
// ================================================================

function mat3x3Mul(a, b) {
  const r = [[0,0,0],[0,0,0],[0,0,0]];
  for (let i = 0; i < 3; i++)
    for (let j = 0; j < 3; j++)
      for (let k = 0; k < 3; k++)
        r[i][j] += a[i][k] * b[k][j];
  return r;
}

function mat2to3(m) {
  return [[m[0][0], m[0][1], 0],
          [m[1][0], m[1][1], 0],
          [0, 0, 1]];
}

// ================================================================
// Slider <-> Entry sync
// ================================================================

const sliderIds = {
  scale:    { sliders: ['scale-x','scale-y'], vals: ['scale-x-val','scale-y-val'] },
  rotation: { sliders: ['rotation'], vals: ['rotation-val'] },
  shear:    { sliders: ['shear-x','shear-y'], vals: ['shear-x-val','shear-y-val'] },
};

const entryIds = {
  scale:    [['s00','s01'],['s10','s11']],
  rotation: [['r00','r01'],['r10','r11']],
  shear:    [['h00','h01'],['h10','h11']],
};

function getEntryValues(key) {
  const ids = entryIds[key];
  return ids.map(row => row.map(id => parseExpr($('#'+id).value)));
}

function setEntryValues(key, m) {
  const ids = entryIds[key];
  for (let r = 0; r < 2; r++)
    for (let c = 0; c < 2; c++)
      $('#'+ids[r][c]).value = formatVal(m[r][c]);
}

function buildMatrixFromSliders(key) {
  if (key === 'scale') {
    const sx = parseFloat($('#scale-x').value);
    const sy = parseFloat($('#scale-y').value);
    return [[sx, 0], [0, sy]];
  } else if (key === 'rotation') {
    const deg = parseFloat($('#rotation').value);
    const a = deg * Math.PI / 180;
    return [[Math.cos(a), -Math.sin(a)], [Math.sin(a), Math.cos(a)]];
  } else {
    const hx = parseFloat($('#shear-x').value);
    const hy = parseFloat($('#shear-y').value);
    return [[1, hx], [hy, 1]];
  }
}

function syncSlidersFromMatrix(key, m) {
  suppressSlider = true;
  if (key === 'scale') {
    const sx = m[0][0], sy = m[1][1];
    if (sx >= 0.1 && sx <= 3) { $('#scale-x').value = sx; $('#scale-x-val').textContent = sx.toFixed(2); }
    if (sy >= 0.1 && sy <= 3) { $('#scale-y').value = sy; $('#scale-y-val').textContent = sy.toFixed(2); }
  } else if (key === 'rotation') {
    const angle = Math.atan2(m[1][0], m[0][0]) * 180 / Math.PI;
    if (angle >= -180 && angle <= 180) {
      $('#rotation').value = angle;
      $('#rotation-val').textContent = Math.round(angle);
    }
  } else {
    const hx = m[0][1], hy = m[1][0];
    if (hx >= -2 && hx <= 2) { $('#shear-x').value = hx; $('#shear-x-val').textContent = hx.toFixed(2); }
    if (hy >= -2 && hy <= 2) { $('#shear-y').value = hy; $('#shear-y-val').textContent = hy.toFixed(2); }
  }
  suppressSlider = false;
}

function updateSliderDisplay() {
  $('#scale-x-val').textContent = parseFloat($('#scale-x').value).toFixed(2);
  $('#scale-y-val').textContent = parseFloat($('#scale-y').value).toFixed(2);
  $('#rotation-val').textContent = Math.round(parseFloat($('#rotation').value));
  $('#shear-x-val').textContent = parseFloat($('#shear-x').value).toFixed(2);
  $('#shear-y-val').textContent = parseFloat($('#shear-y').value).toFixed(2);
}

// ================================================================
// Transform
// ================================================================

function computeOutputBounds(w, h, full) {
  const corners = [[0,0,1],[w,0,1],[w,h,1],[0,h,1]];
  let minX=Infinity, maxX=-Infinity, minY=Infinity, maxY=-Infinity;
  for (const c of corners) {
    const tx = full[0][0]*c[0] + full[0][1]*c[1] + full[0][2];
    const ty = full[1][0]*c[0] + full[1][1]*c[1] + full[1][2];
    minX = Math.min(minX, tx); maxX = Math.max(maxX, tx);
    minY = Math.min(minY, ty); maxY = Math.max(maxY, ty);
  }
  const pad = Math.max(w, h) * 0.25;
  minX -= pad; minY -= pad; maxX += pad; maxY += pad;
  return {
    outW: Math.ceil(maxX - minX),
    outH: Math.ceil(maxY - minY),
    minX, minY
  };
}

function applyTransform() {
  if (!originalImage) return;

  const w = originalImage.width;
  const h = originalImage.height;
  const cx = w / 2, cy = h / 2;

  // Build individual matrices from sliders
  for (const key of ['scale','rotation','shear']) {
    matrices[key] = buildMatrixFromSliders(key);
  }

  // Compose in order (center-based)
  const toOrigin   = [[1,0,-cx],[0,1,-cy],[0,0,1]];
  const fromOrigin  = [[1,0,cx],[0,1,cy],[0,0,1]];

  let combined = [[1,0,0],[0,1,0],[0,0,1]];
  for (const key of transformOrder) {
    combined = mat3x3Mul(mat2to3(matrices[key]), combined);
  }
  const full = mat3x3Mul(fromOrigin, mat3x3Mul(combined, toOrigin));

  const { outW, outH, minX, minY } = computeOutputBounds(w, h, full);
  const offset = [[1,0,-minX],[0,1,-minY],[0,0,1]];
  combinedMatrix3x3 = mat3x3Mul(offset, full);

  // Warp image using inverse mapping
  currentImageData = warpAffine(originalImage, combinedMatrix3x3, outW, outH);

  // Update UI
  updateAllEntries();
  updateCombinedMatrixDisplay();
  updateDisplay();
}

function applyFromMatrices() {
  if (!originalImage) return;

  const w = originalImage.width;
  const h = originalImage.height;
  const cx = w / 2, cy = h / 2;

  const toOrigin  = [[1,0,-cx],[0,1,-cy],[0,0,1]];
  const fromOrigin = [[1,0,cx],[0,1,cy],[0,0,1]];

  let combined = [[1,0,0],[0,1,0],[0,0,1]];
  for (const key of transformOrder) {
    combined = mat3x3Mul(mat2to3(matrices[key]), combined);
  }
  const full = mat3x3Mul(fromOrigin, mat3x3Mul(combined, toOrigin));

  const { outW, outH, minX, minY } = computeOutputBounds(w, h, full);
  const offset = [[1,0,-minX],[0,1,-minY],[0,0,1]];
  combinedMatrix3x3 = mat3x3Mul(offset, full);

  currentImageData = warpAffine(originalImage, combinedMatrix3x3, outW, outH);
  updateCombinedMatrixDisplay();
  updateDisplay();
}

// ================================================================
// Image warping (inverse mapping with bilinear interpolation)
// ================================================================

function invertMatrix3x3(m) {
  const [[a,b,c],[d,e,f]] = m;
  // Only need 2x2 + translation inverse for affine
  const det = a*e - b*d;
  if (Math.abs(det) < 1e-12) return null;
  const invDet = 1/det;
  return [
    [ e*invDet, -b*invDet, (b*f - c*e)*invDet],
    [-d*invDet,  a*invDet, (c*d - a*f)*invDet],
    [0, 0, 1]
  ];
}

function warpAffine(img, mat, outW, outH) {
  // Draw original image to get pixel data
  const srcCanvas = document.createElement('canvas');
  srcCanvas.width = img.width;
  srcCanvas.height = img.height;
  const srcCtx = srcCanvas.getContext('2d');
  srcCtx.drawImage(img, 0, 0);
  const srcData = srcCtx.getImageData(0, 0, img.width, img.height);
  const src = srcData.data;
  const sw = img.width, sh = img.height;

  const dstCanvas = document.createElement('canvas');
  dstCanvas.width = outW;
  dstCanvas.height = outH;
  const dstCtx = dstCanvas.getContext('2d');
  const dstImageData = dstCtx.createImageData(outW, outH);
  const dst = dstImageData.data;

  // Fill with transparent
  for (let i = 0; i < dst.length; i += 4) {
    dst[i] = 0; dst[i+1] = 0; dst[i+2] = 0; dst[i+3] = 0;
  }

  const inv = invertMatrix3x3(mat);
  if (!inv) return dstImageData;

  const [ia, ib, ic] = inv[0];
  const [id, ie, iif] = inv[1];

  for (let dy = 0; dy < outH; dy++) {
    for (let dx = 0; dx < outW; dx++) {
      const sx = ia * dx + ib * dy + ic;
      const sy = id * dx + ie * dy + iif;

      // Bilinear interpolation
      const x0 = Math.floor(sx), y0 = Math.floor(sy);
      if (x0 < 0 || x0 >= sw - 1 || y0 < 0 || y0 >= sh - 1) continue;

      const fx = sx - x0, fy = sy - y0;
      const i00 = (y0 * sw + x0) * 4;
      const i10 = i00 + 4;
      const i01 = ((y0+1) * sw + x0) * 4;
      const i11 = i01 + 4;

      const dstIdx = (dy * outW + dx) * 4;
      for (let ch = 0; ch < 4; ch++) {
        const v = src[i00+ch]*(1-fx)*(1-fy) +
                  src[i10+ch]*fx*(1-fy) +
                  src[i01+ch]*(1-fx)*fy +
                  src[i11+ch]*fx*fy;
        dst[dstIdx+ch] = Math.round(v);
      }
    }
  }

  // Store canvas for later use
  dstCtx.putImageData(dstImageData, 0, 0);
  dstCanvas._outW = outW;
  dstCanvas._outH = outH;
  currentImageData = dstCanvas;
  return dstCanvas;
}

// ================================================================
// Display
// ================================================================

function resizeCanvas() {
  const wrap = $('.canvas-wrap');
  canvas.width = wrap.clientWidth;
  canvas.height = wrap.clientHeight;
  updateDisplay();
}

function updateDisplay() {
  if (!currentImageData) {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.fillStyle = '#1e1e1e';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.fillStyle = '#666';
    ctx.font = '18px Arial';
    ctx.textAlign = 'center';
    ctx.fillText('画像を開いてください', canvas.width/2, canvas.height/2 - 10);
    ctx.font = '13px Arial';
    ctx.fillText('左のパネルから画像を開く', canvas.width/2, canvas.height/2 + 16);
    return;
  }

  const cw = canvas.width, ch = canvas.height;
  ctx.clearRect(0, 0, cw, ch);
  ctx.fillStyle = '#1e1e1e';
  ctx.fillRect(0, 0, cw, ch);

  // Grid
  if ($('#show-grid').checked) drawGrid(cw, ch);

  const iw = currentImageData._outW || currentImageData.width;
  const ih = currentImageData._outH || currentImageData.height;

  // Base scale from original image dimensions
  const ow = originalImage.width, oh = originalImage.height;
  const baseScale = Math.min(cw / ow, ch / oh, 1.0) * 0.85;
  const finalScale = baseScale * viewZoom;

  const nw = Math.max(Math.round(iw * finalScale), 1);
  const nh = Math.max(Math.round(ih * finalScale), 1);

  const x = Math.round((cw - nw) / 2 + viewOffsetX);
  const y = Math.round((ch - nh) / 2 + viewOffsetY);

  ctx.drawImage(currentImageData, 0, 0, iw, ih, x, y, nw, nh);

  $('#zoom-label').textContent = Math.round(viewZoom * 100) + '%';
}

function drawGrid(w, h) {
  ctx.strokeStyle = '#333';
  ctx.lineWidth = 1;
  for (let x = 0; x < w; x += 50) {
    ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, h); ctx.stroke();
  }
  for (let y = 0; y < h; y += 50) {
    ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke();
  }
  ctx.strokeStyle = '#4CAF50';
  ctx.lineWidth = 2;
  ctx.setLineDash([5, 5]);
  ctx.beginPath(); ctx.moveTo(w/2, 0); ctx.lineTo(w/2, h); ctx.stroke();
  ctx.beginPath(); ctx.moveTo(0, h/2); ctx.lineTo(w, h/2); ctx.stroke();
  ctx.setLineDash([]);
}

// ================================================================
// UI Updates
// ================================================================

function updateAllEntries() {
  for (const key of ['scale','rotation','shear']) {
    setEntryValues(key, matrices[key]);
  }
}

function updateCombinedMatrixDisplay() {
  const m = combinedMatrix3x3;
  const lines = [
    '[',
    '  ' + [m[0][0], m[0][1], m[0][2]].map(v => v.toFixed(3).padStart(9)).join('  '),
    '  ' + [m[1][0], m[1][1], m[1][2]].map(v => v.toFixed(3).padStart(9)).join('  '),
    ']'
  ];
  $('#combined-matrix').value = lines.join('\n');
}

function buildOrderUI() {
  const list = $('#order-list');
  list.innerHTML = '';
  const names = {
    scale:    { label: '[S] スケール', cls: 'color-scale' },
    rotation: { label: '[R] 回転',     cls: 'color-rotation' },
    shear:    { label: '[H] シアー',   cls: 'color-shear' },
  };

  transformOrder.forEach((key, i) => {
    const row = document.createElement('div');
    row.className = 'order-row';

    const num = document.createElement('span');
    num.className = 'order-num';
    num.textContent = (i + 1) + '.';

    const name = document.createElement('span');
    name.className = 'order-name ' + names[key].cls;
    name.textContent = names[key].label;

    const btns = document.createElement('div');
    btns.className = 'order-btns';

    const upBtn = document.createElement('button');
    upBtn.className = 'order-btn' + (i === 0 ? ' invisible' : '');
    upBtn.textContent = '▲';
    upBtn.onclick = () => moveOrder(i, -1);

    const downBtn = document.createElement('button');
    downBtn.className = 'order-btn' + (i === transformOrder.length - 1 ? ' invisible' : '');
    downBtn.textContent = '▼';
    downBtn.onclick = () => moveOrder(i, 1);

    btns.appendChild(upBtn);
    btns.appendChild(downBtn);
    row.appendChild(num);
    row.appendChild(name);
    row.appendChild(btns);
    list.appendChild(row);
  });
}

function moveOrder(index, direction) {
  const newIndex = index + direction;
  if (newIndex < 0 || newIndex >= transformOrder.length) return;
  [transformOrder[index], transformOrder[newIndex]] =
    [transformOrder[newIndex], transformOrder[index]];
  buildOrderUI();
  if (originalImage) applyTransform();
}

// ================================================================
// Events
// ================================================================

function setupEvents() {
  // File open
  $('#btn-open').onclick = () => $('#file-input').click();
  $('#file-input').onchange = (e) => {
    const file = e.target.files[0];
    if (!file) return;
    const img = new Image();
    img.onload = () => {
      originalImage = img;
      resetAll();
    };
    img.src = URL.createObjectURL(file);
  };

  // File save
  $('#btn-save').onclick = () => {
    if (!currentImageData) { alert('保存する画像がありません'); return; }
    const link = document.createElement('a');
    link.download = 'transformed.png';
    link.href = currentImageData.toDataURL('image/png');
    link.click();
  };

  // Sliders
  for (const id of ['scale-x','scale-y','rotation','shear-x','shear-y']) {
    $('#'+id).oninput = () => {
      if (suppressSlider) return;
      updateSliderDisplay();
      if (originalImage) applyTransform();
    };
  }

  // Presets
  $$('.btn-preset').forEach(btn => {
    btn.onclick = () => {
      const angle = parseInt(btn.dataset.angle);
      $('#rotation').value = angle > 180 ? angle - 360 : angle;
      updateSliderDisplay();
      if (originalImage) applyTransform();
    };
  });

  // Matrix apply buttons
  $$('.btn-apply').forEach(btn => {
    btn.onclick = () => {
      const key = btn.dataset.key;
      try {
        matrices[key] = getEntryValues(key);
        syncSlidersFromMatrix(key, matrices[key]);
        applyFromMatrices();
      } catch (e) {
        alert('行列の解析に失敗:\n' + e.message);
      }
    };
  });

  // Combined matrix apply
  $('#btn-apply-combined').onclick = () => {
    try {
      const txt = $('#combined-matrix').value;
      const lines = txt.trim().replace(/[\[\]]/g, '').split('\n').map(l => l.trim()).filter(l => l);
      if (lines.length !== 2) throw new Error('2行3列の行列を入力してください');
      const vals = lines.map(l => {
        const v = l.split(/\s+/).map(Number);
        if (v.length !== 3 || v.some(isNaN)) throw new Error('各行は3つの数値が必要です');
        return v;
      });
      const custom = [vals[0], vals[1], [0,0,1]];
      if (!originalImage) return;

      const w = originalImage.width, h = originalImage.height;
      const { outW, outH, minX, minY } = computeOutputBounds(w, h, custom);
      const offset = [[1,0,-minX],[0,1,-minY],[0,0,1]];
      combinedMatrix3x3 = mat3x3Mul(offset, custom);
      currentImageData = warpAffine(originalImage, combinedMatrix3x3, outW, outH);
      updateDisplay();
    } catch (e) {
      alert('行列適用失敗:\n' + e.message);
    }
  };

  // Reset
  $('#btn-reset').onclick = resetAll;

  // Grid toggle
  $('#show-grid').onchange = () => updateDisplay();

  // Zoom buttons
  $('#btn-zoom-in').onclick = () => { setZoomLevel(viewZoom * 1.25); };
  $('#btn-zoom-out').onclick = () => { setZoomLevel(viewZoom * 0.8); };
  $('#btn-fit').onclick = resetView;
  $$('.btn-pct').forEach(btn => {
    btn.onclick = () => {
      viewZoom = parseFloat(btn.dataset.zoom);
      viewOffsetX = 0; viewOffsetY = 0;
      updateDisplay();
    };
  });

  // Canvas pan/zoom
  canvas.addEventListener('mousedown', (e) => {
    if (e.button === 0) { isDragging = true; dragStartX = e.clientX; dragStartY = e.clientY; }
  });
  canvas.addEventListener('mousemove', (e) => {
    if (!isDragging || !currentImageData) return;
    viewOffsetX += e.clientX - dragStartX;
    viewOffsetY += e.clientY - dragStartY;
    dragStartX = e.clientX; dragStartY = e.clientY;
    updateDisplay();
  });
  canvas.addEventListener('mouseup', () => { isDragging = false; });
  canvas.addEventListener('mouseleave', () => { isDragging = false; });

  canvas.addEventListener('wheel', (e) => {
    e.preventDefault();
    if (!currentImageData) return;
    const factor = e.deltaY < 0 ? 1.05 : 0.95;
    setZoomLevel(viewZoom * factor);
  }, { passive: false });

  canvas.addEventListener('contextmenu', (e) => {
    e.preventDefault();
    resetView();
  });

  // Resize
  window.addEventListener('resize', resizeCanvas);
}

function setZoomLevel(z) {
  if (z >= 0.1 && z <= 10) {
    viewZoom = z;
    updateDisplay();
  }
}

function resetView() {
  viewOffsetX = 0; viewOffsetY = 0; viewZoom = 1.0;
  updateDisplay();
}

function resetAll() {
  $('#scale-x').value = 1; $('#scale-y').value = 1;
  $('#rotation').value = 0;
  $('#shear-x').value = 0; $('#shear-y').value = 0;
  updateSliderDisplay();

  transformOrder = ['scale', 'rotation', 'shear'];
  buildOrderUI();

  for (const key of ['scale','rotation','shear']) {
    matrices[key] = [[1,0],[0,1]];
  }
  combinedMatrix3x3 = [[1,0,0],[0,1,0],[0,0,1]];

  updateAllEntries();
  updateCombinedMatrixDisplay();

  if (originalImage) {
    // Reset current image to original
    const c = document.createElement('canvas');
    c.width = originalImage.width;
    c.height = originalImage.height;
    c._outW = c.width; c._outH = c.height;
    const cctx = c.getContext('2d');
    cctx.drawImage(originalImage, 0, 0);
    currentImageData = c;

    resetView();
  }
}

// ================================================================
// Init
// ================================================================

function init() {
  setupEvents();
  buildOrderUI();
  updateCombinedMatrixDisplay();
  resizeCanvas();
}

init();
