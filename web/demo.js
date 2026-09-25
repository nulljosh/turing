// The landing page demo. samantha.js decides what a sentence means, this file
// is the Mac it happens on. A web page cannot touch a visitor's computer, so
// the desk up top is a stand-in, and everything a browser can really do, it
// really does: speech, weather, timers, sound, the logo, the lookups.
(function () {
  var S = window.Samantha;
  var $ = function (id) { return document.getElementById(id); };
  var transcript = $('chat-transcript'), input = $('chat-input'), space = $('desk-space'), statusEl = $('chat-status');
  var reduceMotion = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var typing = reduceMotion ? 0 : 14;
  var isLive = false, busy = false, reel = false, idleTimer = 0, reelTimer = 0, lastUser = 0, pending = null;
  var LOCAL = 'http://localhost:8127/v1/chat/completions';

  function el(tag, cls, text) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text != null) e.textContent = text;
    return e;
  }
  function load(key) { try { return JSON.parse(localStorage.getItem('samantha-' + key)) || []; } catch (e) { return []; } }
  function save(key, val) { try { localStorage.setItem('samantha-' + key, JSON.stringify(val.slice(-20))); } catch (e) {} }

  var desk = { volume: 50, playing: false, track: 0, notes: load('notes'), reminders: load('reminders'), tab: null,
               clipboard: 'turing.heyitsmejosh.com', timerEnd: 0 };

  // ---- the stand-in Mac ----
  // hosts that allow being framed, each tried in a real Chromium (curl headers missed Hacker News, which refuses). GitHub, YouTube, Reddit, HN and most others refuse.
  var FRAMEABLE = /^(?:www\.)?(?:(?:[a-z-]+\.)?wikipedia\.org|heyitsmejosh\.com|example\.com|lobste\.rs|text\.npr\.org|info\.cern\.ch|archive\.org|gutenberg\.org|openlibrary\.org|xkcd\.com|wiby\.me)$/i;
  function closeWins() { var all = space.querySelectorAll('.win'); for (var k = 0; k < all.length; k++) all[k].remove(); }
  function win(id, title, build) {
    var w = $('win-' + id);
    if (!w) {
      w = el('div', 'win');
      w.id = 'win-' + id;
      var bar = el('div', 'win-bar'), dots = el('span', 'win-dots');
      dots.appendChild(el('i')); dots.appendChild(el('i')); dots.appendChild(el('i'));
      bar.appendChild(dots);
      bar.appendChild(el('span', 'win-title'));
      w.appendChild(bar);
      w.appendChild(el('div', 'win-body'));
      var open = space.querySelectorAll('.win');
      for (var k = 0; k <= open.length - 2; k++) open[k].remove();  // at most two windows on the stand-in Mac, the oldest goes
      var n = space.querySelectorAll('.win').length;
      w.style.left = (2 + (n % 4) * 7) + '%';
      w.style.top = (8 + (n % 4) * 18) + 'px';
    }
    w.querySelector('.win-title').textContent = title;
    var body = w.querySelector('.win-body');
    body.textContent = '';
    build(body);
    space.appendChild(w);  // last child sits on top
    var all = space.querySelectorAll('.win');
    if (all.length > 4) all[0].remove();
    // a window is a glance, not furniture: it leaves after a few seconds so it never sits on the picture
    clearTimeout(w._away);
    w._away = setTimeout(function () { w.remove(); }, id === 'Google Chrome' ? 14000 : 6000);
  }

  function list(body, items, empty) {
    if (!items.length) { body.appendChild(el('div', 'win-empty', empty)); return; }
    items.slice(-6).forEach(function (t) { body.appendChild(el('div', 'win-row', t)); });
  }

  function paintBar() {
    $('desk-vol-fill').style.width = desk.volume + '%';
    $('desk-vol').textContent = desk.volume === 0 ? 'Muted' : 'Vol ' + desk.volume;
    $('desk-music').textContent = desk.playing ? 'Playing: ' + TRACKS[desk.track][0] : '';
    $('desk-clock').textContent = new Date().toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' });
    var left = Math.max(0, Math.ceil((desk.timerEnd - Date.now()) / 1000));
    $('desk-timer').textContent = desk.timerEnd ? 'Timer ' + Math.floor(left / 60) + ':' + ('0' + left % 60).slice(-2) : '';
  }

  // ---- sound: three little loops, so play, pause, skip and volume are audible ----
  var TRACKS = [['Arpeggio in C', [261.6, 329.6, 392, 523.3]], ['Minor Loop', [220, 261.6, 329.6, 440]], ['Fifths', [196, 293.7, 392, 293.7]]];
  var audio = null, gain = null, beat = 0, step = 0;
  function tick() {
    if (!desk.playing || !audio) return;
    var t = audio.currentTime, o = audio.createOscillator(), g = audio.createGain();
    o.type = 'triangle';
    o.frequency.value = TRACKS[desk.track][1][step++ % 4];
    g.gain.setValueAtTime(0.0001, t);
    g.gain.exponentialRampToValueAtTime(0.22, t + 0.02);
    g.gain.exponentialRampToValueAtTime(0.0001, t + 0.28);
    o.connect(g); g.connect(gain); o.start(t); o.stop(t + 0.3);
  }
  function sound(on) {
    clearInterval(beat);
    if (!on || reel) return;  // the idle reel never makes noise
    var AC = window.AudioContext || window.webkitAudioContext;
    if (!AC) return;
    if (!audio) { audio = new AC(); gain = audio.createGain(); gain.connect(audio.destination); }
    audio.resume();
    gain.gain.value = desk.volume / 100;
    beat = setInterval(tick, 300);
  }

  // ---- logos: the same layout rules as tools._logo_layers and _complex_layers, drawn as SVG ----
  var PALETTES = { ember: ['#15110D', '#F4C893', '#E8A96A'], ink: ['#101418', '#FFFFFF', '#F2B33D'], forest: ['#0F1A14', '#E9F2EA', '#6FBF73'],
                   signal: ['#16161A', '#FFFFFF', '#E5484D'], paper: ['#F3EDE2', '#1A1410', '#C2562D'] };
  var NS = 'http://www.w3.org/2000/svg';
  function svg(tag, attrs) {
    var e = document.createElementNS(NS, tag);
    Object.keys(attrs).forEach(function (k) { e.setAttribute(k, attrs[k]); });
    return e;
  }
  function star(cx, cy, size, points, inner, fill, opacity) {
    var pts = [], R = size / 2, r = R * inner / 100;
    for (var i = 0; i < points * 2; i++) {
      var a = Math.PI * i / points - Math.PI / 2, d = i % 2 ? r : R;
      pts.push((cx + d * Math.cos(a)).toFixed(1) + ',' + (cy + d * Math.sin(a)).toFixed(1));
    }
    return svg('polygon', { points: pts.join(' '), fill: fill, opacity: opacity == null ? 1 : opacity });
  }
  function hash(s) { var h = 5381; for (var i = 0; i < s.length; i++) h = ((h * 33) ^ s.charCodeAt(i)) >>> 0; return h; }
  // Default: no letters. Cells on a golden-angle spiral, the same layout as tools_logo._bloom_layers; cell 1 sits on the centre.
  // style flower is her icon's look: packed accent petals round a dark ring and one bright core (tools_logo._flower_layers).
  function drawBloom(desc) {
    var h = hash(desc.toLowerCase()), names = Object.keys(PALETTES), palette = names[h % names.length], p = PALETTES[palette];
    var tile = p[0], ink = p[1], accent = p[2], cells = [55, 89, 144, 233][(h >>> 3) % 4], shape = (h >>> 5) % 2 ? 'square' : 'circle', lit = 1 + (h >>> 7) % 5;
    var style = (h >>> 9) % 2 ? 'flower' : 'spiral', flower = style === 'flower', span = flower ? 305 : 335, k = Math.sqrt(144 / cells) * (flower ? 1.45 * span / 335 : 1);
    var root = svg('svg', { viewBox: '0 0 1024 1024', role: 'img', 'aria-label': 'A wordless logo: a golden spiral of cells' });
    root.appendChild(svg('rect', { x: 72, y: 72, width: 880, height: 880, rx: 200, fill: tile }));
    var golden = 137.507764 * Math.PI / 180, fib = [1, 3, 8, 21, 55, 144, 233].filter(function (n) { return n <= cells; });
    var bright = flower ? [] : fib.slice(-lit).concat([1]), drawn = 1;
    for (var i = flower ? 2 : 1; i <= cells; i++) {
      var f = Math.sqrt((i - 1) / (cells - 1)), r = span * f, th = i * golden, on = bright.indexOf(i) >= 0;
      if (flower && f < 0.55) continue;  // tools_logo.FLOWER_GAP
      var size = Math.round(k * (14 + 30 * f + (on ? (i === 1 ? 44 : 16) : 0))), x = 512 + Math.round(r * Math.cos(th)), y = 512 + Math.round(r * Math.sin(th));
      var op = flower ? (85 + 15 * f) / 100 : on ? 1 : (52 + 40 * f) / 100, fill = flower || on ? accent : ink;
      drawn++;
      root.appendChild(shape === 'square'
        ? svg('rect', { x: x - size / 2, y: y - size / 2, width: size, height: size, rx: Math.max(2, Math.floor(size / 6)), fill: fill, opacity: op,
                        transform: 'rotate(' + (th * 180 / Math.PI % 360).toFixed(2) + ' ' + x + ' ' + y + ')' })
        : svg('circle', { cx: x, cy: y, r: size / 2, fill: fill, opacity: op }));
    }
    if (flower) { root.appendChild(svg('circle', { cx: 512, cy: 512, r: 80, fill: ink })); drawn++; }
    return { svg: root, text: 'I went with palette ' + palette + ', cells ' + cells + ', shape ' + shape + ', style ' + style + (flower ? '' : ', lit ' + lit) + '. ' + drawn +
             ' layers, no text. Here a hash of your words turns the dials. On the Mac her 1.7B picks them.' };
  }
  function drawLogo(desc) {
    var fancy = /\b(?:complex|intricate|detailed|elaborate|ornate|fancy|crazy|insane)\b/i.test(desc);
    var simple = !fancy && /\b(?:simple|minimal|minimalist|clean|plain)\b/i.test(desc);
    if (!fancy && !simple) return drawBloom(desc);
    var h = hash(desc.toLowerCase()), names = Object.keys(PALETTES), palette = names[h % names.length], p = PALETTES[palette];
    var tile = p[0], ink = p[1], accent = p[2], C = 512;
    var root = svg('svg', { viewBox: '0 0 1024 1024', role: 'img', 'aria-label': 'An icon logo, no text' });
    root.appendChild(svg('rect', { x: 72, y: 72, width: 880, height: 880, rx: 200, fill: tile }));
    var chose, layers;
    if (!fancy) {
      var motif = ['ring', 'spark', 'bars', 'dot'][(h >>> 3) % 4];
      if (motif === 'ring') {
        root.appendChild(svg('circle', { cx: C, cy: C, r: 320, fill: 'none', stroke: accent, 'stroke-width': 28 }));
        root.appendChild(svg('circle', { cx: C, cy: C, r: 150, fill: accent }));
      } else if (motif === 'spark') {
        root.appendChild(star(C, C, 520, 4, 72, accent));
        root.appendChild(svg('circle', { cx: C, cy: C, r: 60, fill: ink }));
      } else if (motif === 'bars') {
        [[392, 240, accent], [512, 420, ink], [632, 320, accent]].forEach(function (b) {
          root.appendChild(svg('rect', { x: b[0] - 45, y: C - b[1] / 2, width: 90, height: b[1], rx: 45, fill: b[2] }));
        });
      } else {
        root.appendChild(svg('circle', { cx: C, cy: C, r: 180, fill: accent }));
        root.appendChild(svg('circle', { cx: 690, cy: 340, r: 55, fill: ink }));
      }
      chose = 'palette ' + palette + ', motif ' + motif;
      layers = motif === 'bars' ? 4 : 3;
    } else {
      var rings = 2 + (h >>> 3) % 4, rays = [12, 16, 20, 24, 30, 36][(h >>> 5) % 6], style = ['bars', 'dots', 'stars'][(h >>> 8) % 3];
      var orbit = [0, 6, 8, 12, 16][(h >>> 10) % 5], points = 4 + (h >>> 13) % 9, gap = Math.floor(300 / rings);
      var polar = function (r, deg) { var t = deg * Math.PI / 180; return [C + r * Math.sin(t), C - r * Math.cos(t)]; };
      for (var i = 0; i < rays; i++) {
        var deg = 360 * i / rays, long = i % 2 === 0, at = polar(long ? 372 : 384, deg), op = long ? 1 : 0.55;
        if (style === 'bars') {
          var bh = long ? 64 : 36;
          root.appendChild(svg('rect', { x: at[0] - 5, y: at[1] - bh / 2, width: 10, height: bh, rx: 5, fill: accent, opacity: op,
                                         transform: 'rotate(' + deg.toFixed(2) + ' ' + at[0].toFixed(1) + ' ' + at[1].toFixed(1) + ')' }));
        } else if (style === 'stars') root.appendChild(star(at[0], at[1], long ? 34 : 22, 4, 35, accent, op));
        else root.appendChild(svg('circle', { cx: at[0], cy: at[1], r: long ? 11 : 6, fill: accent, opacity: op }));
      }
      for (var k = 0; k < rings; k++)
        root.appendChild(svg('circle', { cx: C, cy: C, r: (620 - k * gap) / 2, fill: 'none', stroke: k % 2 ? ink : accent,
                                         'stroke-width': Math.max(4, 16 - 3 * k), opacity: (100 - 15 * k) / 100 }));
      for (var j = 0; j < orbit; j++) {
        var o = polar(310 - gap / 2, 360 * j / orbit + 180 / orbit);
        root.appendChild(svg('circle', { cx: o[0], cy: o[1], r: 9, fill: ink }));
      }
      root.appendChild(svg('circle', { cx: C, cy: C, r: 150, fill: tile }));
      root.appendChild(star(C, C, 290, points, 72, accent, 0.28));
      root.appendChild(svg('circle', { cx: C, cy: C, r: 48, fill: ink }));
      chose = 'palette ' + palette + ', rings ' + rings + ', rays ' + rays + ', ray_style ' + style +
              ', orbit_dots ' + orbit + ', star_points ' + points;
      layers = 1 + rays + rings + orbit + 3;
    }
    return { svg: root, text: 'I went with ' + chose + '. ' + layers + ' layers, no text. Here a hash of your words turns the dials. On the Mac her 1.7B picks them.' };
  }

  // ---- a small home folder, with the same rules as tools._inside_home ----
  var DIRS = { '~': ['Desktop', 'Documents', 'Downloads', 'notes.txt'], '~/Desktop': ['samantha-logo.png'], '~/Documents': ['ideas.txt', 'todo.md'], '~/Downloads': [] };
  var FILES = { '~/notes.txt': 'Facts live in the lookup. Shape lives in the weights.', '~/Documents/todo.md': '- knowledge to 60 of 65\n- her own tool-picking head\n- a timer she can cancel',
                '~/Documents/ideas.txt': 'Train the tiny from-scratch model with three-value weights.' };
  function path(p) {
    p = p.trim().replace(/^(?:my |the )/i, '').replace(/ folder$/i, '').replace(/\/+$/, '');
    if (/^(desktop|documents|downloads)$/i.test(p)) p = '~/' + p[0].toUpperCase() + p.slice(1).toLowerCase();
    return p || '~';
  }

  // ---- her tools. Each returns the sentence she says, or a promise of it ----
  var TOOLS = {
    open_app: function (name) {
      var app = S.appMatch(name);
      if (!app) return 'No app called "' + name + '" on this Mac.';
      var open = $('win-' + app);
      if (open && !/^(?:Notes|Reminders|Music|Calendar)$/.test(app)) { space.appendChild(open); return 'Opened ' + app + '.'; }  // already showing her work: raise it, don't wipe it
      win(app, app, function (b) {
        if (app === 'Notes') list(b, desk.notes, 'No notes yet.');
        else if (app === 'Reminders') list(b, desk.reminders, 'No reminders.');
        else if (app === 'Music') b.appendChild(el('div', 'win-row', desk.playing ? 'Playing: ' + TRACKS[desk.track][0] : 'Paused'));
        else if (app === 'Calendar') b.appendChild(el('div', 'win-row', new Date().toLocaleDateString([], { weekday: 'long', month: 'long', day: 'numeric' })));
        else b.appendChild(el('div', 'win-empty', app));
      });
      return 'Opened ' + app + '.';
    },
    open_url: function (target) {
      var url = S.urlOf(target);
      if (!url) return TOOLS.web_search(target);
      var host = '';
      try { host = new URL(url).hostname; } catch (e) {}
      var framed = FRAMEABLE.test(host);
      desk.tab = { title: url.replace(/^https?:\/\//, ''), url: url };
      win('Google Chrome', 'Google Chrome', function (b) {
        b.appendChild(el('div', 'win-url', url));
        if (framed) {
          // the real page, live, inside the stand-in Mac. Sandboxed, and a different origin from this page, so it cannot reach it.
          var f = el('iframe', 'win-frame');
          f.src = url; f.setAttribute('sandbox', 'allow-scripts allow-same-origin allow-popups allow-forms');  // same-origin here means the framed site's OWN origin, never ours f.setAttribute('referrerpolicy', 'no-referrer');
          f.setAttribute('loading', 'lazy'); f.setAttribute('title', 'Live page: ' + host);
          b.appendChild(f);
        } else {
          b.appendChild(el('div', 'win-note', host.replace(/^www\./, '') + ' does not allow itself to be shown inside another page.'));
        }
        var a = el('a', 'win-link', framed ? 'Open it in its own tab' : 'Open it for real');
        a.href = url; a.target = '_blank'; a.rel = 'noopener';
        b.appendChild(a);
      });
      var w = $('win-Google Chrome');
      if (w) w.classList.toggle('browser', framed);
      // a command you typed is a click, so the browser lets it open a real tab. The idle reel is not, and stays in the demo.
      var mine = Date.now() - lastUser < 4000;
      if (!framed && mine) { try { window.open(url, '_blank', 'noopener'); } catch (e) {} }
      return framed ? 'Opened ' + url + ' in Chrome. That is the live page.' : mine ? 'Opened ' + url + ' in a new tab, because that site does not allow being shown here.' : 'Opened ' + url + ' in Chrome.';
    },
    web_search: function (q) {
      var url = 'https://duckduckgo.com/?q=' + encodeURIComponent(q).replace(/%20/g, '+');
      desk.tab = { title: q + ' at DuckDuckGo', url: url };
      win('Google Chrome', 'Google Chrome', function (b) {
        b.appendChild(el('div', 'win-url', url));
        var a = el('a', 'win-link', 'Run this search for real');
        a.href = url; a.target = '_blank'; a.rel = 'noopener';
        b.appendChild(a);
      });
      var opened = "Searching for '" + q + "' in Chrome.";
      // same as tools.search_answer: a searched question is answered too, with its source. A list to browse is not.
      if (!/\?$/.test(q.trim()) && !/^(?:who|what|why|when|where|which|how|is|are|was|were|does|do|did)\b/i.test(q.trim())) return opened;
      return fetch('/api/ask', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ q: q }) })
        .then(function (r) { return r.json(); })
        .then(function (d) { return d && d.answer && d.source ? d.answer + ' (Source: ' + d.source + '.)\n' + opened : opened; })
        .catch(function () { return opened; });
    },
    current_tab: function () { return desk.tab ? desk.tab.title + '\n' + desk.tab.url : 'Chrome has no window open.'; },
    screenshot: function () {
      if (!reduceMotion) { space.classList.remove('flash'); void space.offsetWidth; space.classList.add('flash'); }
      $('desk-file').textContent = 'samantha-shot.png';
      return 'Saved ~/Desktop/samantha-shot.png.';
    },
    clipboard: function () { return desk.clipboard || 'The clipboard is empty.'; },
    set_volume: function (level) {
      var n = level === 'up' ? desk.volume + 15 : level === 'down' ? desk.volume - 15 : parseInt(level, 10);
      desk.volume = Math.max(0, Math.min(100, isNaN(n) ? desk.volume : n));
      if (gain) gain.gain.value = desk.volume / 100;
      return 'Volume at ' + desk.volume + '.';
    },
    battery: function () {
      if (!navigator.getBattery) return 'The stand-in Mac is plugged in. Your own battery is hidden by this browser.';
      return navigator.getBattery().then(function (b) {
        return 'Your battery: ' + Math.round(b.level * 100) + '%, ' + (b.charging ? 'charging' : 'on battery') + '. Read from your own device, not the stand-in.';
      });
    },
    say: function (text) {
      if (!reel && window.speechSynthesis) {
        var u = new SpeechSynthesisUtterance(text.slice(0, 500));
        u.volume = desk.volume / 100;
        speechSynthesis.speak(u);
      }
      return 'Saying: ' + text.slice(0, 80);
    },
    list_dir: function (p) {
      var full = path(p);
      if (full.indexOf('~') !== 0 || full.indexOf('..') >= 0 || !DIRS[full]) return 'No folder at "' + p + '" inside your home folder.';
      win('Finder', 'Finder: ' + full, function (b) { list(b, DIRS[full], 'Empty folder.'); });
      return DIRS[full].join(', ') || 'Empty folder.';
    },
    read_file: function (p) {
      var full = path(p);
      if (full.split('/').some(function (part) { return part[0] === '.' && part !== '..'; })) return "I don't read hidden files.";
      if (full.indexOf('~') !== 0 || full.indexOf('..') >= 0 || FILES[full] == null) return 'No file at "' + p + '" inside your home folder.';
      win('TextEdit', full.split('/').pop(), function (b) { b.appendChild(el('div', 'win-row', FILES[full])); });
      return FILES[full];
    },
    make_logo: function (desc) {
      var logo = drawLogo(desc);
      win('Logo', 'Logo', function (b) { b.appendChild(logo.svg.cloneNode(true)); });
      return { text: logo.text, node: logo.svg };
    },
    music: function (c) {
      if (c === 'playing') return desk.playing ? TRACKS[desk.track][0] + ' by Samantha' : 'Nothing is playing.';
      if (c === 'play') desk.playing = true;
      if (c === 'pause') desk.playing = false;
      if (c === 'next') { desk.track = (desk.track + 1) % TRACKS.length; desk.playing = true; }
      if (c === 'previous') { desk.track = (desk.track + TRACKS.length - 1) % TRACKS.length; desk.playing = true; }
      sound(desk.playing);
      return { play: 'Playing.', pause: 'Paused.', next: 'Skipped.', previous: 'Went back one.' }[c];
    },
    weather: function (place) {
      // wttr.in serves its one-line format as a whole HTML page to browsers, so ask for JSON. Its nearest area can be a suburb, so a named place keeps its name.
      var where = place.trim();
      return fetch('https://wttr.in/' + encodeURIComponent(where) + '?format=j1').then(function (r) { return r.json(); })
        .then(function (d) {
          var c = d.current_condition[0];
          return (where ? where.replace(/\b\w/g, function (l) { return l.toUpperCase(); }) : d.nearest_area[0].areaName[0].value) +
            ': ' + c.weatherDesc[0].value.trim() + ', ' + c.temp_C + '°C, feels ' + c.FeelsLikeC + '°C';
        })
        .catch(function () { return where ? 'No weather for "' + where + '".' : "Couldn't get the weather."; });
    },
    timer: function (minutes) {
      var secs = (/^[\d.]+$/.test(String(minutes).trim()) ? parseFloat(minutes) : S.duration(minutes)) * 60;
      if (!(secs > 0 && secs <= 86400)) return 'A timer runs from a second to a day.';
      desk.timerEnd = Date.now() + secs * 1000;
      return secs >= 60 ? 'Timer set for ' + (secs / 60) + ' minutes.' : 'Timer set for ' + secs + ' seconds.';
    },
    new_note: function (text) {
      desk.notes.push(text);
      if (!reel) save('notes', desk.notes);
      TOOLS.open_app('Notes');
      return 'Noted: ' + text.slice(0, 80);
    },
    new_reminder: function (text) {
      desk.reminders.push(text);
      if (!reel) save('reminders', desk.reminders);
      TOOLS.open_app('Reminders');
      return "I'll remind you: " + text.slice(0, 80);
    },
    calendar_today: function () { TOOLS.open_app('Calendar'); return 'Nothing on the calendar today.'; }
  };

  // ---- the page is hers too. Every change is local to this visitor and undone by "reset the page". ----
  var wrap = document.querySelector('.wrap'), h1 = document.querySelector('h1'), tagline = document.querySelector('header .sub');
  var original = { h1: h1.textContent, tagline: tagline.textContent };
  var paintNames = ['Mona Lisa', 'The Last Supper', 'The ENIAC'];
  function sections() { return Array.prototype.slice.call(document.querySelectorAll('section')).filter(function (x) { return x.querySelector('h2'); }); }
  function names() { return sections().map(function (x) { return x.querySelector('h2').textContent; }); }
  function find(arg) {
    var name = S.section(arg, names());
    if (name === 'top') return document.querySelector('header');
    if (name === 'bottom') return document.querySelector('footer') || sections().pop();
    return sections().filter(function (x) { return x.querySelector('h2').textContent === name; })[0] || null;
  }
  function label(node) { var h = node.querySelector('h2'); return h ? h.textContent : node.tagName === 'HEADER' ? 'the top' : 'the bottom'; }
  function go(node) { node.scrollIntoView({ behavior: reduceMotion ? 'auto' : 'smooth', block: 'start' }); }
  var zoom = 1;
  var lastPaintIndex = 0;
  var PAGE = {
    paint: function (cmd) {
      closeWins();  // the picture is the show: nothing sits on top of it
      var text = (cmd || '').toLowerCase().trim();
      var subject = text.replace(/^(?:me |us )?(?:an? |the |some )?(?:picture|painting|drawing|image|photo|sketch|illustration) of /, '').replace(/^(?:me |an? |the |some )+/, '').replace(/[.!?]+$/, '').trim();
      var index = -1;
      if (/mona|lisa/.test(text)) index = 0;
      else if (/supper/.test(text)) index = 1;
      else if (/eniac/.test(text)) index = 2;
      if (index < 0 && subject.length > 1 && !/^(?:it|that|this|again|another|something|anything)$/.test(subject)) return PAGE.draw(subject);
      if (index < 0) index = (lastPaintIndex + 1) % paintNames.length;
      lastPaintIndex = index;
      if (typeof window.samanthaPaint === 'function') window.samanthaPaint(index);
      return 'Painting ' + paintNames[index].replace(/^The /, 'the ').replace(/^Mona/, 'the Mona') + ' from 30,000 squares.';
    },
    // Anything at all. An image model on Cloudflare imagines it, then she rebuilds the picture from 30,000 squares in front of you.
    draw: function (what) {
      var subject = String(what).trim().slice(0, 120);
      if (!subject) return 'Draw what? Try "draw a lighthouse at dusk".';
      narrate('draw', subject);
      var was = statusEl.textContent;
      statusEl.textContent = 'Imagining ' + subject + '...';
      return fetch('/api/draw', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ q: subject }) })
        .then(function (r) { return r.json().then(function (d) { return { ok: r.ok, d: d }; }); })
        .then(function (x) {
          statusEl.textContent = was;
          if (!x.ok || !x.d.image) return x.d.answer || 'I could not draw that one.';
          window.samanthaPaintSrc(x.d.image, subject);
          return 'Here it is: ' + subject + '. An image model on Cloudflare imagined it, and I am rebuilding it from 30,000 squares.';
        })
        .catch(function () { statusEl.textContent = was; return 'I could not reach my image model just now.'; });
    },
    set_heading: function (text) { h1.textContent = text.slice(0, 60); go(document.querySelector('header')); return 'The title now says "' + h1.textContent + '". Only on your screen.'; },
    set_tagline: function (text) { userTagline = true; clearTimeout(typing); clearTimeout(backTimer); tagline.textContent = text.slice(0, 120); go(document.querySelector('header')); return 'Tagline changed.'; },
    scroll_to: function (where) {
      var w = where.toLowerCase().trim();
      if (w === 'down' || w === 'up') { window.scrollBy({ top: (w === 'down' ? 1 : -1) * window.innerHeight * 0.8, behavior: reduceMotion ? 'auto' : 'smooth' }); return 'Scrolled ' + w + '.'; }
      var node = find(where);
      if (!node) return "I don't see a part of this page called \"" + where + '".';
      go(node);
      return 'Scrolled to ' + label(node) + '.';
    },
    theme: function (mode) { document.documentElement.setAttribute('data-theme', mode); return mode === 'dark' ? 'Lights off.' : 'Lights on.'; },
    text_size: function (dir) {
      zoom = Math.max(0.8, Math.min(1.5, zoom + (dir === 'bigger' ? 0.15 : -0.15)));
      wrap.style.zoom = zoom;
      return 'Text is ' + (dir === 'bigger' ? 'bigger.' : 'smaller.');
    },
    set_color: function (name) { h1.style.color = S.COLORS[name.toLowerCase()]; go(document.querySelector('header')); return 'The title is ' + name.toLowerCase() + ' now.'; },
    hide: function (what) { var n = find(what); if (!n || n === sections()[0]) return "I'll keep that one where it is."; n.style.display = 'none'; return 'Hid ' + label(n) + '. Say "show ' + label(n).toLowerCase() + '" to bring it back.'; },
    show: function (what) { var n = find(what); if (!n) return "I don't see that part."; n.style.display = ''; go(n); return label(n) + ' is back.'; },
    highlight: function (what) {
      var n = find(what);
      if (!n) return "I don't see that part.";
      go(n); n.classList.remove('lit'); void n.offsetWidth; n.classList.add('lit');
      return 'Highlighted ' + label(n) + '.';
    },
    read_aloud: function (what) {
      var n = find(what);
      if (!n) return "I don't see that part.";
      go(n);
      var text = n.innerText.replace(/\s+/g, ' ').slice(0, 600);
      if (!reel && window.speechSynthesis) { speechSynthesis.cancel(); var u = new SpeechSynthesisUtterance(text); u.volume = desk.volume / 100; speechSynthesis.speak(u); }
      return 'Reading ' + label(n) + ' out loud. Say "pause" style commands won\'t stop me, "reset the page" will.';
    },
    barrel_roll: function () {
      if (reduceMotion) return "Your system asked for less motion, so I'll sit this one out.";
      wrap.classList.remove('roll'); void wrap.offsetWidth; wrap.classList.add('roll');
      return 'Wheee.';
    },
    reset_page: function () {
      h1.textContent = original.h1; userTagline = false; clearTimeout(typing); clearTimeout(backTimer); tagline.textContent = original.tagline; h1.style.color = ''; zoom = 1; wrap.style.zoom = '';
      document.documentElement.removeAttribute('data-theme');
      sections().forEach(function (x) { x.style.display = ''; });
      if (window.speechSynthesis) speechSynthesis.cancel();
      return 'Page is back to how Joshua left it.';
    }
  };
  Object.keys(PAGE).forEach(function (k) { TOOLS[k] = PAGE[k]; });
  // the utility tools run for real here, the same code as tools_util.py (eval/util_diff.py keeps the two honest)
  Object.keys(S.util).forEach(function (k) { if (typeof S.util[k] === 'function') TOOLS[k] = S.util[k]; });

  setInterval(function () {
    if (desk.timerEnd && Date.now() >= desk.timerEnd) {
      desk.timerEnd = 0;
      say(null, [], 'Time is up.');
      if (!reel) TOOLS.say('Time is up');
    }
    paintBar();
  }, 500);

  // ---- the transcript ----
  function addUser(text) {
    var d = el('div', 'chat-message chat-user', text);
    transcript.appendChild(d);
    transcript.scrollTop = transcript.scrollHeight;
  }
  function say(_, calls, text, extra, done) {
    text = String(text || '').slice(0, 1200); // no upstream gets to fill the transcript
    var d = el('div', 'chat-message');
    (calls || []).forEach(function (c) { d.appendChild(el('div', 'chat-tool-call', c)); });
    var body = el('div', 'chat-message-content');
    body.style.whiteSpace = 'pre-line';
    d.appendChild(body);
    transcript.appendChild(d);
    var i = 0;
    (function type() {
      i = typing ? Math.min(text.length, i + 3) : text.length;
      body.textContent = text.slice(0, i);
      transcript.scrollTop = transcript.scrollHeight;
      if (i < text.length) return setTimeout(type, typing);
      if (extra && extra.node) { var pic = el('div', 'chat-logo'); pic.appendChild(extra.node); d.appendChild(pic); }
      if (extra && extra.source) d.appendChild(el('div', 'chat-source', extra.source));
      var all = transcript.querySelectorAll('.chat-message');
      for (var k = 0; k < all.length - 14; k++) all[k].remove();
      transcript.scrollTop = transcript.scrollHeight;
      if (done) done();
    })();
  }

  var SMALLTALK = [
    [/^(?:hi|hello|hey|yo|good (?:morning|evening|afternoon))\b/i, "Hi. Ask me something, or tell me to do something on the Mac up there."],
    [/^(?:thanks|thank you|cheers|nice|cool)\b/i, 'Any time.'],
    [/^(?:who are you|what are you)\b/i, "I'm Samantha, a 0.5B model fine-tuned on one Mac Mini. I look facts up instead of guessing, and I have hands for the Mac I live on."],
    [/^(?:what can you do|help|what do you do)\b/i, 'Open apps and sites, search, set the volume, play and skip music, timers, notes, reminders, weather, screenshots, logos, arithmetic, and look things up. Try "set a timer for 1 minute" or "who painted the mona lisa".']
  ];
  var faq = null;
  function fromFaq(q) {
    if (!faq) return null;
    var kq = S.keywords(q), best = null, top = 0;
    faq.forEach(function (f) {
      var kh = S.keywords(f.q), shared = kq.filter(function (k) { return kh.indexOf(k) >= 0; }).length;
      var score = shared / Math.sqrt((kq.length || 1) * (kh.length || 1));
      if (score > top) { top = score; best = f; }
    });
    return top >= 0.5 ? best.a : null;
  }

  // ---- the hero line narrates the demo: what she is doing right now, typed out, then back to the tagline. Joshua Tree's eyebrow does the same. ----
  var typing = 0, backTimer = 0, userTagline = false;
  function say_hero(text) {
    clearTimeout(typing); clearTimeout(backTimer);
    if (reduceMotion) { tagline.textContent = text; return; }
    var i = 0;
    (function type() { tagline.textContent = text.slice(0, ++i); if (i < text.length) typing = setTimeout(type, 16); })();
  }
  var STORY = {
    paint: function () { return 'Rebuilding a painting from 30,000 squares.'; },
    draw: function (a) { return 'Imagining ' + a.slice(0, 50) + ', then rebuilding it square by square.'; },
    make_logo: function () { return 'Designing a logo dial by dial. Her model picks, the code draws.'; },
    set_volume: function () { return 'Turning the volume on a stand-in Mac.'; },
    open_app: function () { return 'Opening an app on a stand-in Mac.'; },
    open_url: function () { return 'Opening a site on a stand-in Mac.'; },
    web_search: function () { return 'Searching the web for you.'; },
    weather: function () { return 'Checking the weather live.'; },
    timer: function () { return 'Starting a timer on the stand-in Mac.'; },
    new_note: function () { return 'Writing a note. On a real Mac it asks first.'; },
    new_reminder: function () { return 'Adding a reminder. On a real Mac it asks first.'; },
    music: function () { return 'Driving the music player.'; },
    screenshot: function () { return 'Taking a screenshot.'; },
    set_heading: function () { return 'Rewriting this page. Only on your screen.'; },
    scroll_to: function () { return 'Scrolling this page for you.'; },
    theme: function () { return 'Switching this page between light and dark.'; },
    reset_page: function () { return 'Putting the page back the way Joshua left it.'; }
  };
  function narrate(tool, arg) {
    if (userTagline || tool === 'set_tagline') return;
    var line = (STORY[tool] || function () { return 'Using her ' + tool.replace(/_/g, ' ') + ' tool. No model needed.'; })(String(arg || ''));
    say_hero(line);
    backTimer = setTimeout(function () { say_hero(original.tagline); }, 7000);
  }

  function runTool(tool, arg) {
    narrate(tool, arg);
    var call = '[' + tool + '(' + arg + ')]';
    return Promise.resolve(TOOLS[tool](arg)).then(function (out) {
      return typeof out === 'string' ? { call: call, text: out } : { call: call, text: out.text, node: out.node };
    });
  }

  // multi-step: on the Mac a 1.7B drives this. Here, steps that each route on their own run in order.
  function agent(q) {
    if (/\b(?:hacker news|hn)\b/i.test(q)) {
      return fetch('https://hacker-news.firebaseio.com/v0/topstories.json').then(function (r) { return r.json(); }).then(function (ids) {
        return Promise.all(ids.slice(0, 3).map(function (id) {
          return fetch('https://hacker-news.firebaseio.com/v0/item/' + id + '.json').then(function (r) { return r.json(); });
        }));
      }).then(function (items) {
        return { calls: ['[read_page(https://news.ycombinator.com)]'], source: 'Live from Hacker News, just now',
                 text: 'Top of Hacker News right now:\n' + items.map(function (it, i) { return (i + 1) + '. ' + it.title + ' (' + it.score + ' points)'; }).join('\n') };
      }).catch(function () { return { calls: [], text: "I couldn't reach Hacker News." }; });
    }
    var parts = S.bare(q).split(/\s*(?:,? and then |,? then |,? and )\s*/i).map(function (p) {
      return S.route(p.replace(/^(?:tell me|show me|give me|read me)\s+(?:my |the )?/i, ''));
    });
    if (parts.length < 2 || !parts.every(function (r) { return r && r.tool; }))
      return Promise.resolve({ calls: [], text: 'That one takes my multi-step head, a 1.7B model that only runs on the Mac. One step at a time works here.' });
    var calls = [], last = '';
    return parts.reduce(function (chain, r) {
      return chain.then(function () { return runTool(r.tool, r.arg); }).then(function (o) { calls.push(o.call); last = o.text; });
    }, Promise.resolve()).then(function () { return { calls: calls, text: last }; });
  }

  // Real feedback (feedback.py) writes to a file only the real Mac has; the landing page has nowhere private to put
  // it, so it says so instead of pretending, same words either way. Caught here first, before any route or tool.
  var FEEDBACK_UP = /^(?:good|thanks,? that'?s right|👍|\+1)[.!]*$/i;
  var FEEDBACK_DOWN = /^(?:bad|wrong|that'?s not what i meant|👎|-1)[.!]*$/i;
  var FEEDBACK_CORRECTION = /^wrong,?\s*i meant\s+.+$/i;
  var FEEDBACK_SUMMARY = /^(?:how am i rating you|show my feedback)\??$/i;

  function answer(q) {
    var bareQ = S.bare(q);
    if (FEEDBACK_UP.test(bareQ) || FEEDBACK_DOWN.test(bareQ) || FEEDBACK_CORRECTION.test(bareQ) || FEEDBACK_SUMMARY.test(bareQ))
      return Promise.resolve({ text: "On her real Mac that rating is saved locally so she learns from it." });
    var exact = S.exact(q);
    if (exact) return Promise.resolve({ text: exact });
    // bare() strips "can you", "please" and the rest, the same as every other command
    var plain = S.bare(q), paintMatch = /^(?:paint|repaint|draw|imagine|sketch|illustrate|(?:generate|make|create)(?: me)?(?: an?)?(?: image| picture| painting| drawing| photo) of)\b/i.exec(plain);
    if (paintMatch) return runTool('paint', plain.slice(paintMatch[0].length)).then(function (o) { return { calls: [o.call], text: o.text, node: o.node }; });
    var steps = S.chain(q);
    if (steps) return steps.reduce(function (chain, r) {
      return chain.then(function (acc) { return runTool(r.tool, r.arg).then(function (o) { acc.calls.push(o.call); acc.text.push(o.text); return acc; }); });
    }, Promise.resolve({ calls: [], text: [] })).then(function (a) { return { calls: a.calls, text: a.text.join('\n') }; });
    var r = S.pageRoute(q, names()) || S.route(q);
    if (r && r.tool) return runTool(r.tool, r.arg).then(function (o) { return { calls: [o.call], text: o.text, node: o.node }; });
    if (r && r.agent) return agent(q);
    for (var i = 0; i < SMALLTALK.length; i++) if (SMALLTALK[i][0].test(q.trim())) return Promise.resolve({ text: SMALLTALK[i][1] });
    if (S.isProject(q)) {
      var known = fromFaq(q);
      if (known) return Promise.resolve({ text: known, source: 'From the project FAQ' });
    }
    // No rule matched. If it does not read like a question, a model gets to pick a tool, and the pick has to pass the guard.
    var plain = S.bare(q);
    var asking = /\?$/.test(q.trim()) || /^(?:who|what|why|when|where|which|how|is|are|was|were|does|do|did|tell me about|explain|describe|define)\b/i.test(plain);
    if (!asking) {
      return fetch('/api/pick', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ q: q, sections: names() }) })
        .then(function (res) { return res.json(); })
        .then(function (p) {
          if (p && p.tool && TOOLS[p.tool] && S.sound(p.tool, p.arg, q, names()))
            return runTool(p.tool, String(p.arg || '')).then(function (o) { return { calls: ['no rule for that, so a model picked:', o.call], text: o.text, node: o.node }; });
          return lookup(q);
        }).catch(function () { return lookup(q); });
    }
    return lookup(q);
  }

  function lookup(q) {
    return fetch('/api/ask', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ q: q }) })
      .then(function (res) { return res.json(); })
      .then(function (d) { return { text: d.answer, source: d.source ? d.source + (d.read ? ', read by the 3B stand-in' : '') : '' }; })
      .catch(function () { return { text: "I couldn't reach my lookup just now." }; });
  }

  function send(question, done) {
    var q = (question || input.value).trim().slice(0, 200);
    if (!q) return;
    // She is still answering: don't drop what was typed, hold it and send it the moment she's free.
    if (busy) { pending = { q: q, done: done }; input.value = ''; return; }
    busy = true;
    input.value = '';
    addUser(q);
    var finish = function () {
      busy = false; paintBar(); if (done) done();
      if (pending) { var p = pending; pending = null; send(p.q, p.done); }
    };
    if (isLive) {
      fetch(LOCAL, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ model: 'samantha', messages: [{ role: 'user', content: q }] }) })
        .then(function (r) { return r.json(); })
        .then(function (d) { say(null, [], ((d.choices || [])[0] || { message: { content: 'No response.' } }).message.content, null, finish); })
        .catch(function (e) { say(null, [], 'Error: ' + e, null, finish); });
      return;
    }
    answer(q).then(function (a) { say(null, a.calls, a.text || '', { node: a.node, source: a.source }, finish); });
  }

  // No theme commands and no barrel roll in the reel: moving a visitor's whole page unasked reads as a bug.
  // ---- idle reel: if nobody types, she shows what she does. Silent, and it stops the moment you touch anything ----
  var REEL = ['paint the mona lisa', 'open chrome and go to en.wikipedia.org/wiki/Alan_Turing', 'set the volume to 40', 'paint the eniac',
              'what is 17*23', 'make me a complex logo for a surf school', 'make me an original wordless logo for turing', "what's the weather in tokyo", 'play some music', 'skip this song', 'paint the last supper',
              'who painted the mona lisa', 'scroll to the results', 'take a screenshot', 'draw a lighthouse at dusk', 'draw a fox in the snow', 'calculate 17*23', 'convert 72 f to c', 'time in tokyo', 'roll 2d6', 'is 91 prime', 'days until christmas', 'who invented the telephone', 'reset the page'];
  // more phrasings for the input's autocomplete only. The reel stays short.
  var MORE = ['what are my reminders', 'search notes for eggs', 'what apps are running', 'turn on dark mode', 'git status', 'recent commits', 'take a note pick up milk', 'set a timer for 1 minute', 'open chrome and go to github.com', 'change the title to Hello there', 'draw a robot reading a book', 'draw a sailboat on a calm lake', 'imagine a city on the moon', 'do a barrel roll', 'tip on 45', 'roman numerals for 2026', 'sha256 of turing', 'base64 encode hello', 'morse sos', 'flip a coin', 'generate a strong password',
              'make a uuid', 'random number between 1 and 100', 'count words in the quick brown fox', 'reverse the text hello', 'what day is it',
              'convert 5 km to miles', 'calculate 15% of 80', 'factor 84', 'time in london', 'days until halloween', 'how much disk space do i have', 'edit notes.md: make it shorter', 'write a python script that prints the date to today.py'];
  var reelAt = 0;
  function stopReel() { reel = false; clearTimeout(reelTimer); clearTimeout(idleTimer); }
  function nextReel() {
    if (!reel) return;
    var q = REEL[reelAt++ % REEL.length], i = 0;
    (function typeIn() {
      if (!reel) { input.value = ''; return; }
      input.value = q.slice(0, ++i);
      if (i < q.length) return void (reelTimer = setTimeout(typeIn, 40));
      reelTimer = setTimeout(function () { if (reel) send(q, function () { reelTimer = setTimeout(nextReel, 2600); }); }, 400);
    })();
  }
  function idle() {
    stopReel();
    if (reduceMotion || isLive || document.hidden) return;
    idleTimer = setTimeout(function () { if (!busy) { reel = true; desk.playing = false; nextReel(); } }, Date.now() - lastUser < 90000 ? 30000 : reelAt ? 6000 : 2200);  // a visitor's own drawing stays 30 seconds
  }

  function startDemo() {
    statusEl.textContent = 'Live demo. She controls the stand-in Mac and this page. Ask her to draw anything: an image model on Cloudflare imagines it and she rebuilds it from 30,000 squares. A 3B on Cloudflare stands in for the models on her Mac.';
    say(null, [], "I'm Samantha. Tell me to do something, to the Mac up there or to this page, or ask me something. Type anything.");
    // No buttons. The reel shows what she does, and the same lines feed the input's native autocomplete.
    var suggest = $('chat-suggest');
    REEL.concat(MORE).forEach(function (q) { var o = document.createElement('option'); o.value = q; suggest.appendChild(o); });
    fetch('faq.json').then(function (r) { return r.json(); }).then(function (f) { faq = f; }).catch(function () {});
    idle();
  }

  $('chat-send').addEventListener('click', function () { lastUser = Date.now(); stopReel(); send(null, idle); });
  input.addEventListener('keydown', function (e) {
    stopReel();
    if (e.key === 'Enter') { e.preventDefault(); lastUser = Date.now(); send(null, idle); }
  });
  ['pointerdown', 'touchstart'].forEach(function (ev) { document.addEventListener(ev, function () { if (reel) { stopReel(); input.value = ''; } idle(); }, true); });
  document.addEventListener('visibilitychange', idle);

  // ---- borrowed from Joshua Tree's landing: sections ease in on scroll, and the demo can fill the screen ----
  (function () {
    document.documentElement.classList.add('js');
    var secs = Array.prototype.slice.call(document.querySelectorAll('section')).slice(1);
    if ('IntersectionObserver' in window && !reduceMotion) {
      var io = new IntersectionObserver(function (es) {
        es.forEach(function (e) { if (e.isIntersecting) { e.target.classList.add('in'); io.unobserve(e.target); } });
      }, { threshold: 0.06, rootMargin: '0px 0px -6% 0px' });
      secs.forEach(function (s) { s.classList.add('reveal'); io.observe(s); });
    }
    var btn = $('demo-full'), card = btn && btn.closest('.card');
    function setFull(on) {
      card.classList.toggle('full', on); document.documentElement.classList.toggle('noscroll', on);
      btn.textContent = on ? 'Exit full screen' : 'Full screen'; btn.setAttribute('aria-pressed', on ? 'true' : 'false');
      if (on) input.focus();
    }
    if (btn && card) {
      btn.addEventListener('click', function () { setFull(!card.classList.contains('full')); });
      document.addEventListener('keydown', function (e) { if (e.key === 'Escape' && card.classList.contains('full')) setFull(false); });
    }
  })();

  paintBar();
  // Joshua's own Mac runs the real thing on a local port. Only look for it when asked (?local) or when the page itself is
  // local: probing localhost from a public page shows every visitor a connection error, or a permission prompt in newer Chrome.
  if (!/[?&]local\b/.test(location.search) && !/^(?:localhost|127\.0\.0\.1)$/.test(location.hostname)) { startDemo(); return; }
  fetch(LOCAL, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ model: 'samantha', messages: [{ role: 'user', content: 'hi' }] }) })
    .then(function (r) {
      if (!r.ok) return startDemo();
      isLive = true;
      $('desk').style.display = 'none';
      statusEl.textContent = 'Live, talking to Samantha on this Mac';
      say(null, [], "I'm Samantha. Live on this Mac. Ask me anything.");
    }).catch(startDemo);
})();
