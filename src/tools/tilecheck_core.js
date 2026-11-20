// Tile-budget check for Lufia II battle backgrounds. Port of seasons_prep.sky() + bbg_floor.floor_mask().
// Pure functions on Float32Array RGB (H*W*3); shared by the page and the node validation script.
const W = 256, H = 224, TILE_BUDGET = 426;

function boxResize(src, sw, sh, dw, dh) {          // area-weighted downscale (PIL BOX)
  const tmp = new Float32Array(dw * sh * 3), out = new Float32Array(dw * dh * 3);
  const sx = sw / dw, sy = sh / dh;
  for (let x = 0; x < dw; x++) {
    const x0 = x * sx, x1 = x0 + sx;
    for (let i = Math.floor(x0); i < Math.min(sw, Math.ceil(x1)); i++) {
      const w = Math.min(i + 1, x1) - Math.max(i, x0);
      if (w <= 0) continue;
      for (let y = 0; y < sh; y++) {
        const s = (y * sw + i) * 3, d = (y * dw + x) * 3;
        tmp[d] += src[s] * w; tmp[d + 1] += src[s + 1] * w; tmp[d + 2] += src[s + 2] * w;
      }
    }
  }
  for (let y = 0; y < dh; y++) {
    const y0 = y * sy, y1 = y0 + sy;
    for (let j = Math.floor(y0); j < Math.min(sh, Math.ceil(y1)); j++) {
      const w = Math.min(j + 1, y1) - Math.max(j, y0);
      if (w <= 0) continue;
      for (let x = 0; x < dw; x++) {
        const s = (j * dw + x) * 3, d = (y * dw + x) * 3;
        out[d] += tmp[s] * w; out[d + 1] += tmp[s + 1] * w; out[d + 2] += tmp[s + 2] * w;
      }
    }
  }
  const area = sx * sy;
  for (let k = 0; k < out.length; k++) out[k] = Math.round(out[k] / area);
  return out;
}

// scipy 'reflect' boundary: d c b a | a b c d | d c b a
const refl = (i, n) => { while (i < 0 || i >= n) i = i < 0 ? -i - 1 : 2 * n - i - 1; return i; };

function uniform(a, size) {                         // ndimage.uniform_filter(a, (size, size, 1))
  const r = (size - 1) >> 1, tmp = new Float32Array(a.length), out = new Float32Array(a.length);
  for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) for (let c = 0; c < 3; c++) {
    let s = 0; for (let k = -r; k < size - r; k++) s += a[(y * W + refl(x + k, W)) * 3 + c];
    tmp[(y * W + x) * 3 + c] = s / size;
  }
  for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) for (let c = 0; c < 3; c++) {
    let s = 0; for (let k = -r; k < size - r; k++) s += tmp[(refl(y + k, H) * W + x) * 3 + c];
    out[(y * W + x) * 3 + c] = s / size;
  }
  return out;
}

function label(m) {                                 // 4-connected components; returns [labels, sizes]
  const lab = new Int32Array(W * H), sizes = [0], stack = [];
  let n = 0;
  for (let p = 0; p < W * H; p++) {
    if (!m[p] || lab[p]) continue;
    n++; let size = 0; lab[p] = n; stack.push(p);
    while (stack.length) {
      const q = stack.pop(); size++;
      const y = (q / W) | 0, x = q - y * W;
      const nb = [x > 0 ? q - 1 : -1, x < W - 1 ? q + 1 : -1, y > 0 ? q - W : -1, y < H - 1 ? q + W : -1];
      for (const r of nb) if (r >= 0 && m[r] && !lab[r]) { lab[r] = n; stack.push(r); }
    }
    sizes.push(size);
  }
  return [lab, sizes];
}

function keepTouchingRow(m, row) {
  const [lab] = label(m), keep = new Set();
  for (let x = 0; x < W; x++) if (lab[row * W + x]) keep.add(lab[row * W + x]);
  const out = new Uint8Array(W * H);
  for (let p = 0; p < W * H; p++) out[p] = keep.has(lab[p]) ? 1 : 0;
  return out;
}

