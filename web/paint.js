// Samantha's painting hands, in the browser. Same quadtree as pixelmator/pxm.py paint_layers.
// The same quadtree as paint_layers in pxm.py: split the cell with the most color error.
const c = document.getElementById('paint-c'), ctx = c.getContext('2d');
// Paint at the screen's real pixels, one canvas pixel per image pixel, so nothing gets stretched.
const SIDE = Math.round(420 * Math.min(2, window.devicePixelRatio || 1));
const BUDGET = 30000;
let S, w, h, run = 0, style = 'squares';
// Same six styles as pixelmator/styles.py, each at the cell count it reads best at on this smaller canvas.
const STYLE_CELLS = {mosaic: 1200, dots: 3500, poster: 12000, sketch: 9000, glass: 700};
const pics = [['mona.jpg', 'Mona Lisa'], ['supper.jpg', 'The Last Supper'], ['eniac.jpg', 'The ENIAC']];
let pic = 0;

function load(src, name) {
  const img = new Image();
  img.onload = () => {
    const k = SIDE / Math.max(img.width, img.height);
    w = Math.round(img.width * k); h = Math.round(img.height * k);
    const t = Object.assign(document.createElement('canvas'), {width: w, height: h}).getContext('2d');
    t.drawImage(img, 0, 0, w, h);
    const d = t.getImageData(0, 0, w, h).data;
    S = new Float64Array((w + 1) * (h + 1) * 4);  // summed-area table: r, g, b, squares
    for (let y = 0; y < h; y++) for (let x = 0, a = [0, 0, 0, 0]; x < w; x++) {
      const i = (y * w + x) * 4, r = d[i], g = d[i + 1], b = d[i + 2];
      a[0] += r; a[1] += g; a[2] += b; a[3] += r * r + g * g + b * b;
      for (let j = 0; j < 4; j++) S[((y + 1) * (w + 1) + x + 1) * 4 + j] = a[j] + S[(y * (w + 1) + x + 1) * 4 + j];
    }
    c.width = w; c.height = h;
    c.style.aspectRatio = w + ' / ' + h;
    const titleEl = document.getElementById('paint-title');
    titleEl.textContent = name;
    titleEl.style.display = 'inline';
    document.getElementById('desk-space').classList.add('painting');
    paint();
  };
  img.src = src;
}

function cell(x0, y0, x1, y1) {
  const at = (x, y, j) => S[(y * (w + 1) + x) * 4 + j], n = (x1 - x0) * (y1 - y0);
  const v = [0, 1, 2, 3].map(j => at(x1, y1, j) - at(x1, y0, j) - at(x0, y1, j) + at(x0, y0, j));
  return {x0, y0, x1, y1, err: v[3] - (v[0] * v[0] + v[1] * v[1] + v[2] * v[2]) / n,
          fill: `rgb(${v[0] / n | 0},${v[1] / n | 0},${v[2] / n | 0})`};
}

// Max-heap on err: the worst cell is always at the top.
function push(hp, q) {
  let i = hp.push(q) - 1;
  for (let p; i && hp[p = (i - 1) >> 1].err < q.err; i = p) hp[i] = hp[p];
  hp[i] = q;
}
function pop(hp) {
  const top = hp[0], q = hp.pop();
  if (!hp.length) return top;
  let i = 0;
  for (let k; (k = 2 * i + 1) < hp.length; i = k) {
    if (k + 1 < hp.length && hp[k + 1].err > hp[k].err) k++;
    if (hp[k].err <= q.err) break;
    hp[i] = hp[k];
  }
  hp[i] = q;
  return top;
}

// Draw cells in batches across multiple frames to avoid long tasks
function drawBatch(drawFn, cells, batchSize, onComplete) {
  if (!cells.length) { if (onComplete) onComplete(); return; }
  let index = 0;
  function nextBatch() {
    const start = performance.now();
    const end = Math.min(index + batchSize, cells.length);
    for (let i = index; i < end; i++) drawFn(cells[i], i);
    index = end;
    document.getElementById('paint-n').textContent = index;
    if (index < cells.length) {
      // Schedule next batch on next frame
      requestAnimationFrame(nextBatch);
    } else if (onComplete) {
      onComplete();
    }
  }
  requestAnimationFrame(nextBatch);
}

