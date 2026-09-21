// Samantha's router and exact answers, ported from tools.py and ask.py so the
// landing page runs the real logic instead of replaying a recording. No DOM in
// here: the page, the Worker and the node parity check all load this one file.
// eval/web_parity.py feeds eval/actions.py through route() and fails if this
// file and tools.py ever disagree.
(function (root) {
  var SITES = {
    "hacker news": "https://news.ycombinator.com", "hn": "https://news.ycombinator.com",
    "github": "https://github.com", "youtube": "https://youtube.com",
    "gmail": "https://mail.google.com", "reddit": "https://reddit.com",
    "twitter": "https://x.com", "x": "https://x.com"
  };
  // the stand-in Mac's /Applications
  var APPS = ["Safari", "Google Chrome", "Notes", "Mail", "Calendar", "Music", "Reminders", "Pixelmator Pro", "Terminal",
              "Finder", "Messages", "Photos", "Preview", "Maps", "Calculator", "TextEdit", "Weather", "Xcode"];

  function appMatch(name) {
    var key = name.trim().toLowerCase().replace(/^(?:the |my )|(?: app)$/g, "");
    if (key === "chrome") key = "google chrome";
    var sorted = APPS.slice().sort();
    return sorted.find(function (a) { return a.toLowerCase() === key; }) ||
           sorted.find(function (a) { return a.toLowerCase().indexOf(key) === 0; }) || null;
  }

  function urlOf(target) {
    var t = target.trim().replace(/^["']+|["']+$/g, "");
    if (SITES[t.toLowerCase()]) return SITES[t.toLowerCase()];
    if (/^https?:\/\//i.test(t)) return t;
    if (/^[\w-]+(\.[\w-]+)+(\/\S*)?$/.test(t)) return "https://" + t;
    return null;
  }

  var UNIT = { s: 1 / 60, m: 1, h: 60 };
  // same table, same order as _ROUTES in tools.py. First match wins.
  var ROUTES = [
    [/^(?:play|resume)(?: (?:the |some |my )?(?:music|song|tunes))?$/i, function () { return ["music", "play"]; }],
    [/^pause$|^(?:pause|stop) (?:the |my |this )?(?:music|song|track)$/i, function () { return ["music", "pause"]; }],
    [/^(?:skip|next)(?: (?:this |the )?(?:song|track|one))?$/i, function () { return ["music", "next"]; }],
    [/^(?:previous|last|go back a|go back one)(?: (?:song|track))?$/i, function () { return ["music", "previous"]; }],
    [/^what(?:'s| is) (?:this song|playing)\b|^what song is (?:this|playing)/i, function () { return ["music", "playing"]; }],
    [/^(?:what(?:'s| is) the |how(?:'s| is) the )?weather\b(?: like)?(?: today| outside| right now| now)*(?: (?:in|for) (.+))?$/i,
     function (m) { return ["weather", m[1] || ""]; }],
    [/^(?:set |start )?(?:a |an )?(?:timer (?:for )?(\d+(?:\.\d+)?) ?(s|m|h)\w*|(\d+(?:\.\d+)?)[ -]?(s|m|h)\w* timer)$/i,
     function (m) { return ["timer", String(parseFloat(m[1] || m[3]) * UNIT[(m[2] || m[4]).toLowerCase()])]; }],
    [/^remind me (?:to |that |about )?(.+)$|^(?:add|create|make|set|new) (?:a |me a )?(?:new )?reminder(?: to| that says| saying|:)? (.+)$/i,
     function (m) { return ["new_reminder", m[1] || m[2]]; }],
    [/^(?:(?:make|create|take|write|add|new) (?:a |me a )?(?:new )?note|note)(?: that says| saying| that|:)? (.+)$/i,
     function (m) { return ["new_note", m[1]]; }],
    [/^what(?:'s| is) on (?:my |the )?(?:calendar|schedule|agenda)\b|^(?:my )?(?:calendar|schedule|agenda)(?: for)?(?: today)?$|^what do i have (?:on )?today/i,
     function () { return ["calendar_today", ""]; }],
    [/^(?:make|design|draw|create|build)(?: me)? (?:a |an )?(complex |intricate |detailed |elaborate |ornate |fancy |crazy |insane )?(?:logo|icon)(?: for| of)? (.+)$/i, function (m) { return ["make_logo", (m[1] || "") + m[2]]; }],
    [/^(?:(?:show me |tell me )?what(?:'s| is) (?:on|in) (?:my |the )?clipboard|(?:read|show)(?: me)? (?:my |the )?clipboard)\b/i, function () { return ["clipboard", ""]; }],
    [/^(?:set |turn |put )?(?:the |it |my )?(?:volume )?(?:up |down )?(?:to |at )(\d{1,3})\b/i, function (m) { return ["set_volume", m[1]]; }],
    [/^(?:set |turn )?(?:the )?volume (\d{1,3})\b/i, function (m) { return ["set_volume", m[1]]; }],
    [/^(?:turn )?(?:the |it )?(?:volume )?(up|down)$|^(?:turn )?(?:the )?volume (up|down)$|^(louder|quieter)$/i,
     function (m) { return ["set_volume", /up|louder/i.test(m[1] || m[2] || m[3]) ? "up" : "down"]; }],
    [/^mute\b/i, function () { return ["set_volume", "0"]; }],
    [/^(?:how(?:'s| is) (?:my |the )?battery|battery(?: level| status)?$|what(?:'s| is) (?:my |the )?battery|how much battery)/i, function () { return ["battery", ""]; }],
    [/^say (.+)$/i, function (m) { return ["say", m[1]]; }],
    [/^(?:list|show)(?: me)? (?:the )?(?:files|folder|contents) (?:in|of|at) (.+)$/i, function (m) { return ["list_dir", m[1]]; }],
    [/^(?:read|show|cat)(?: me)? (?:the )?file (.+)$/i, function (m) { return ["read_file", m[1]]; }],
    [/^(?:take a |grab a )?screenshot\b/i, function () { return ["screenshot", ""]; }],
    [/^what(?:'s| is) (?:on |in )?(?:my |the )?(?:current |open )?(?:tab|chrome|browser)\b/i, function () { return ["current_tab", ""]; }],
    [/^(?:search|google|look up)(?: the web)?(?: for)? (.+)$/i, function (m) { return ["web_search", m[1]]; }],
    [/^(?:open|launch|start) (?:up )?(?:chrome|the browser) (?:and |then )?(?:go to|open|visit|load) (.+)$/i, function (m) { return ["open_url", m[1]]; }],
    [/^(?:go to|visit|browse to|pull up) (.+)$/i, function (m) { return ["open_url", m[1]]; }],
    [/^(?:open|launch|start) (?:up )?(.+)$/i, function (m) {
      var g = m[1];
      return urlOf(g) || (g.trim().indexOf(" ") >= 0 && !appMatch(g)) ? ["open_url", g] : ["open_app", g];
    }]
  ];
  var MULTISTEP = /\b(?:and (?:then )?(?:tell|read|find|summar|poke|look|check|see|click)|poke around|then )/i;
  var ACTION = /^(?:open|launch|start|go to|visit|browse|pull up|search|google|look up|poke around|take a|grab a|screenshot|make|design|draw|play|pause|skip|remind me|set a)\b/i;
  var LEAD = /^(?:(?:hey|ok|okay|yo|samantha|please|now|just)[, ]+)*(?:(?:can|could|would|will) you (?:please )?|i (?:want|need|would like|'d like) (?:you )?to |let's |go ahead and )?(?:please )?/i;
  var TAIL = /(?:[, ]+(?:please|for me|real quick|now|thanks|thank you))+$/i;

  function bare(query) {
    return query.trim().replace(/[.!?]+$/, "").replace(LEAD, "").replace(TAIL, "").trim();
  }

  // {tool, arg} for one exact command, {agent: true} for multi-step work, null for anything that is not a command
  function route(query) {
    var q = bare(query);
    if (MULTISTEP.test(q)) return { agent: true };
    for (var i = 0; i < ROUTES.length; i++) {
      var m = ROUTES[i][0].exec(q);
      if (m) { var r = ROUTES[i][1](m); return { tool: r[0], arg: r[1] }; }
    }
    return ACTION.test(q) ? { agent: true } : null;
  }

  // ---- the page itself is a thing she can act on. Landing page only: tools.py has no page. ----
  var COLORS = { red: "#c0392b", orange: "#d9701a", amber: "#c98a14", gold: "#b8901f", green: "#2e9e4a", blue: "#2b6cb0", pink: "#d6457f",
                 black: "#111111", white: "#ffffff", grey: "#777777", gray: "#777777" };

  // which part of the page a phrase means, or null. names are the page's own section headings.
  function section(arg, names) {
    var a = arg.trim().toLowerCase().replace(/^(?:the |that |this )/, "").replace(/ (?:section|part|bit|area)$/, "");
    if (/^(?:top|start|beginning|header|up)$/.test(a)) return "top";
    if (/^(?:bottom|end|footer|down)$/.test(a)) return "bottom";
    if (/^(?:chat|demo|mac|desk)$/.test(a)) return names[0] || null;
    var want = keywords(a), best = null, top = 0;
    names.forEach(function (n) {
      var have = keywords(n), hit = want.filter(function (k) { return have.indexOf(k) >= 0; }).length;
      if (hit > top) { top = hit; best = n; }
    });
    return best;
  }

  var PAGE_ROUTES = [
    [/^(?:make|turn|paint|color|colour) (?:the |this )?(?:page|site|title|heading|h1|accent|everything) (red|orange|amber|gold|green|blue|pink|black|white|grey|gray)$/i, "set_color"],
    [/^(?:change|set|make|rename|update|edit) (?:the |this |your )?(?:h1|title|heading|headline|header|page title)(?: text)?(?: to(?: say)?| say| read| into)? (.+)$/i, "set_heading"],
    [/^(?:change|set|make|update) (?:the |your )?(?:tagline|subtitle|subheading)(?: to(?: say)?| say| read)? (.+)$/i, "set_tagline"],
    [/^scroll (?:all the way )?(?:back )?(?:to the )?(up|down|top|bottom)(?: of the page)?$/i, "scroll_to"],
    [/^(?:scroll|go|jump|take me|skip|head)(?: down| up| back)? to (.+)$/i, "scroll_to", true],
    [/^(?:switch to |turn on |go |enable |use )?(dark|light)(?: mode| theme)?$/i, "theme"],
    [/^(?:make|turn) (?:the |this )?(?:page|site|text|font|everything) (bigger|smaller)$|^(bigger|smaller) (?:text|font)$/i, "text_size"],
    [/^(?:hide|remove|get rid of|collapse) (.+)$/i, "hide", true],
    [/^(?:show|unhide|bring back|restore) (.+)$/i, "show", true],
    [/^(?:read|say|speak)(?: me| out)? (.+?)(?: out loud| aloud| to me)*$/i, "read_aloud", true],
    [/^highlight (.+)$/i, "highlight", true],
    [/^(?:reset|restore|undo)(?: the| this)? (?:page|site|everything)$|^reset$|^undo (?:that|all|it)$/i, "reset_page"],
    [/^(?:do a )?barrel roll$|^spin(?: the page| around)?$|^flip(?: the page)?$/i, "barrel_roll"]
  ];

  // a rule marked true only fires when its words name a real part of this page: "go to the results" scrolls, "go to github" still opens github
  function pageRoute(query, names) {
    var q = bare(query);
    for (var i = 0; i < PAGE_ROUTES.length; i++) {
      var m = PAGE_ROUTES[i][0].exec(q);
      if (!m) continue;
      var arg = m[1] || m[2] || "";
      if (PAGE_ROUTES[i][2] && !section(arg, names)) continue;
      return { tool: PAGE_ROUTES[i][1], arg: arg };
    }
    return null;
  }

  // minutes in a spoken length of time, same as tools.duration()
  var NUMBER_WORDS = { zero: 0, one: 1, two: 2, three: 3, four: 4, five: 5, six: 6, seven: 7, eight: 8, nine: 9, ten: 10, a: 1, an: 1, half: 0.5 };
  function duration(text) {
    var m = /^(\d+(?:\.\d+)?|[a-z]+)(?: an| a)?[ -]?(s|m|h)?[a-z]*$/.exec(String(text).toLowerCase().trim());
    if (!m) return null;
    var n = /^\d/.test(m[1]) ? parseFloat(m[1]) : NUMBER_WORDS[m[1]];
    return n == null ? null : Math.round(n * { s: 1 / 60, m: 1, h: 60 }[m[2] || "m"] * 10000) / 10000;
  }

  // Is a model's pick safe to run? Same rule as tools._sound(): she copies her argument out of the sentence,
  // so an argument that is not in the sentence is a guess, and a guess does not get to touch anything.
  var FIXED = { music: ["play", "pause", "next", "previous", "playing"], theme: ["dark", "light"], text_size: ["bigger", "smaller"] };
  var NO_ARG = ["current_tab", "screenshot", "clipboard", "battery", "calendar_today", "reset_page", "barrel_roll"];
  var SPAN = ["open_app", "open_url", "web_search", "say", "make_logo", "new_note", "new_reminder", "set_heading", "set_tagline", "weather", "list_dir", "read_file"];
  function sound(tool, arg, query, names) {
    var q = query.toLowerCase(), a = String(arg || "").toLowerCase().trim();
    if (FIXED[tool]) return FIXED[tool].indexOf(a) >= 0;
    if (NO_ARG.indexOf(tool) >= 0) return true;
    if (tool === "set_volume") return a === "up" || a === "down" || (/^\d{1,3}$/.test(a) && q.indexOf(a) >= 0);
    if (tool === "timer") return duration(a) !== null && q.indexOf(a) >= 0;
    if (tool === "set_color") return !!COLORS[a] && q.indexOf(a) >= 0;
    if (["scroll_to", "hide", "show", "read_aloud", "highlight"].indexOf(tool) >= 0) return !!section(a, names || []);
    return SPAN.indexOf(tool) >= 0 && (tool === "weather" || a.length > 0) && q.indexOf(a) >= 0;
  }

  // ---- exact answers: one right answer, so no model and no lookup ----
  var ARITH_WORDS = [[/\b(?:multiplied by|times)\b/g, "*"], [/\bplus\b/g, "+"], [/\bminus\b/g, "-"], [/\b(?:divided by|over)\b/g, "/"], [/(\d)\s*x\s*(\d)/g, "$1*$2"]];
  var CONVERT = { mile: ["km", 1.609344], km: ["miles", 0.621371], kg: ["lb", 2.204623], lb: ["kg", 0.453592], foot: ["m", 0.3048],
                  m: ["feet", 3.28084], inch: ["cm", 2.54], cm: ["inches", 0.393701] };
  var UNIT_NAME = { miles: "mile", mile: "mile", km: "km", kilometers: "km", kilometres: "km", kg: "kg", kilograms: "kg", lb: "lb", lbs: "lb",
                    pounds: "lb", feet: "foot", foot: "foot", ft: "foot", m: "m", meters: "m", metres: "m", inches: "inch", inch: "inch", cm: "cm", centimeters: "cm" };

  function tidy(n) { return String(Math.round(n * 10000) / 10000); }

  // + - * / and brackets, by hand. No eval, no Function: the page's security policy forbids both, as it should.
  function calc(src) {
    var t = src.replace(/\s+/g, ""), i = 0;
    function num() {
      if (t[i] === "-") { i++; return -num(); }
      if (t[i] === "(") { i++; var v = sum(); if (t[i++] !== ")") throw 0; return v; }
      var m = /^\d+(?:\.\d+)?/.exec(t.slice(i));
      if (!m) throw 0;
      i += m[0].length;
      return parseFloat(m[0]);
    }
    function product() { var v = num(); while (t[i] === "*" || t[i] === "/") { var op = t[i++], r = num(); v = op === "*" ? v * r : v / r; } return v; }
    function sum() { var v = product(); while (t[i] === "+" || t[i] === "-") { var op = t[i++], r = product(); v = op === "+" ? v + r : v - r; } return v; }
    try { var out = sum(); return i === t.length ? out : null; } catch (e) { return null; }
  }

  function exact(query) {
    var q = query.trim().toLowerCase().replace(/[?!.]+$/, "");
    var expr = q.replace(/^(?:what(?:'s| is)|calculate|compute|how much is)\s+/, "");
    ARITH_WORDS.forEach(function (p) { expr = expr.replace(p[0], p[1]); });
    if (/^[\d\s+\-*\/().]+$/.test(expr) && /\d/.test(expr) && /[+\-*\/]/.test(expr)) {
      var v = calc(expr);
      if (v !== null && isFinite(v)) return expr.replace(/\s+/g, "") + " = " + tidy(v);
    }
    var c = /^(?:convert |what(?:'s| is) )?(-?\d+(?:\.\d+)?)\s*(?:degrees? )?([a-z]+)\s+(?:to|in|into)\s+([a-z]+)$/.exec(q);
    if (c) {
      var n = parseFloat(c[1]), from = c[2], to = c[3];
      if (/^(?:c|celsius)$/.test(from) && /^(?:f|fahrenheit)$/.test(to)) return c[1] + " C = " + tidy(n * 9 / 5 + 32) + " F";
      if (/^(?:f|fahrenheit)$/.test(from) && /^(?:c|celsius)$/.test(to)) return c[1] + " F = " + tidy((n - 32) * 5 / 9) + " C";
      var u = CONVERT[UNIT_NAME[from]];
      if (u && UNIT_NAME[to] === UNIT_NAME[u[0]]) return c[1] + " " + from + " = " + tidy(n * u[1]) + " " + u[0];
    }
    var now = new Date();
    if (/^what(?:'s| is) the time|^what time is it|^(?:current )?time$/.test(q)) return "It's " + now.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" }).replace(/\.$/, "") + ".";
    if (/^what(?:'s| is) (?:the |today's )?date|^what day is it|^what(?:'s| is) today/.test(q)) return "It's " + now.toLocaleDateString([], { weekday: "long", month: "long", day: "numeric", year: "numeric" }) + ".";
    return null;
  }

  // ---- shared by the FAQ matcher in the page and the lookup chain in the Worker ----
  var STOP = {};
  ("a an the is are was were what who why how does do did this that it its to for of in on at be used let and or not with right now current about")
    .split(" ").forEach(function (w) { STOP[w] = 1; });

  function stem(w) {
    var suffixes = ["ing", "ers", "er", "ed", "es", "s"];
    for (var i = 0; i < suffixes.length; i++) {
      var s = suffixes[i];
      if (w.slice(-s.length) === s && w.length - s.length >= 3) { w = w.slice(0, -s.length); break; }
    }
    return w.slice(-1) === "e" && w.length > 3 ? w.slice(0, -1) : w;
  }

  function keywords(s) {
    var out = {};
    (s.toLowerCase().match(/[a-z0-9]+/g) || []).forEach(function (w) { if (w.length > 2 && !STOP[w]) out[stem(w)] = 1; });
    return Object.keys(out);
  }

  var PROJECT = /\b(?:turing|samantha|arthur|lora|faq|roadmap|project|repo|repository|model|adapter|eval|trained|training|fine.?tun\w*|mlx|qwen|yourself|you)\b/i;
  function isProject(q) { return PROJECT.test(q); }

  root.Samantha = { route: route, exact: exact, bare: bare, urlOf: urlOf, appMatch: appMatch, APPS: APPS, SITES: SITES,
                    stem: stem, keywords: keywords, isProject: isProject,
                    pageRoute: pageRoute, section: section, sound: sound, duration: duration, COLORS: COLORS };
})(typeof globalThis !== "undefined" ? globalThis : this);
