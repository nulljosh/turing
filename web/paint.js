// Samantha's painting hands, in the browser. Same quadtree as pixelmator/pxm.py paint_layers.
// The same quadtree as paint_layers in pxm.py: split the cell with the most color error.
const c = document.getElementById('paint-c'), ctx = c.getContext('2d');
const SCALE = 3, SIDE = 192;
let S, w, h, run = 0;
const pics = [['mona.jpg', 'Mona Lisa'], ['supper.jpg', 'The Last Supper'], ['monet.jpg', 'Impression, Sunrise']];
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
    c.width = w * SCALE; c.height = h * SCALE;
    document.getElementById('paint-title').textContent = name;
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

function paint() {
  const me = ++run, budget = +document.getElementById('paint-budget').value;
  const still = matchMedia('(prefers-reduced-motion:reduce)').matches;
  let count = 0, heap = [];
  const draw = q => { ctx.fillStyle = q.fill; ctx.fillRect(q.x0 * SCALE, q.y0 * SCALE, (q.x1 - q.x0) * SCALE, (q.y1 - q.y0) * SCALE); count++; };
  const root = cell(0, 0, w, h); draw(root); heap.push(root);
  (function step() {
    if (me !== run) return;
    for (let k = 0; k < (still ? 1e9 : Math.max(1, budget / 240)) && heap.length && count + 4 <= budget; k++) {
      let bi = 0;  // linear scan for the worst cell: fine at a few thousand cells
      for (let i = 1; i < heap.length; i++) if (heap[i].err > heap[bi].err) bi = i;
      const q = heap.splice(bi, 1)[0], mx = (q.x0 + q.x1) >> 1, my = (q.y0 + q.y1) >> 1;
      for (const [a, b, e, f] of [[q.x0, q.y0, mx, my], [mx, q.y0, q.x1, my], [q.x0, my, mx, q.y1], [mx, my, q.x1, q.y1]]) {
        if (e <= a || f <= b) continue;
        const kid = cell(a, b, e, f); draw(kid);
        if (e - a > 1 && f - b > 1) heap.push(kid);
      }
    }
    document.getElementById('paint-n').textContent = count;
    if (heap.length && count + 4 <= budget) requestAnimationFrame(step);
  })();
}

document.getElementById('paint-again').onclick = paint;
document.getElementById('paint-budget').onchange = paint;
const picks = document.getElementById('paint-picks');
pics.forEach(([src, name], i) => {
  const b = document.createElement('button');
  b.type = 'button'; b.className = 'paint-pick'; b.title = name; b.setAttribute('aria-label', 'Paint ' + name);
  b.setAttribute('aria-pressed', i === 0);
  b.innerHTML = '<img src="' + src + '" alt="" loading="lazy">';
  b.onclick = () => {
    pic = i;
    picks.querySelectorAll('button').forEach((x, k) => x.setAttribute('aria-pressed', k === i));
    load(src, name);
  };
  picks.appendChild(b);
});
document.getElementById('paint-file').onchange = e => {
  const f = e.target.files[0];
  if (!f) return;
  const r = new FileReader();
  r.onload = () => load(r.result, f.name.replace(/\.[^.]+$/, ''));
  r.readAsDataURL(f);
};
load(...pics[0]);