function morph(m, erode, cross) {                   // 3x3 square or cross; outside counts as 0
  const out = new Uint8Array(W * H);
  for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
    let v = erode ? 1 : 0;
    for (let dy = -1; dy <= 1; dy++) for (let dx = -1; dx <= 1; dx++) {
      if (cross && dx && dy) continue;
      const yy = y + dy, xx = x + dx;
      const b = yy >= 0 && yy < H && xx >= 0 && xx < W ? m[yy * W + xx] : 0;
      if (erode && !b) v = 0; if (!erode && b) v = 1;
    }
    out[y * W + x] = v;
  }
  return out;
}
const opening = m => morph(morph(m, true, false), false, false);

function median(v) { v.sort((p, q) => p - q); const n = v.length; return n % 2 ? v[n >> 1] : (v[n / 2 - 1] + v[n / 2]) / 2; }

function skyMask(a, hmax = 100, tol = 30) {
  const sm = uniform(a, 3), cand = new Uint8Array(W * H);
  for (let y = 0; y < hmax; y++) for (let x = 0; x < W; x++) {
    const p = (y * W + x) * 3, py = (Math.max(0, y - 1) * W + x) * 3, px = (y * W + Math.max(0, x - 1)) * 3;
    let g = 0; for (let c = 0; c < 3; c++) g += Math.abs(sm[p + c] - sm[py + c]) + Math.abs(sm[p + c] - sm[px + c]);
    cand[y * W + x] = g < 18 ? 1 : 0;
  }
  const top = keepTouchingRow(cand, 0);
  const ref = [], ok = [];
  for (let y = 0; y < hmax; y++) {
    const ch = [[], [], []];
    for (let x = 0; x < W; x++) if (top[y * W + x]) for (let c = 0; c < 3; c++) ch[c].push(a[(y * W + x) * 3 + c]);
    if (ch[0].length >= 16) { ref[y] = ch.map(median); ok.push(y); }
  }
  const m = new Uint8Array(W * H);
  if (!ok.length) return m;
  const ymax = ok[ok.length - 1];
  for (let y = 0; y < hmax; y++) {                  // np.interp: linear, clamped at the ends
    if (!ref[y]) {
      let i = 0; while (i < ok.length && ok[i] < y) i++;
      if (i === 0) ref[y] = ref[ok[0]]; else if (i === ok.length) ref[y] = ref[ok[ok.length - 1]];
      else { const y0 = ok[i - 1], y1 = ok[i], t = (y - y0) / (y1 - y0); ref[y] = ref[y0].map((v, c) => v + (ref[y1][c] - v) * t); }
    }
    if (y > ymax) continue;
    for (let x = 0; x < W; x++) {
      const p = (y * W + x) * 3;
      const d = Math.hypot(a[p] - ref[y][0], a[p + 1] - ref[y][1], a[p + 2] - ref[y][2]);
      m[y * W + x] = d < tol ? 1 : 0;
    }
  }
  const mt = keepTouchingRow(m, 0);
  const k = morph(keepTouchingRow(opening(mt), 0), false, true);
  for (let p = 0; p < W * H; p++) mt[p] = mt[p] && k[p] ? 1 : 0;
  return mt;
}

function inv3(m) {
  const [a, b, c, d, e, f, g, h, i] = m;
  const A = e * i - f * h, B = -(d * i - f * g), C = d * h - e * g;
  const det = a * A + b * B + c * C;
  return [A, -(b * i - c * h), b * f - c * e, B, a * i - c * g, -(a * f - c * d), C, -(a * h - b * g), a * e - b * d].map(v => v / det);
}