// The styled painting: plan the cells at once (leaves only, like styles.cells), then draw them one style's way.
function leaves(budget) {
  const heap = [cell(0, 0, w, h)], done = [];
  while (heap.length && heap.length + done.length + 3 <= budget) {
    const q = pop(heap), mx = (q.x0 + q.x1) >> 1, my = (q.y0 + q.y1) >> 1;
    for (const [a, b, e, f] of [[q.x0, q.y0, mx, my], [mx, q.y0, q.x1, my], [q.x0, my, mx, q.y1], [mx, my, q.x1, q.y1]]) {
      if (e <= a || f <= b) continue;
      const kid = cell(a, b, e, f);
      if (e - a > 1 && f - b > 1) push(heap, kid); else done.push(kid);
    }
  }
  return done.concat(heap);
}
const rgbOf = q => q.fill.match(/\d+/g).map(Number);
function rich([r, g, b], sat, val) {  // more saturated, a touch brighter: light through glass
  const m = (r + g + b) / 3;
  return 'rgb(' + [r, g, b].map(v => Math.max(0, Math.min(255, (m + (v - m) * sat) * val)) | 0).join(',') + ')';
}

function drawBatch(drawFn, cells, batchSize, onComplete) {
  let index = 0;
  function nextBatch() {
    const end = Math.min(index + batchSize, cells.length);
    for (let i = index; i < end; i++) drawFn(cells[i]);
    index = end;
    document.getElementById('paint-n').textContent = index;
    if (index < cells.length) requestAnimationFrame(nextBatch);
    else if (onComplete) onComplete();
  }
  nextBatch();
}

function styled(name) {
  const cs = leaves(STYLE_CELLS[name]), rnd = (s => () => (s = (s * 16807) % 2147483647) / 2147483647)(7);
  ctx.fillStyle = name === 'mosaic' ? '#1E1C1A' : name === 'glass' ? '#101010' : name === 'poster' ? '#000' : '#F4EFE4';
  ctx.fillRect(0, 0, w, h);

  if (name === 'mosaic' || name === 'glass') {
    const batchSize = 100;
    drawBatch(q => {
      const side = Math.min(q.x1 - q.x0, q.y1 - q.y0), gap = Math.max(1, Math.min(6, Math.round(side * (name === 'mosaic' ? 0.06 : 0.1))));
      if (q.x1 - q.x0 <= 2 * gap || q.y1 - q.y0 <= 2 * gap) return;
      ctx.fillStyle = name === 'mosaic' ? q.fill : rich(rgbOf(q), 1.5, 1.1);
      ctx.beginPath(); ctx.roundRect(q.x0 + gap, q.y0 + gap, q.x1 - q.x0 - 2 * gap, q.y1 - q.y0 - 2 * gap, name === 'mosaic' ? gap : 0); ctx.fill();
    }, cs, batchSize);
  } else if (name === 'dots') {
    const sorted = cs.sort((a, b) => (b.x1 - b.x0) * (b.y1 - b.y0) - (a.x1 - a.x0) * (a.y1 - a.y0));
    const batchSize = 50;
    drawBatch(q => {
      const cw = q.x1 - q.x0, ch = q.y1 - q.y0, n = Math.max(1, Math.min(6, Math.round(Math.max(cw, ch) / Math.min(cw, ch)) + (Math.min(cw, ch) > 20 ? 2 : 0)));
      ctx.fillStyle = rich(rgbOf(q), 1.25, 1.03);
      for (let i = 0; i < n; i++) {
        const r = Math.max(0.8, Math.sqrt(cw * ch / n) * (0.55 + rnd() * 0.2));
        ctx.beginPath(); ctx.arc(q.x0 + (0.2 + rnd() * 0.6) * cw, q.y0 + (0.2 + rnd() * 0.6) * ch, r, 0, 7); ctx.fill();
      }
    }, sorted, batchSize);
  } else if (name === 'poster') {
    // eight colors by area (a small k-means, same seed every time), then every cell takes its nearest
    let cen = Array.from({length: 8}, () => rgbOf(cs[(rnd() * cs.length) | 0]));
    const near = p => cen.reduce((bi, c, i) => (c[0] - p[0]) ** 2 + (c[1] - p[1]) ** 2 + (c[2] - p[2]) ** 2 < (cen[bi][0] - p[0]) ** 2 + (cen[bi][1] - p[1]) ** 2 + (cen[bi][2] - p[2]) ** 2 ? i : bi, 0);
    for (let round = 0; round < 10; round++) {
      const sum = cen.map(() => [0, 0, 0, 0]);
      for (const q of cs) { const p = rgbOf(q), a = (q.x1 - q.x0) * (q.y1 - q.y0), s = sum[near(p)]; s[0] += p[0] * a; s[1] += p[1] * a; s[2] += p[2] * a; s[3] += a; }
      cen = cen.map((c, i) => sum[i][3] ? sum[i].slice(0, 3).map(v => v / sum[i][3]) : c);
    }
    const batchSize = 200;
    drawBatch(q => {
      const c = cen[near(rgbOf(q))];
      ctx.fillStyle = 'rgb(' + c.map(v => v | 0).join(',') + ')';
      ctx.fillRect(q.x0, q.y0, q.x1 - q.x0, q.y1 - q.y0);
    }, cs, batchSize);
  } else if (name === 'sketch') {
    // pencil: equalized tones, one hatch layer per step darker, all on one lattice so strokes run on unbroken
    const lum = q => { const [r, g, b] = rgbOf(q); return (0.299 * r + 0.587 * g + 0.114 * b) / 255; };
    const byTone = cs.map(q => [lum(q), (q.x1 - q.x0) * (q.y1 - q.y0)]).sort((a, b) => a[0] - b[0]);
    const total = byTone.reduce((t, x) => t + x[1], 0), rank = new Map();
    let run2 = 0;
    for (const [v, a] of byTone) { run2 += a; if (!rank.has(v)) rank.set(v, run2 / total); }
    const gap = Math.max(3, Math.round(w / 150));
    ctx.strokeStyle = '#2B2723'; ctx.lineWidth = 1; ctx.beginPath();
    for (const [tone, way, shift] of [[0.2, 1, 0], [0.42, -1, 0], [0.62, 1, 0.5], [0.8, -1, 0.5]]) for (const q of cs) {
      if (1 - rank.get(lum(q)) < tone) continue;
      const lo = way === 1 ? q.x0 + q.y0 : q.x0 - q.y1, hi = way === 1 ? q.x1 + q.y1 : q.x1 - q.y0;
      for (let k = (Math.floor(lo / gap) + shift) * gap; k <= hi; k += gap) {
        const a = way === 1 ? Math.max(q.x0, k - q.y1) : Math.max(q.x0, k + q.y0), e = way === 1 ? Math.min(q.x1, k - q.y0) : Math.min(q.x1, k + q.y1);
        if (e <= a) continue;
        ctx.moveTo(a, way === 1 ? k - a : a - k); ctx.lineTo(e, way === 1 ? k - e : e - k);
      }
    }
    ctx.stroke();
    document.getElementById('paint-n').textContent = cs.length;
  }
  if (name !== 'mosaic' && name !== 'glass' && name !== 'dots' && name !== 'poster' && name !== 'sketch') {
    document.getElementById('paint-n').textContent = cs.length;
  }
}

