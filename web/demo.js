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
  var isLive = false, busy = false, reel = false, idleTimer = 0, reelTimer = 0;
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
  function initials(desc) {
    var called = /\b(?:called|named)\s+(\w)/i.exec(desc);
    if (called) return called[1];
    var words = (desc.toLowerCase().match(/[a-z0-9]+/g) || []).filter(function (w) {
      return !/^(?:a|an|the|my|our|for|of|about|and|most|ever|logo|icon|complex|intricate|detailed|elaborate|ornate|fancy|crazy|insane)$/.test(w);
    });
    return ((words[0] || 's')[0] + (words.length > 1 && words.length < 4 ? words[1][0] : '')).slice(0, 2);
  }
  function drawLogo(desc) {
    var h = hash(desc.toLowerCase()), fancy = /\b(?:complex|intricate|detailed|elaborate|ornate|fancy|crazy|insane)\b/i.test(desc);
    var names = Object.keys(PALETTES), palette = names[h % names.length], p = PALETTES[palette];
    var tile = p[0], ink = p[1], accent = p[2], letters = initials(desc).toUpperCase(), C = 512;
    var root = svg('svg', { viewBox: '0 0 1024 1024', role: 'img', 'aria-label': 'Logo: ' + letters });
    root.appendChild(svg('rect', { x: 72, y: 72, width: 880, height: 880, rx: 200, fill: tile }));
    function mark(size) {
      var t = svg('text', { x: C, y: C, 'text-anchor': 'middle', 'dominant-baseline': 'central', fill: ink,
                            'font-family': 'Helvetica Neue, Helvetica, Arial, sans-serif', 'font-weight': 700, 'font-size': size });
      t.textContent = letters;
      root.appendChild(t);
    }
    var chose, layers;
    if (!fancy) {
      var motif = ['ring', 'spark', 'underline', 'dot'][(h >>> 3) % 4];
      if (motif === 'ring') root.appendChild(svg('circle', { cx: C, cy: C, r: 320, fill: 'none', stroke: accent, 'stroke-width': 28 }));
      mark(letters.length === 1 ? 340 : 280);
      if (motif === 'spark') root.appendChild(star(765, 265, 150, 4, 35, accent));
      if (motif === 'underline') root.appendChild(svg('rect', { x: 362, y: 730, width: 300, height: 28, rx: 14, fill: accent }));
      if (motif === 'dot') root.appendChild(svg('circle', { cx: 745, cy: 685, r: 45, fill: accent }));
      chose = 'letters ' + letters + ', palette ' + palette + ', motif ' + motif;
      layers = motif === 'ring' || motif === 'spark' || motif === 'underline' || motif === 'dot' ? 3 : 2;
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
      mark(letters.length === 1 ? 190 : 150);
      chose = 'letters ' + letters + ', palette ' + palette + ', rings ' + rings + ', rays ' + rays + ', ray_style ' + style +
              ', orbit_dots ' + orbit + ', star_points ' + points;
      layers = 1 + rays + rings + orbit + 3;
    }
    return { svg: root, text: 'I went with ' + chose + '. ' + layers + ' layers. Here a hash of your words turns the dials. On the Mac a 1.7B picks them and Pixelmator builds it.' };
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
      desk.tab = { title: url.replace(/^https?:\/\//, ''), url: url };
      win('Google Chrome', 'Google Chrome', function (b) {
        b.appendChild(el('div', 'win-url', url));
        var a = el('a', 'win-link', 'Open it for real');
        a.href = url; a.target = '_blank'; a.rel = 'noopener';
        b.appendChild(a);
      });
      return 'Opened ' + url + ' in Chrome.';
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
      return "Searching for '" + q + "' in Chrome.";
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
      if (!navigator.getBattery) return "Now drawing from 'AC Power'.";
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
      win('Pixelmator Pro', 'Pixelmator Pro', function (b) { b.appendChild(logo.svg.cloneNode(true)); });
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
      return fetch('https://wttr.in/' + encodeURIComponent(place.trim()) + '?format=%l:+%C,+%t,+feels+%f').then(function (r) { return r.text(); })
        .then(function (t) { return t.indexOf('°') >= 0 ? t.trim() : 'No weather for "' + place + '".'; })
        .catch(function () { return "Couldn't get the weather."; });
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
  var PAGE = {
    set_heading: function (text) { h1.textContent = text.slice(0, 60); go(document.querySelector('header')); return 'The title now says "' + h1.textContent + '". Only on your screen.'; },
    set_tagline: function (text) { tagline.textContent = text.slice(0, 120); go(document.querySelector('header')); return 'Tagline changed.'; },
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
      h1.textContent = original.h1; tagline.textContent = original.tagline; h1.style.color = ''; zoom = 1; wrap.style.zoom = '';
      document.documentElement.removeAttribute('data-theme');
      sections().forEach(function (x) { x.style.display = ''; });
      if (window.speechSynthesis) speechSynthesis.cancel();
      return 'Page is back to how Joshua left it.';
    }
  };
  Object.keys(PAGE).forEach(function (k) { TOOLS[k] = PAGE[k]; });

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

  function runTool(tool, arg) {
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

  function answer(q) {
    var exact = S.exact(q);
    if (exact) return Promise.resolve({ text: exact });
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
    if (!q || busy) return;
    busy = true;
    input.value = '';
    addUser(q);
    var finish = function () { busy = false; paintBar(); if (done) done(); };
    if (isLive) {
      fetch(LOCAL, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ model: 'samantha', messages: [{ role: 'user', content: q }] }) })
        .then(function (r) { return r.json(); })
        .then(function (d) { say(null, [], ((d.choices || [])[0] || { message: { content: 'No response.' } }).message.content, null, finish); })
        .catch(function (e) { say(null, [], 'Error: ' + e, null, finish); });
      return;
    }
    answer(q).then(function (a) { say(null, a.calls, a.text || '', { node: a.node, source: a.source }, finish); });
  }

  // ---- idle reel: if nobody types, she shows what she does. Silent, and it stops the moment you touch anything ----
  var REEL = ['change the title to Hello there', 'open chrome and go to github.com', 'set the volume to 40', 'take a note the demo is live', 'what is 17*23', 'make me a logo for turing',
              "what's the weather in tokyo", 'play some music', 'skip this song', 'who painted the mona lisa', 'take a screenshot', 'reset the page'];
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
    idleTimer = setTimeout(function () { if (!busy) { reel = true; desk.playing = false; nextReel(); } }, 6000);
  }

  function startDemo() {
    statusEl.textContent = 'Live demo. Her real command rules run in your browser. What the rules miss, a small model picks a tool for, and a guard checks the pick. ' +
      'She can act on the stand-in Mac and on this page itself. A 3B on Cloudflare stands in for the models on her Mac.';
    say(null, [], "I'm Samantha. Tell me to do something, to the Mac up there or to this page, or ask me something. Type anything.");
    var chips = $('chat-chips');
    ['change the title to Hello Joshua', 'dark mode', 'scroll to the results', 'do a barrel roll', 'play some music', 'set a timer for 1 minute',
     'make me a complex logo for a surf school', 'who invented the telephone', 'reset the page'].forEach(function (q) {
      var chip = el('button', 'chat-chip', q);
      chip.type = 'button';
      chip.addEventListener('click', function () { stopReel(); send(q, idle); });
      chips.appendChild(chip);
    });
    fetch('faq.json').then(function (r) { return r.json(); }).then(function (f) { faq = f; }).catch(function () {});
    idle();
  }

  $('chat-send').addEventListener('click', function () { stopReel(); send(null, idle); });
  input.addEventListener('keydown', function (e) {
    stopReel();
    if (e.key === 'Enter') { e.preventDefault(); send(null, idle); }
  });
  ['pointerdown', 'touchstart'].forEach(function (ev) { document.addEventListener(ev, function () { if (reel) { stopReel(); input.value = ''; } idle(); }, true); });
  document.addEventListener('visibilitychange', idle);

  paintBar();
  // Joshua's own Mac runs the real thing on a local port. Everyone else gets the demo.
  fetch(LOCAL, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ model: 'samantha', messages: [{ role: 'user', content: 'hi' }] }) })
    .then(function (r) {
      if (!r.ok) return startDemo();
      isLive = true;
      $('desk').style.display = 'none';
      statusEl.textContent = 'Live, talking to Samantha on this Mac';
      say(null, [], "I'm Samantha. Live on this Mac. Ask me anything.");
    }).catch(startDemo);
})();
