/* The footer plate: an engraving of a language model writing (tokens, causal attention arcs, a field of weights),
   every tone a hatch of ink lines. Only animates while on screen; a still frame with reduced motion; hidden without WebGL. */
      (function () {
        var canvas = document.querySelector('.foot-scene');
        var gl = canvas && canvas.getContext('webgl', { antialias: false, alpha: false });
        if (!gl) { if (canvas) canvas.style.display = 'none'; return; }
        var FRAG = `
precision highp float;
uniform vec2 res;
uniform float time;
uniform vec3 paper;
uniform vec3 ink;
uniform float dpr;

float hash(float n) { return fract(sin(n) * 43758.5453); }
float hash2(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
float noise2(vec2 p) {
  vec2 i = floor(p), f = fract(p);
  vec2 u = f * f * (3.0 - 2.0 * f);
  return mix(mix(hash2(i), hash2(i + vec2(1, 0)), u.x), mix(hash2(i + vec2(0, 1)), hash2(i + vec2(1, 1)), u.x), u.y);
}

// Ink lines at angle a, spacing s pixels. Returns 1 where ink falls for tone t.
float hatch(vec2 px, float a, float s, float t) {
  float d = abs(fract(dot(px, vec2(cos(a), sin(a))) / s) - 0.5) * 2.0;
  return 1.0 - smoothstep(t - 0.12, t + 0.12, d);
}

// The plate is a language model writing: a row of tokens fills in left to right, each new token throws attention
// arcs back to a few earlier ones (causal, never forward), and a faint matrix of weights breathes above.
// Tone 0 = paper, 1 = solid ink; kind picks the hatch angle.
const float N = 28.0;
float tokX(float i) { return (i + 0.5) / N; }
float scene(vec2 uv, out float kind) {
  float asp = res.x / res.y;
  float cur = mod(floor(time * 0.9), N + 6.0);  // the token being written; a short pause on the full line, then a new one
  kind = 0.0;
  float i = floor(uv.x * N), fx = fract(uv.x * N);
  if (uv.y > 0.10 && uv.y < 0.19 && fx > 0.14 && fx < 0.86) {
    kind = 2.0;
    if (i > cur) return 0.10;
    return i == cur ? 0.96 : 0.6;
  }
  if (uv.y > 0.19) {
    float best = 0.0;
    for (int k = 1; k < 28; k++) {
      float t = float(k);
      if (t > cur) break;
      for (int h = 0; h < 2; h++) {
        float back = 1.0 + floor(hash(t * 7.0 + float(h) * 13.0) * min(t, 8.0));
        float b = t - back;
        vec2 c = vec2((tokX(t) + tokX(b)) * 0.5 * asp, 0.19);
        float r = (tokX(t) - tokX(b)) * 0.5 * asp;
        float d = abs(length(vec2(uv.x * asp, uv.y) - c) - r);
        float w = 0.003 + 0.005 * hash(t + float(h) * 3.1);
        float on = 1.0 - smoothstep(w, w + 0.003, d);
        best = max(best, on * (t == cur ? 0.95 : 0.4 + 0.3 * hash(t * 3.0 + float(h))));
      }
    }
    if (best > 0.0) { kind = 1.0; return best; }
  }
  vec2 g = vec2(uv.x * asp, uv.y) * 18.0;
  float wv = noise2(floor(g) * 0.35 + vec2(time * 0.05, 0.0));
  kind = 3.0;
  return (1.0 - smoothstep(0.16, 0.22, length(fract(g) - 0.5))) * wv * 0.26 * smoothstep(0.25, 0.85, uv.y);
}

void main() {
  vec2 px = gl_FragCoord.xy;
  vec2 uv = px / res;
  float kind;
  float tone = scene(uv, kind);
  float s = 4.0 * dpr;
  float a = kind == 2.0 ? 0.0 : kind == 1.0 ? 0.785 : kind == 3.0 ? -0.6 : 0.35;
  float lines = hatch(px, a, s, tone);
  // A cross hatch in the darkest places, like a real engraving.
  lines = max(lines, hatch(px, a + 1.5708, s, tone - 0.55));
  // Fade the whole plate in from the top so it sits under the footer text.
  float fade = smoothstep(1.0, 0.72, uv.y);
  float grain = (hash2(px) - 0.5) * 0.06;
  float amt = clamp(lines * fade + grain * fade, 0.0, 1.0);
  gl_FragColor = vec4(mix(paper, ink, amt), 1.0);
}`;
        var VERT = 'attribute vec2 p; void main() { gl_Position = vec4(p, 0.0, 1.0); }';
        var prog = gl.createProgram();
        [[gl.VERTEX_SHADER, VERT], [gl.FRAGMENT_SHADER, FRAG]].forEach(function (s) {
          var sh = gl.createShader(s[0]); gl.shaderSource(sh, s[1]); gl.compileShader(sh); gl.attachShader(prog, sh);
        });
        gl.linkProgram(prog);
        if (!gl.getProgramParameter(prog, gl.LINK_STATUS)) { canvas.style.display = 'none'; return; }
        gl.useProgram(prog);
        gl.bindBuffer(gl.ARRAY_BUFFER, gl.createBuffer());
        gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 3, -1, -1, 3]), gl.STATIC_DRAW);
        var loc = gl.getAttribLocation(prog, 'p');
        gl.enableVertexAttribArray(loc);
        gl.vertexAttribPointer(loc, 2, gl.FLOAT, false, 0, 0);
        function u(name) { return gl.getUniformLocation(prog, name); }
        function rgb(css) {
          var c = document.createElement('canvas').getContext('2d');
          c.fillStyle = css;
          var h = c.fillStyle;
          if (h.charAt(0) === '#') return [1, 3, 5].map(function (i) { return parseInt(h.slice(i, i + 2), 16) / 255; });
          return (h.match(/[\d.]+/g) || [0, 0, 0]).slice(0, 3).map(function (n) { return +n / 255; });
        }
        var still = matchMedia('(prefers-reduced-motion: reduce)').matches, raf = 0, visible = false, start = performance.now();
        function draw() {
          var dpr = Math.min(window.devicePixelRatio || 1, 2); /* ponytail: capped at 2, a 3x phone canvas costs memory for no visible gain */
          var w = canvas.clientWidth * dpr, h = canvas.clientHeight * dpr;
          if (canvas.width !== w || canvas.height !== h) { canvas.width = w; canvas.height = h; }
          gl.viewport(0, 0, w, h);
          var cs = getComputedStyle(canvas);
          gl.uniform2f(u('res'), w, h);
          gl.uniform1f(u('time'), (performance.now() - start) / 1000);
          gl.uniform1f(u('dpr'), dpr);
          gl.uniform3fv(u('paper'), rgb(cs.getPropertyValue('--scene-paper').trim() || '#ffffff'));
          gl.uniform3fv(u('ink'), rgb(cs.getPropertyValue('--scene-ink').trim() || '#8e949d'));
          gl.drawArrays(gl.TRIANGLES, 0, 3);
        }
        function loop() { draw(); if (visible && !still) raf = requestAnimationFrame(loop); }
        new IntersectionObserver(function (e) { visible = e[0].isIntersecting; cancelAnimationFrame(raf); if (visible) loop(); }).observe(canvas);
        /* a theme switch or a resize repaints the still frame too */
        new MutationObserver(draw).observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] });
        matchMedia('(prefers-color-scheme: dark)').addEventListener('change', function () { setTimeout(draw, 0); });
        addEventListener('resize', draw);
        draw();
      })();