function paint() {
  const me = ++run;
  if (style !== 'squares' && STYLE_CELLS[style]) return styled(style);
  const still = matchMedia('(prefers-reduced-motion:reduce)').matches;
  let count = 0, heap = [];
  const draw = q => { ctx.fillStyle = q.fill; ctx.fillRect(q.x0, q.y0, q.x1 - q.x0, q.y1 - q.y0); count++; };
  const root = cell(0, 0, w, h); draw(root); heap.push(root);
  (function step() {
    if (me !== run) return;
    for (let k = 0; k < (still ? 1e9 : Math.max(1, BUDGET / 240)) && heap.length && count + 4 <= BUDGET; k++) {
      const q = pop(heap), mx = (q.x0 + q.x1) >> 1, my = (q.y0 + q.y1) >> 1;
      for (const [a, b, e, f] of [[q.x0, q.y0, mx, my], [mx, q.y0, q.x1, my], [q.x0, my, mx, q.y1], [mx, my, q.x1, q.y1]]) {
        if (e <= a || f <= b) continue;
        const kid = cell(a, b, e, f); draw(kid);
        if (e - a > 1 && f - b > 1) push(heap, kid);
      }
    }
    document.getElementById('paint-n').textContent = count;
    if (heap.length && count + 4 <= BUDGET) requestAnimationFrame(step);
  })();
}

const picks = document.getElementById('paint-picks');
(picks ? pics : []).forEach(([src, name], i) => {
  const b = document.createElement('button');
  b.type = 'button'; b.className = 'paint-pick'; b.title = name; b.setAttribute('aria-label', 'Paint ' + name);
  b.setAttribute('aria-pressed', i === 0);
  b.innerHTML = '<img src="' + src + '" alt="" loading="lazy">';
  b.onclick = () => {
    pic = i; style = 'squares';
    picks.querySelectorAll('button').forEach((x, k) => x.setAttribute('aria-pressed', k === i));
    load(src, name);
  };
  picks.appendChild(b);
});
const fileInput = document.getElementById('paint-file');
if (fileInput) fileInput.onchange = e => {
  const f = e.target.files[0];
  if (!f) return;
  const r = new FileReader();
  r.onload = () => load(r.result, f.name.replace(/\.[^.]+$/, ''));
  r.readAsDataURL(f);
};
window.samanthaPaint = function(index, how) {
  style = STYLE_CELLS[how] ? how : 'squares';
  if (index < 0 || index >= pics.length) index = pic;
  pic = index;
  if (picks) picks.querySelectorAll('button').forEach((x, k) => x.setAttribute('aria-pressed', k === index));
  load(...pics[index]);
  return pics[index][1];
};

// A picture from anywhere (the image model's drawing arrives as a data URL): rebuild it from squares.
window.samanthaPaintSrc = (src, name) => { style = 'squares'; load(src, name); };