function floorMask(a, sample = [150, 205, 32, 224], minRow = 96, thr = 3, minObj = 40, anchor = 160, low = [128, 400], dropBelow = 168) {
  const sm = uniform(a, 5), [y0, y1, x0, x1] = sample;
  const mu = [0, 0, 0]; let n = 0;
  for (let y = y0; y < y1; y++) for (let x = x0; x < x1; x++) { const p = (y * W + x) * 3; for (let c = 0; c < 3; c++) mu[c] += sm[p + c]; n++; }
  for (let c = 0; c < 3; c++) mu[c] /= n;
  const cov = new Array(9).fill(0);
  for (let y = y0; y < y1; y++) for (let x = x0; x < x1; x++) {
    const p = (y * W + x) * 3;
    for (let r = 0; r < 3; r++) for (let c = 0; c < 3; c++) cov[r * 3 + c] += (sm[p + r] - mu[r]) * (sm[p + c] - mu[c]);
  }
  for (let k = 0; k < 9; k++) cov[k] = cov[k] / (n - 1) + (k % 4 === 0 ? 4 : 0);
  const iv = inv3(cov);
  let fl = new Uint8Array(W * H);
  for (let y = minRow; y < H; y++) for (let x = 0; x < W; x++) {
    const p = (y * W + x) * 3, d = [sm[p] - mu[0], sm[p + 1] - mu[1], sm[p + 2] - mu[2]];
    let q = 0; for (let r = 0; r < 3; r++) for (let c = 0; c < 3; c++) q += d[r] * iv[r * 3 + c] * d[c];
    fl[y * W + x] = Math.sqrt(Math.max(0, q)) < thr ? 1 : 0;
  }
  fl = opening(fl);
  const obj = fl.map(v => 1 - v), [lab, sizes] = label(obj);
  for (let p = 0; p < W * H; p++) {
    const l = lab[p]; if (!l) continue;
    if (sizes[l] < minObj || (sizes[l] < low[1] && p >= low[0] * W)) fl[p] = 1;
  }
  for (let p = 0; p < minRow * W; p++) fl[p] = 0;
  fl = keepTouchingRow(fl, anchor);
  for (let p = dropBelow * W; p < W * H; p++) fl[p] = 1;
  return fl;
}

// Main entry: full-size RGB pixels -> report.
function analyse(src, sw, sh) {
  const fitH = Math.round(sh * W / sw);
  const res = { fitH, problems: [] };
  if (fitH < H) { res.problems.push('short'); return res; }
  const full = boxResize(src, sw, sh, W, fitH);
  const a = full.subarray(0, W * H * 3);
  const sky = skyMask(a), fl = floorMask(a);
  let skyEnd = 0;
  for (let p = 0; p < W * H; p++) if (sky[p]) skyEnd = Math.max(skyEnd, ((p / W) | 0) + 1);
  const kind = new Uint8Array(28 * 32);           // 0 sky (free), 1 ground (repeating), 2 costs a tile
  let cost = 0, detail = 0, dn = 0;
  for (let ty = 0; ty < 28; ty++) for (let tx = 0; tx < 32; tx++) {
    let anyOther = false, allSky = true;
    for (let y = ty * 8; y < ty * 8 + 8; y++) for (let x = tx * 8; x < tx * 8 + 8; x++) {
      const p = y * W + x;
      if (!sky[p]) allSky = false;
      if (!sky[p] && !fl[p]) {
        anyOther = true;
        if (x > 0) { const q = p * 3; detail += Math.abs(a[q] - a[q - 3]) + Math.abs(a[q + 1] - a[q - 2]) + Math.abs(a[q + 2] - a[q - 1]); dn++; }
      }
    }
    kind[ty * 32 + tx] = anyOther ? 2 : allSky ? 0 : 1;
    if (anyOther) cost++;
  }
  res.sceneryTiles = cost;
  res.tiles = cost + 88;                           // + repeating ground (64) + blend edge (~24), calibrated on 48 pictures
  res.detail = dn ? detail / dn : 0;
  res.skyEnd = skyEnd; res.kind = kind; res.pixels = a; res.sky = sky; res.floor = fl;
  if (skyEnd > 112) res.problems.push('sky');
  // Forecast of the error in the band below the horizon, fitted on the 48 grassland pictures (test build 3):
  // 13 = clean, 19+ = visible blocks. Verdict cut-offs 15.5 / 17.5.
  res.forecast = 0.08 * res.tiles + 0.153 * res.detail - 28.5;
  res.verdict = res.problems.length || res.forecast > 17.5 ? 'fail' : res.forecast > 15.5 ? 'warn' : 'pass';
  return res;
}

if (typeof module !== 'undefined') module.exports = { analyse, boxResize, skyMask, floorMask, W, H };
