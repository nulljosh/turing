// Hero, after Plank and Keyrate. Her real screen (reel/hero-loop.mp4, the trailer with its title cards and captions
// cut) lies tilted on the desk under the title and flattens as you scroll. The readout under the buttons follows the
// video: the command she was given and what she said back, typed out. Loose keycaps of her commands drift at three
// depths and lean away from the pointer. "Sound on" plays it from the top with her voice. Reduced motion: a still scene.
(function () {
  var still = matchMedia('(prefers-reduced-motion: reduce)').matches;
  var hero = document.querySelector('.hero'), v = document.querySelector('.hero-video'), b = document.querySelector('.hero-sound');
  var cmd = document.getElementById('rCmd'), said = document.getElementById('rSaid');
  var el = function (t, c, x) { var e = document.createElement(t); if (c) e.className = c; if (x != null) e.textContent = x; return e; };

  // what happens in the loop, by second (read off the trailer's own command bar and captions)
  var CUES = [
    [0, 'open calculator', 'Opened Calculator'],
    [2, 'open chess', 'Opened Chess'],
    [4, "type Hi, I'm Samantha", 'Typed it into TextEdit'],
    [5.5, 'boot joshua tree', 'Booted Joshua Tree, the OS built from scratch'],
    [7.5, 'write a script to today.py', 'Wrote today.py, shown first, saved on a yes'],
    [9.5, 'make a logo for a surf school', 'I went with a wave, palette blue'],
    [11.5, 'make a logo for a coffee roaster', 'I went with a cup, palette green'],
    [13.5, 'reveal today.py in finder', 'Showing today.py in Finder'],
    [15, 'add captions to talk.mp4', 'Wrote the captions from what I heard'],
    [17, 'is 91 prime', '91 is not prime: 7 × 13'],
    [19, 'convert 72 f to c', '72 F is 22.22 C'],
    [21, 'time in tokyo', 'It is 8:36 AM in Tokyo']
  ];
  var shown = -1, typing = 0;
  function cueAt(t) { var i = 0; while (i + 1 < CUES.length && CUES[i + 1][0] <= t) i++; return i; }
  function show(i) {
    if (i === shown || !cmd || !said) return;
    shown = i; cmd.textContent = CUES[i][1]; clearInterval(typing);
    var text = CUES[i][2], n = 0;
    if (still) { said.textContent = text; return; }
    said.textContent = '';
    typing = setInterval(function () { said.textContent = text.slice(0, ++n); if (n >= text.length) clearInterval(typing); }, 22);
  }
  if (v) {
    if (still) { v.removeAttribute('autoplay'); v.pause(); show(1); }
    else { var p = v.play(); if (p && p.catch) p.catch(function () {}); show(0); }
    v.addEventListener('timeupdate', function () { show(cueAt(v.currentTime)); });
  }
  if (b && v) b.addEventListener('click', function () {
    var on = v.muted;
    v.muted = !on; if (on) { v.currentTime = 0; v.play(); }
    b.textContent = on ? 'Sound off' : 'Sound on'; b.setAttribute('aria-pressed', on ? 'true' : 'false');
  });

  // loose keycaps at three depths; the middle stays clear for the title
  var sky = document.getElementById('sky'), layers = [];
  if (sky) {
    var seed = 7, rnd = function () { return (seed = (seed * 16807) % 2147483647) / 2147483647; };
    var few = innerWidth < 640;
    var words = ['open', 'remind', 'note', 'paint', '7 × 13', '°C', '.srt', 'esc', 'yes?', 'find', 'logo', 'timer', '⌘', 'mail', 'tokyo', 'chess', 'mute', 'undo', 'today.py', 'calc'];
    var depths = [
      { cls: 'far', n: 10, size: 22, lag: .6, o: .45 },
      { cls: 'mid', n: 8, size: 36, lag: .3, o: .75 },
      { cls: 'near', n: 6, size: 56, lag: -.3, o: .95 }
    ];
    depths.forEach(function (d, di) {
      var layer = sky.appendChild(el('div', 'layer ' + d.cls));
      var n = few ? (d.cls === 'far' ? Math.ceil(d.n / 2) : 0) : d.n;  // a phone's text spans the width: only the faint far keys, or they sit on the headline
      for (var i = 0; i < n; i++) {
        var side = i % 2, slot = Math.floor(i / 2), slots = Math.ceil(n / 2);
        var band = d.cls === 'far' ? 22 : 13;
        var x = side ? 96 - band + rnd() * band - 4 : 2 + rnd() * band;
        var y = 4 + (slot + .15 + rnd() * .7) * (88 / slots);
        var hot = d.cls !== 'far' && rnd() < .3;
        var t = layer.appendChild(el('span', 'tok' + (hot ? ' hot' : ''), words[(i * 7 + di * 5 + 2) % words.length]));
        t.style.cssText = 'left:' + x.toFixed(1) + '%;top:' + y.toFixed(1) + '%;--s:' + d.size + 'px;opacity:' + d.o + ';' +
          'animation-duration:' + (5 + rnd() * 5).toFixed(1) + 's;animation-delay:' + (-rnd() * 10).toFixed(1) + 's;--r:' + Math.round(rnd() * 30 - 15) + 'deg';
      }
      layers.push({ layer: layer, lag: d.lag });
    });
  }
  if (still || !hero) return;

  // scroll and pointer, eased each frame: the screen flattens and grows, keycaps move at their own speed, the copy lifts
  var screen = document.querySelector('.screen'), copy = document.querySelector('.hero-copy');
  var px = 0, py = 0, tx = 0, ty = 0, sy = 0, cur = 0, raf = 0, onscreen = true;
  if ('IntersectionObserver' in window) new IntersectionObserver(function (es) { onscreen = es[0].isIntersecting; if (onscreen) kick(); }).observe(hero);
  if (matchMedia('(pointer: fine)').matches) addEventListener('pointermove', function (e) { tx = e.clientX / innerWidth - .5; ty = e.clientY / innerHeight - .5; kick(); }, { passive: true });
  addEventListener('scroll', kick, { passive: true });
  function kick() { if (!raf) raf = requestAnimationFrame(frame); }
  function frame() {
    raf = 0; if (!onscreen) return;
    sy = scrollY; cur += (sy - cur) * .14; px += (tx - px) * .08; py += (ty - py) * .08;
    var h = hero.offsetHeight || 1, k = Math.min(1, Math.max(0, cur / (h * .6)));
    if (screen) { screen.style.setProperty('--tilt', (24 * (1 - k)).toFixed(2) + 'deg'); screen.style.setProperty('--grow', (.94 + .06 * k).toFixed(3)); }
    if (copy) { copy.style.transform = 'translateY(' + (-cur * .18).toFixed(1) + 'px)'; copy.style.opacity = Math.max(0, 1 - cur / (h * .55)).toFixed(3); }
    layers.forEach(function (L, i) { L.layer.style.transform = 'translate(' + (px * (i + 1) * -14).toFixed(1) + 'px,' + (cur * L.lag * -1 + py * (i + 1) * -10).toFixed(1) + 'px)'; });
    if (Math.abs(sy - cur) > .5 || Math.abs(tx - px) > .002 || Math.abs(ty - py) > .002) kick();
  }
  kick();
})();
