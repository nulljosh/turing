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
    var found = sorted.find(function (a) { return a.toLowerCase() === key; }) ||
                sorted.find(function (a) { return a.toLowerCase().indexOf(key) === 0; }) || null;
    // "photoshop" is what people call any photo editor: without Photoshop, it means the one this Mac has
    return !found && (key === "photoshop" || key === "adobe photoshop") ? appMatch("pixelmator") : found;
  }

  var SITE_SEARCH = {
    "youtube": "https://www.youtube.com/results?search_query=", "amazon": "https://www.amazon.com/s?k=",
    "reddit": "https://www.reddit.com/search/?q=", "github": "https://github.com/search?q=",
    "wikipedia": "https://en.wikipedia.org/w/index.php?search=", "google maps": "https://www.google.com/maps/search/",
    "maps": "https://www.google.com/maps/search/"
  };
  var SITE_NAMES = Object.keys(SITE_SEARCH).sort(function (a, b) { return b.length - a.length; }).join("|");
  // same as tools.site_search: quote_plus spells a space "+"
  function siteSearch(site, query) {
    return SITE_SEARCH[site.toLowerCase()] + encodeURIComponent(query.trim()).replace(/%20/g, "+");
  }

  function urlOf(target) {
    var t = target.trim().replace(/^["']+|["']+$/g, "");
    if (SITES[t.toLowerCase()]) return SITES[t.toLowerCase()];
    if (/^https?:\/\//i.test(t)) return /^https?:\/\/[^\s\/]/i.test(t) ? t : null;
    if (/^[\w-]+(\.[\w-]+)+(\/\S*)?$/.test(t)) return "https://" + t;
    return null;
  }

  var UNIT = { s: 1 / 60, m: 1, h: 60 };
  // same list as tools.LANGUAGES: a real language name, so "translate 5 km to miles" never reaches translate
  var LANGUAGES = "english|french|spanish|german|italian|portuguese|dutch|swedish|norwegian|danish|finnish|polish|czech|" +
    "romanian|hungarian|ukrainian|russian|greek|turkish|arabic|hebrew|hindi|japanese|chinese|mandarin|" +
    "cantonese|korean|vietnamese|thai|indonesian|latin";
  // same table, same order as _ROUTES in tools.py. First match wins.
  var ROUTES = [
    [/^(?:play|resume)(?: (?:the |some |my )?(?:music|song|tunes))?$/i, function () { return ["music", "play"]; }],
    [/^pause$|^(?:pause|stop) (?:the |my |this )?(?:music|song|track)$/i, function () { return ["music", "pause"]; }],
    [/^(?:skip|next)(?: (?:this |the )?(?:song|track|one))?$/i, function () { return ["music", "next"]; }],
    [/^(?:previous|last|go back a|go back one)(?: (?:song|track))?$/i, function () { return ["music", "previous"]; }],
    [/^what(?:'s| is) (?:this song|playing)\b|^what song is (?:this|playing)/i, function () { return ["music", "playing"]; }],
    [/^(?:what(?:'s| is) the |how(?:'s| is) the |(?:look up|check|get) the )?weather\b(?: like)?(?: today| outside| right now| now)*(?: (?:in|for) (.+))?$/i,
     function (m) { return ["weather", m[1] || ""]; }],
    [/^(?:set |start )?(?:a |an )?(?:timer (?:for )?(\d+(?:\.\d+)?) ?(s|m|h)\w*|(\d+(?:\.\d+)?)[ -]?(s|m|h)\w* timer)$/i,
     function (m) { return ["timer", String(parseFloat(m[1] || m[3]) * UNIT[(m[2] || m[4]).toLowerCase()])]; }],
    [/^remind me (?:to |that |about )?(.+)$|^(?:add|create|make|set|new) (?:a |me a )?(?:new )?reminder(?: to| that says| saying|:)? (.+)$/i,
     function (m) { return ["new_reminder", m[1] || m[2]]; }],
    [/^(?:(?:make|create|take|write|add|new) (?:a |me a )?(?:new )?note|note)(?: that says| saying| that|:)? (.+)$/i,
     function (m) { return ["new_note", m[1]]; }],
    [/^what(?:'s| is) on (?:my |the )?(?:calendar|schedule|agenda)\b|^(?:my )?(?:calendar|schedule|agenda)(?: for)?(?: today)?$|^what do i have (?:on )?today/i,
     function () { return ["calendar_today", ""]; }],
    [/^(?:check (?:my )?|do i have |is there )?(?:any )?(?:new |unread )?(?:mail|email)\??$/i, function () { return ["unread_mail", ""]; }],
    [/^(?:is there |do i have )?anything from (.+?) in my (?:mail|email|inbox)(?: today)?\??$|^(?:mail|email) from (.+?)(?: today)?\??$/i,
     function (m) { return ["unread_mail", m[1] || m[2]]; }],
    [/^(?:make|design|draw|create|build)(?: me)? (?:a |an )?((?:(?:complex|intricate|detailed|elaborate|ornate|fancy|crazy|insane|original|wordless|abstract|textless) )*)(?:logo|icon)(?: for| of)? (.+)$/i, function (m) { return ["make_logo", (m[1] || "") + m[2]]; }],
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
    [new RegExp("^(?:search|look up|find) (?:on )?(" + SITE_NAMES + ") for (.+)$|^(?:search|look up) (.+) on (" + SITE_NAMES + ")$", "i"),
     function (m) { return ["open_url", siteSearch(m[1] || m[4], m[2] || m[3])]; }],
    [new RegExp("^(?:open |go to |pull up )?(" + SITE_NAMES + ") and search(?: it)?(?: for)? (.+)$", "i"), function (m) { return ["open_url", siteSearch(m[1], m[2])]; }],
    [/^(?:search|google|look up)(?: search)?(?: (?:the web|online|the internet|on google|google))?(?: for)? (.+)$/i, function (m) { return ["web_search", m[1]]; }],
    [/^(?:read|fetch) (?:me )?(?:the )?(?:page |site |website )?(?:at )?(https?:\/\/\S+|[\w-]+(?:\.[\w-]+)+(?:\/\S*)?)$|^what does (https?:\/\/\S+|[\w-]+(?:\.[\w-]+)+(?:\/\S*)?) say$/i,
     function (m) { return ["read_page", m[1] || m[2]]; }],
    [/^summari[sz]e (?:this |the )?(?:page|tab)$/i, function () { return ["summarize", ""]; }],
    [/^summari[sz]e (?:my |the )?(?:unread )?(?:mail|email|inbox)$/i, function () { return ["summarize", "mail"]; }],
    [/^summari[sz]e (?:me )?(?:the )?(?:document|pdf|doc|file called) (.+)$/i, function (m) { return ["summarize", m[1]]; }],
    [/^summari[sz]e (~\/\S+|\/\S+)$/i, function (m) { return ["summarize", m[1]]; }],
    [/^summari[sz]e (?:me )?(?:the )?(?:page |site |website )?(?:at )?(https?:\/\/\S+|[\w-]+(?:\.[\w-]+)+(?:\/\S*)?)$/i,
     function (m) { return ["summarize", m[1]]; }],
    [new RegExp("^translate (?:the page |the site )?(.+?) (?:to|into) (" + LANGUAGES + ")$|^how do you say (.+?) in (" + LANGUAGES + ")$", "i"),
     function (m) { return ["translate", (m[1] || m[3]) + "\t" + (m[2] || m[4])]; }],
    [/^(?:open|launch|start) (?:up )?(?:chrome|the browser) (?:and |then )?(?:go to|open|visit|load) (.+)$/i, function (m) { return ["open_url", m[1]]; }],
    [/^(?:go to|visit|browse to|pull up) (.+)$/i, function (m) { return ["open_url", m[1]]; }],
    [/^(?:open|launch|start) (?:up )?(.+)$/i, function (m) {
      var g = m[1];
      return urlOf(g) || (g.trim().indexOf(" ") >= 0 && !appMatch(g)) ? ["open_url", g] : ["open_app", g];
    }]
  ];
  // the catch-all routes whose argument is any text, same as tools._GREEDY
  var GREEDY = [ROUTES[ROUTES.length - 2][0], ROUTES[ROUTES.length - 1][0]];
  var MULTISTEP = /\b(?:and (?:then )?(?:tell|read|find|summar|poke|look|check|see|click)|poke around|then )/i;
  // "look at my screen and tell me what's wrong" is one question about one picture, not two steps, same as tools._EYES
  var EYES = /^(?:look at|describe|see|check out|what(?:'s| is) in) (?:(?:my |the )?screen|\S+\.(?:png|jpe?g|heic|gif|webp|tiff?|bmp))\b/i;
  // an explicit multi-step screen job, same as tools._SCREEN_JOB: her own screen agent plans it on the real Mac
  var SCREEN_JOB = /^(?:log (?:me )?(?:in|into)|sign (?:me )?(?:in|into)|walk me through|step me through)\b/i;
  var ACTION = /^(?:open|launch|start|go to|visit|browse|pull up|search|google|look up|poke around|take a|grab a|screenshot|make|design|draw|play|pause|skip|remind me|set a)\b/i;
  var LEAD = /^(?:(?:hey|ok|okay|yo|samantha|please|now|just)[, ]+)*(?:(?:can|could|would|will) you (?:please )?|i (?:want|need|would like|'d like) (?:you )?to |let's |go ahead and )?(?:please )?/i;
  var TAIL = /(?:[, ]+(?:please|for me|real quick|now|thanks|thank you))+$/i;

  function bare(query) {
    return query.normalize("NFKC").replace(/[\x00-\x1f\x7f\u200b-\u200f\u202a-\u202e\u2060-\u2069\ufeff]/g, "").trim().replace(/[.!?]+$/, "")
      .replace(/\b(what|how|where|who)s\b/gi, "$1's").replace(/(?:[,;]?\s+(?:and then|and|then))+$/i, "").replace(LEAD, "").replace(TAIL, "").trim();
  }

  // {tool, arg} for one exact command, {agent: true} for multi-step work, null for anything that is not a command
  function route(query) {
    var q = bare(query);
    if (SCREEN_JOB.test(q)) return { agent: true };
    if (MULTISTEP.test(q) && !EYES.test(q)) return { agent: true };
    for (var i = 0; i < ROUTES.length; i++) {
      var m = ROUTES[i][0].exec(q);
      if (m) { var r = ROUTES[i][1](m); return { tool: r[0], arg: r[1] }; }
    }
    return ACTION.test(q) ? { agent: true } : null;
  }

  function routeOf(command) {
    for (var i = 0; i < ROUTES.length; i++) if (ROUTES[i][0].test(command)) return ROUTES[i][0];
    return null;
  }

  // same rule as tools.chain: the steps of "open youtube and set the volume to 20", or null when it is one command
  function chain(query) {
    var whole = bare(query.split("\n").pop());
    if (!/\bthen\b|;/i.test(whole) && routeOf(whole) && GREEDY.indexOf(routeOf(whole)) < 0) return null;
    var parts = whole.split(/\s*(?:,? and then |,? then |,? and |; )\s*/i).map(function (p) {
      return p.replace(/^(?:tell|show|give|read) me (?:my |the )?|^(?:also|and) /i, "").trim();
    });
    if (parts.length < 2 || !parts.every(Boolean)) return null;
    if (parts.slice(1).some(function (p) { return GREEDY.indexOf(routeOf(p)) >= 0; })) return null;
    var steps = parts.map(function (p) { return route(p); });
    return steps.every(function (r) { return r && r.tool; }) ? steps : null;
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


  // ---- the forty-seven utility tools, ported from tools_util.py. Same words back, so the two sides can be diffed. ----
  var U = {};
  function num(x) { x = Math.round(x * 1e10) / 1e10; return String(x); }

  // arithmetic without eval: a small parser for + - * / // % ** ( ), a few functions, pi and e
  var FUNCS = { sqrt: Math.sqrt, abs: Math.abs, round: Math.round, sin: Math.sin, cos: Math.cos, tan: Math.tan, log: Math.log10, ln: Math.log };
  function calcParse(text) {
    var toks = text.match(/\d+\.?\d*|\.\d+|\*\*|\/\/|[-+*\/%()]|[a-z]+/g) || [], i = 0;
    if (toks.join("") !== text.replace(/\s+/g, "")) throw new Error("I only do plain arithmetic");
    function peek() { return toks[i]; }
    function atom() {
      var t = toks[i++];
      if (t === undefined) throw new Error("I only do plain arithmetic");
      if (/^[\d.]/.test(t)) return parseFloat(t);
      if (t === "pi") return Math.PI;
      if (t === "e") return Math.E;
      if (t === "(") { var v = expr(); if (toks[i++] !== ")") throw new Error("I only do plain arithmetic"); return v; }
      if (FUNCS[t] && toks[i] === "(") { i++; var a = expr(); if (toks[i++] !== ")") throw new Error("I only do plain arithmetic"); return FUNCS[t](a); }
      throw new Error("I only do plain arithmetic");
    }
    function power() {
      var base = atom();
      if (peek() === "**") { i++; var e = unary(); if (Math.abs(e) > 1000) throw new Error("that power is too big"); return Math.pow(base, e); }
      return base;
    }
    function unary() {
      if (peek() === "-") { i++; return -unary(); }
      if (peek() === "+") { i++; return unary(); }
      return power();
    }
    function term() {
      var v = unary();
      while (["*", "/", "//", "%"].indexOf(peek()) >= 0) {
        var op = toks[i++], b = unary();
        if ((op !== "*") && b === 0) throw new RangeError("zero");
        v = op === "*" ? v * b : op === "/" ? v / b : op === "//" ? Math.floor(v / b) : v - b * Math.floor(v / b);
      }
      return v;
    }
    function expr() {
      var v = term();
      while (peek() === "+" || peek() === "-") { var op = toks[i++], b = term(); v = op === "+" ? v + b : v - b; }
      return v;
    }
    var out = expr();
    if (i < toks.length) throw new Error("I only do plain arithmetic");
    return out;
  }
  U.calculate = function (expression) {
    var text = expression.toLowerCase().replace(/x/g, "*").replace(/\^/g, "**").replace(/,/g, "").trim();
    var m = /^(\d+(?:\.\d+)?)\s*% of (\d+(?:\.\d+)?)$/.exec(text);
    if (m) return num(parseFloat(m[1]) * parseFloat(m[2]) / 100);
    try {
      var v = calcParse(text);
      if (!isFinite(v)) throw new RangeError("zero");
      return num(v);
    } catch (e) {
      if (e instanceof RangeError) return "You cannot divide by zero.";
      return "Cannot work that out: " + (e.message === "that power is too big" ? e.message : "I only do plain arithmetic") + ".";
    }
  };

  var LENGTH = { mm: 0.001, cm: 0.01, m: 1, km: 1000, "in": 0.0254, ft: 0.3048, yd: 0.9144, mi: 1609.344 };
  var MASS = { g: 0.001, kg: 1, lb: 0.45359237, oz: 0.028349523125 };
  var VOLUME = { ml: 0.001, l: 1, cup: 0.2365882365, gal: 3.785411784 };
  var TIME = { s: 1, min: 60, h: 3600, day: 86400, week: 604800 };
  var ALIAS = {
    millimeter: "mm", millimeters: "mm", centimeter: "cm", centimeters: "cm", meter: "m", meters: "m", metre: "m", metres: "m",
    kilometer: "km", kilometers: "km", kilometre: "km", kilometres: "km", inch: "in", inches: "in", foot: "ft", feet: "ft",
    yard: "yd", yards: "yd", mile: "mi", miles: "mi", gram: "g", grams: "g", kilogram: "kg", kilograms: "kg", kilo: "kg", kilos: "kg",
    pound: "lb", pounds: "lb", lbs: "lb", ounce: "oz", ounces: "oz", milliliter: "ml", milliliters: "ml", liter: "l", liters: "l",
    litre: "l", litres: "l", cups: "cup", gallon: "gal", gallons: "gal", second: "s", seconds: "s", sec: "s", minute: "min",
    minutes: "min", mins: "min", hour: "h", hours: "h", hr: "h", hrs: "h", days: "day", weeks: "week",
    celsius: "c", centigrade: "c", fahrenheit: "f", kelvin: "k", "°c": "c", "°f": "f"
  };
  U.convert_units = function (text) {
    var m = /^\s*(-?\d+(?:\.\d+)?)\s*([a-z°]+)\s+(?:to|in|into)\s+([a-z°]+)\s*$/.exec(text.toLowerCase());
    if (!m) return 'Say it like "5 km to miles".';
    var n = parseFloat(m[1]), a = ALIAS[m[2]] || m[2], b = ALIAS[m[3]] || m[3], temps = ["c", "f", "k"];
    if (temps.indexOf(a) >= 0 && temps.indexOf(b) >= 0) {
      var c = a === "c" ? n : a === "f" ? (n - 32) * 5 / 9 : n - 273.15;
      var out = b === "c" ? c : b === "f" ? c * 9 / 5 + 32 : c + 273.15;
      return num(n) + " " + a.toUpperCase() + " is " + num(Math.round(out * 100) / 100) + " " + b.toUpperCase() + ".";
    }
    var tables = [LENGTH, MASS, VOLUME, TIME];
    for (var i = 0; i < tables.length; i++) {
      var t = tables[i];
      if (t.hasOwnProperty(a) && t.hasOwnProperty(b)) return num(n) + " " + a + " is " + num(Math.round(n * t[a] / t[b] * 1e4) / 1e4) + " " + b + ".";
    }
    return "I cannot convert " + m[2] + " to " + m[3] + ".";
  };

  var ZONES = { tokyo: "Asia/Tokyo", london: "Europe/London", paris: "Europe/Paris", berlin: "Europe/Berlin", "new york": "America/New_York",
    "los angeles": "America/Los_Angeles", vancouver: "America/Vancouver", toronto: "America/Toronto", chicago: "America/Chicago",
    denver: "America/Denver", sydney: "Australia/Sydney", dubai: "Asia/Dubai", singapore: "Asia/Singapore", "hong kong": "Asia/Hong_Kong",
    mumbai: "Asia/Kolkata", delhi: "Asia/Kolkata", moscow: "Europe/Moscow", seoul: "Asia/Seoul", beijing: "Asia/Shanghai",
    shanghai: "Asia/Shanghai", cairo: "Africa/Cairo", "sao paulo": "America/Sao_Paulo", "mexico city": "America/Mexico_City",
    auckland: "Pacific/Auckland", honolulu: "Pacific/Honolulu" };
  function clock(zone) {
    var o = zone ? { timeZone: zone } : {};
    return new Date().toLocaleTimeString("en-US", Object.assign({ hour: "numeric", minute: "2-digit" }, o)).replace(/ /g, " ");
  }
  U.time_in = function (place) {
    var key = (place || "").toLowerCase().trim();
    if (!key) return "It is " + clock() + ".";
    var zone = ZONES[key] || place.trim().replace(/ /g, "_");
    try {
      var day = new Date().toLocaleDateString("en-US", { weekday: "long", timeZone: zone });
      return "It is " + clock(zone) + " on " + day + " in " + place.trim().replace(/\b\w/g, function (c) { return c.toUpperCase(); }) + ".";
    } catch (e) { return "I do not know the time zone for " + place.trim() + "."; }
  };
  // convert_time: same grammar and words as util_dates.convert_time. Zone math is Intl only, no library.
  var TZ_ABBR = { pst: "America/Los_Angeles", pdt: "America/Los_Angeles", pt: "America/Los_Angeles", pacific: "America/Los_Angeles",
    mst: "America/Denver", mdt: "America/Denver", mt: "America/Denver", mountain: "America/Denver",
    cst: "America/Chicago", cdt: "America/Chicago", ct: "America/Chicago", central: "America/Chicago",
    est: "America/New_York", edt: "America/New_York", et: "America/New_York", eastern: "America/New_York",
    gmt: "UTC", utc: "UTC", bst: "Europe/London", cet: "Europe/Paris", cest: "Europe/Paris",
    jst: "Asia/Tokyo", kst: "Asia/Seoul", ist: "Asia/Kolkata", aest: "Australia/Sydney", hst: "Pacific/Honolulu" };
  function tzOf(name) {
    var key = name.toLowerCase().trim().replace(/ time$/, "").trim();
    var zone = TZ_ABBR[key] || ZONES[key] || (name.indexOf("/") >= 0 ? name.trim().replace(/ /g, "_") : null);
    if (!zone) return null;
    try { new Intl.DateTimeFormat("en-US", { timeZone: zone }); } catch (e) { return null; }
    var label = TZ_ABBR[key] && key.length <= 4 ? key.toUpperCase() : name.indexOf("/") >= 0 ? name.trim() : key.replace(/\b\w/g, function (c) { return c.toUpperCase(); });
    return { zone: zone, label: label };
  }
  function clockOf(text) {
    var t = text.toLowerCase().replace(/\./g, "").replace(/ /g, "");
    if (t === "noon" || t === "midnight") return [t === "noon" ? 12 : 0, 0];
    var m = /^(\d{1,2})(?::(\d{2}))?(am|pm)?$/.exec(t);
    if (!m) return null;
    var h = +m[1], mi = +(m[2] || 0), half = m[3];
    if (mi > 59 || (half && !(h >= 1 && h <= 12)) || (!half && h > 23)) return null;
    return [half ? h % 12 + (half === "pm" ? 12 : 0) : h, mi];
  }
  // the wall clock in a zone at an instant, as numbers
  function wall(zone, t) {
    var o = { hourCycle: "h23", year: "numeric", month: "numeric", day: "numeric", hour: "numeric", minute: "numeric", second: "numeric", weekday: "long" };
    if (zone) o.timeZone = zone;
    var p = {};
    new Intl.DateTimeFormat("en-US", o).formatToParts(new Date(t)).forEach(function (x) { p[x.type] = x.value; });
    return { y: +p.year, mo: +p.month, d: +p.day, h: +p.hour % 24, mi: +p.minute, s: +p.second, day: p.weekday };
  }
  function offsetAt(zone, t) { var w = wall(zone, t); return Date.UTC(w.y, w.mo - 1, w.d, w.h, w.mi, w.s) - Math.floor(t / 1000) * 1000; }
  function hm(w) { return (w.h % 12 || 12) + ":" + (w.mi < 10 ? "0" : "") + w.mi + " " + (w.h < 12 ? "AM" : "PM"); }
  U.convert_time = function (request) {
    var m = /^\s*(noon|midnight|\d{1,2}(?::\d{2})?\s*(?:am|pm|a\.m\.|p\.m\.)?)\s*(.*?)\s*\b(?:in|to)\s+(.+?)\s*$/i.exec(request);
    if (!m) return 'Say it like "3pm PST in Tokyo" or "15:30 London to New York".';
    var c = clockOf(m[1]);
    if (!c) return m[1].trim() + " is not a time I can read. Try 3pm, 3:30 pm or 15:30.";
    var srcText = m[2].trim().replace(/^(?:in|from)\s+/i, "");
    var src = srcText ? tzOf(srcText) : { zone: undefined, label: "here" }, dst = tzOf(m[3]);
    if (!src || !dst) return "I do not know the time zone for " + (!dst ? m[3] : srcText).trim() + ".";
    var today = wall(src.zone, Date.now()), guess = Date.UTC(today.y, today.mo - 1, today.d, c[0], c[1]);
    var t = guess - offsetAt(src.zone, guess);
    t = guess - offsetAt(src.zone, t);  // once more, in case daylight time starts or ends in between
    return hm(wall(src.zone, t)) + " " + src.label + " is " + hm(wall(dst.zone, t)) + " on " + wall(dst.zone, t).day + " in " + dst.label + ".";
  };
  U.current_date = function () {
    return "It is " + new Date().toLocaleDateString("en-US", { weekday: "long", year: "numeric", month: "long", day: "numeric" }) + ".";
  };
  var HOLIDAYS = { christmas: [12, 25], "new year": [1, 1], "new years": [1, 1], halloween: [10, 31], "canada day": [7, 1],
                   "valentines day": [2, 14], "valentine's day": [2, 14] };
  U.days_until = function (target) {
    var key = target.toLowerCase().trim(), now = new Date(), y = now.getFullYear();
    var today = Date.UTC(y, now.getMonth(), now.getDate()), d;
    if (HOLIDAYS[key]) {
      d = Date.UTC(y, HOLIDAYS[key][0] - 1, HOLIDAYS[key][1]);
      if (d < today) d = Date.UTC(y + 1, HOLIDAYS[key][0] - 1, HOLIDAYS[key][1]);
    } else {
      var m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(key);
      d = m ? Date.UTC(+m[1], +m[2] - 1, +m[3]) : NaN;
      if (m && new Date(d).getUTCMonth() !== +m[2] - 1) d = NaN;
    }
    if (isNaN(d)) return "Give me a date like 2026-12-25, or a holiday like christmas.";
    var n = Math.round((d - today) / 864e5), dt = new Date(d);
    if (n === 0) return "That is today.";
    return Math.abs(n) + " day" + (Math.abs(n) === 1 ? "" : "s") + " " + (n > 0 ? "until" : "since") + " " +
      dt.toLocaleDateString("en-US", { month: "long", day: "numeric", year: "numeric", timeZone: "UTC" }) + ".";
  };

  // date_math: same grammar and words as tools_util.date_math. Dates are whole days in UTC, today is the visitor's local day.
  var MONTH_NAMES = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
  var DAY_NAMES = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];
  var MONTHS = {}, COUNT = { a: 1, an: 1, one: 1, two: 2, three: 3, four: 4, five: 5, six: 6, seven: 7, eight: 8, nine: 9, ten: 10 };
  MONTH_NAMES.forEach(function (m, i) { MONTHS[m.toLowerCase()] = i + 1; MONTHS[m.toLowerCase().slice(0, 3)] = i + 1; });
  MONTHS.sept = 9;
  function todayUTC() { var n = new Date(); return Date.UTC(n.getFullYear(), n.getMonth(), n.getDate()); }
  function mkday(y, m, d) {
    if (y < 1 || y > 9999) return null;
    var t = new Date(Date.UTC(2000, m - 1, d)); t.setUTCFullYear(y);
    return t.getUTCMonth() === m - 1 && t.getUTCDate() === d ? t.getTime() : null;
  }
  function parseDay(text) {
    var t = text.toLowerCase().replace(/[,.]|\b(?:the|of)\b|(\d)(?:st|nd|rd|th)\b/g, function (x, dg) { return dg ? dg + " " : " "; }).trim().split(/\s+/);
    var key = t.join(" "), today = todayUTC(), now = new Date(today);
    if (key === "today" || key === "now") return today;
    if (key === "tomorrow" || key === "yesterday") return today + (key === "tomorrow" ? 1 : -1) * 864e5;
    if (HOLIDAYS[key]) {
      var h = mkday(now.getUTCFullYear(), HOLIDAYS[key][0], HOLIDAYS[key][1]);
      return h >= today ? h : mkday(now.getUTCFullYear() + 1, HOLIDAYS[key][0], HOLIDAYS[key][1]);
    }
    var m;
    if (t.length === 1 && (m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(t[0]))) return mkday(+m[1], +m[2], +m[3]);
    if (t.length === 3 && MONTHS[t[0]] && /^\d+$/.test(t[1]) && /^\d+$/.test(t[2])) return mkday(+t[2], MONTHS[t[0]], +t[1]);
    if (t.length === 3 && MONTHS[t[1]] && /^\d+$/.test(t[0]) && /^\d+$/.test(t[2])) return mkday(+t[2], MONTHS[t[1]], +t[0]);
    return null;
  }
  function shiftDay(d, n, unit) {
    if (unit === "day" || unit === "week") return d + n * (unit === "week" ? 7 : 1) * 864e5;
    var x = new Date(d), months = x.getUTCMonth() + n * (unit === "year" ? 12 : 1);
    var y = x.getUTCFullYear() + Math.floor(months / 12), m = ((months % 12) + 12) % 12 + 1;
    var last = new Date(Date.UTC(2000, m, 0)); last.setUTCFullYear(y, m, 0);
    return mkday(y, m, Math.min(x.getUTCDate(), last.getUTCDate()));
  }
  function longDate(d) { var x = new Date(d); return MONTH_NAMES[x.getUTCMonth()] + " " + x.getUTCDate() + ", " + x.getUTCFullYear(); }
  function sayDay(d) { return DAY_NAMES[new Date(d).getUTCDay()] + ", " + longDate(d); }
  U.date_math = function (question) {
    var q = String(question).trim().toLowerCase(), m, d;
    var bad = 'Say it like "100 days from now", "weekday July 4 1976" or "between 2026-01-01 and 2026-12-25".';
    var range = "That date is out of range: I can do years 1 to 9999.";
    if ((m = /^(\d{1,6}|a|an|one|two|three|four|five|six|seven|eight|nine|ten) (day|week|month|year)s? (from|after|before|ago)(?: (.+))?$/.exec(q))) {
      var n = /^\d/.test(m[1]) ? +m[1] : COUNT[m[1]];
      var base = m[3] === "ago" || !m[4] || m[4] === "now" || m[4] === "today" ? todayUTC() : parseDay(m[4]);
      if ((m[3] === "ago" && m[4]) || base === null) return bad;
      d = shiftDay(base, m[3] === "before" || m[3] === "ago" ? -n : n, m[2]);
      if (d === null || isNaN(d) || new Date(d).getUTCFullYear() < 1 || new Date(d).getUTCFullYear() > 9999) return range;
      var said = / from$/.test(q) ? q + " now" : q;
      return said[0].toUpperCase() + said.slice(1) + " is " + sayDay(d) + ".";
    }
    if ((m = /^weekday (.+)$/.exec(q))) {
      d = parseDay(m[1]);
      if (d === null) return bad;
      var tense = d === todayUTC() ? "is" : d < todayUTC() ? "was" : "will be";
      return longDate(d) + " " + tense + " a " + DAY_NAMES[new Date(d).getUTCDay()] + ".";
    }
    if ((m = /^between (.+?) and (.+)$/.exec(q))) {
      var a = parseDay(m[1]), b = parseDay(m[2]);
      if (a === null || b === null) return bad;
      var days = Math.round(Math.abs(b - a) / 864e5);
      return days.toLocaleString("en-US") + " day" + (days === 1 ? "" : "s") + " between " + longDate(a) + " and " + longDate(b) + ".";
    }
    return bad;
  };

  function rnd(lo, hi) { return lo + Math.floor(Math.random() * (hi - lo + 1)); }
  U.flip_coin = function () { return Math.random() < 0.5 ? "Heads." : "Tails."; };
  U.roll_dice = function (spec) {
    var m = /^(\d*)d(\d+)$/.exec((spec || "1d6").toLowerCase().trim() || "1d6");
    if (!m) return 'Say it like "2d6" or "d20".';
    var n = parseInt(m[1] || "1", 10), sides = parseInt(m[2], 10);
    if (!(n >= 1 && n <= 100 && sides >= 2 && sides <= 1000)) return "Up to 100 dice with 2 to 1000 sides.";
    var rolls = [], sum = 0;
    for (var i = 0; i < n; i++) { var r = rnd(1, sides); rolls.push(r); sum += r; }
    return n === 1 ? String(rolls[0]) : rolls.join(" + ") + " = " + sum;
  };
  U.random_number = function (bounds) {
    var nums = ((bounds || "").match(/-?\d+/g) || []).slice(0, 2).map(Number);
    return String(nums.length === 2 ? rnd(Math.min(nums[0], nums[1]), Math.max(nums[0], nums[1])) : rnd(1, 100));
  };
  U.make_password = function (length) {
    var n = Math.max(8, Math.min(64, /^\d+$/.test(String(length).trim()) ? parseInt(length, 10) : 16));
    var pool = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*-_", out = "";
    var buf = new Uint32Array(n);
    crypto.getRandomValues(buf);
    for (var i = 0; i < n; i++) out += pool[buf[i] % pool.length];
    return out;
  };
  U.make_uuid = function () { return crypto.randomUUID(); };

  U.hash_text = function (text) {
    return crypto.subtle.digest("SHA-256", new TextEncoder().encode(text)).then(function (buf) {
      return Array.prototype.map.call(new Uint8Array(buf), function (b) { return ("0" + b.toString(16)).slice(-2); }).join("");
    });
  };
  U.base64_encode = function (text) { return btoa(unescape(encodeURIComponent(text))); };
  U.base64_decode = function (text) {
    var t = text.trim();
    try {
      if (t.length % 4 || !/^[A-Za-z0-9+\/]*={0,2}$/.test(t)) throw new Error("bad");
      return decodeURIComponent(escape(atob(t)));
    } catch (e) { return "That is not valid base64 text."; }
  };
  U.word_count = function (text) {
    var words = text.trim() ? text.trim().split(/\s+/).length : 0;
    return words + " word" + (words === 1 ? "" : "s") + ", " + Array.from(text).length + " characters.";
  };
  U.reverse_text = function (text) { return Array.from(text).reverse().join(""); };
  U.shout = function (text) { return text.toUpperCase(); };
  var MORSE = {};
  ("abcdefghijklmnopqrstuvwxyz0123456789").split("").forEach(function (c, i) {
    MORSE[c] = (".- -... -.-. -.. . ..-. --. .... .. .--- -.- .-.. -- -. --- .--. --.- .-. ... - ..- ...- .-- -..- -.-- --.. " +
                "----- .---- ..--- ...-- ....- ..... -.... --... ---.. ----.").split(" ")[i];
  });
  U.morse_code = function (text) {
    var out = text.toLowerCase().split("").filter(function (c) { return MORSE[c]; }).map(function (c) { return MORSE[c]; }).join(" ");
    return out || "Nothing there to translate.";
  };
  U.json_pretty = function (text) {
    try { return JSON.stringify(JSON.parse(text), null, 2).slice(0, 2000); } catch (e) { return "That is not valid JSON."; }
  };
  U.is_prime = function (number) {
    var s = String(number).trim();
    if (!/^\d+$/.test(s) || +s < 2 || +s > 1e12) return "Give me a whole number from 2 to a trillion.";
    var n = +s, factors = [], p = 2;
    while (p * p <= n) { while (n % p === 0) { factors.push(p); n /= p; } p += p === 2 ? 1 : 2; }
    if (n > 1) factors.push(n);
    return factors.length === 1 ? s + " is prime." : s + " is not prime: " + factors.join(" x ") + ".";
  };
  U.roman_numeral = function (number) {
    var s = String(number).trim();
    if (!/^\d+$/.test(s) || +s < 1 || +s > 3999) return "Roman numerals run from 1 to 3999.";
    var n = +s, out = "", table = [[1000, "M"], [900, "CM"], [500, "D"], [400, "CD"], [100, "C"], [90, "XC"], [50, "L"], [40, "XL"], [10, "X"], [9, "IX"], [5, "V"], [4, "IV"], [1, "I"]];
    table.forEach(function (row) { while (n >= row[0]) { out += row[1]; n -= row[0]; } });
    return out;
  };
  U.tip = function (amount) {
    var bill = parseFloat(String(amount).replace("$", ""));
    if (!isFinite(bill) || bill < 0) return "Give me the bill amount.";
    return "Tip on " + bill.toFixed(2) + ": " + [15, 18, 20].map(function (p) { return p + "% is " + (bill * p / 100).toFixed(2); }).join(", ") + ".";
  };
  // memory across visits: the same three tools as tools_util.py, kept in this browser's localStorage instead of a file
  function facts() { try { var g = JSON.parse(localStorage.getItem("samantha.memory") || "[]"); return Array.isArray(g) ? g.filter(function (f) { return typeof f === "string"; }) : []; } catch (e) { return []; } }
  function saveFacts(f) { try { localStorage.setItem("samantha.memory", JSON.stringify(f.slice(-500))); } catch (e) {} }
  function words(t) { var out = {}; (t.toLowerCase().match(/[a-z0-9']+/g) || []).forEach(function (w) { if (w.length > 2) out[w] = 1; }); return out; }
  function overlap(a, b) { return Object.keys(a).filter(function (w) { return b[w]; }).length; }
  U.remember = function (text) {
    var fact = text.split(/\s+/).filter(Boolean).join(" ").slice(0, 300);
    if (!fact) return "Tell me what to remember.";
    var all = facts();
    if (all.some(function (f) { return f.toLowerCase() === fact.toLowerCase(); })) return "I already know that.";
    saveFacts(all.concat([fact]));
    return "Remembered: " + fact;
  };
  U.recall = function (query) {
    var want = words(query), found = facts().map(function (f, i) { return [overlap(want, words(f)), i, f]; })
      .filter(function (t) { return t[0]; }).sort(function (a, b) { return b[0] - a[0] || b[1] - a[1]; }).slice(0, 3).map(function (t) { return t[2]; });
    return found.length ? found.join("\n") : "I do not remember anything about " + (query.trim() || "that") + ".";
  };
  U.forget = function (query) {
    var want = words(query);
    if (!Object.keys(want).length) return "Say what to forget.";
    var all = facts(), hit = all.filter(function (f) { return overlap(want, words(f)) === Object.keys(want).length; });
    if (!hit.length) return "I do not remember anything about " + query.trim() + ".";
    if (hit.length > 5) return "That matches " + hit.length + " things. Be more specific.";
    saveFacts(all.filter(function (f) { return hit.indexOf(f) < 0; }));
    return "Forgot " + hit.length + " thing" + (hit.length === 1 ? "" : "s") + ".";
  };
  // the ten that read or touch a real Mac. The stand-in Mac on this page has no disk, network or clipboard to show.
  var REAL_MAC = "That one reads your real Mac, and this stand-in has no disk, memory or network. Run her on a Mac and it answers.";
  ["disk_space", "uptime", "memory_usage", "cpu_load", "ip_address", "wifi_name", "system_info", "copy_to_clipboard", "sleep_display", "reveal_in_finder", "list_shortcuts", "run_shortcut", "list_mcp_tools", "call_mcp_tool", "list_tabs", "switch_tab", "close_tab", "read_tab", "read_screen", "read_document", "find_in_document", "ask_document", "ask_screen", "transcribe_video", "unread_mail"]
    .forEach(function (name) { U[name] = function () { return REAL_MAC; }; });
  U.NEEDS_MAC = ["disk_space", "uptime", "memory_usage", "cpu_load", "ip_address", "wifi_name", "system_info", "copy_to_clipboard", "sleep_display", "reveal_in_finder", "list_shortcuts", "run_shortcut", "list_mcp_tools", "call_mcp_tool", "list_tabs", "switch_tab", "close_tab", "read_tab", "read_screen", "read_document", "find_in_document", "ask_document", "ask_screen", "transcribe_video", "unread_mail"];

  // the image tools, same table as tools_image.ROUTES and ahead of the utilities. The stand-in Mac has no photos on disk.
  var P = "(?:the )?(?:image |photo |picture |pic )?(?:at )?(\\S+\\.(?:jpe?g|png|heic|webp|tiff?))";
  ROUTES.push.apply(ROUTES, [
    [new RegExp("^(?:make|turn|convert) " + P + " (?:into )?(?:black and white|black & white|b&w|grayscale|greyscale)$|^(?:grayscale|greyscale|desaturate) " + P + "$", "i"),
     function (m) { return ["grayscale_image", m[1] || m[2]]; }],
    [new RegExp("^(?:remove|cut out|erase|delete|take out) the background (?:from|of|in|on) " + P + "$", "i"), function (m) { return ["remove_background", m[1]]; }],
    [new RegExp("^(?:upscale|enlarge|blow up) " + P + "$", "i"), function (m) { return ["upscale_image", m[1]]; }],
    [new RegExp("^(?:enhance|auto[- ]?enhance|fix up|improve) " + P + "$", "i"), function (m) { return ["enhance_image", m[1]]; }],
    [new RegExp("^rotate " + P + "(?: by (\\d+)(?: degrees)?)?$", "i"), function (m) { return ["rotate_image", m[1] + " by " + (m[2] || 90)]; }],
    [new RegExp("^flip " + P + "(?: (horizontally|vertically|horizontal|vertical|upside down))?$", "i"),
     function (m) { return ["flip_image", m[1] + (/^(?:vertically|vertical|upside down)$/i.test(m[2] || "") ? " vertical" : "")]; }],
    [new RegExp("^(?:resize|scale) " + P + " to (\\d+)(?: ?px| pixels)?(?: wide)?$", "i"), function (m) { return ["resize_image", m[1] + " to " + m[2]]; }],
    [new RegExp("^(?:crop|square up) " + P + "(?: (?:to |into )?(?:a )?square)?$", "i"), function (m) { return ["crop_square", m[1]]; }],
    [new RegExp("^convert " + P + " (?:to|into) (?:a |an )?(png|jpe?g|webp|heic|tiff?|pdf)$", "i"), function (m) { return ["convert_image", m[1] + " to " + m[2]]; }],
    [new RegExp("^(?:how big is " + P + "|(?:image )?(?:info|size|dimensions) (?:for|of|on) " + P + ")$", "i"), function (m) { return ["image_info", m[1] || m[2]]; }]
  ]);
  U.ask_llm = function () { return "On her real Mac she hands a hard question to another LLM running there: name one (ask qwen, ask llama, ask gemma) or say ask claude for the biggest. She asks you first and nothing leaves the Mac. This page never sends your words anywhere but its own lookup."; };
  U.NEEDS_MAC.push("ask_llm");
  U.research = function () { return "Research happens on her real Mac: she reads Wikipedia, her library and your notes, and a bigger local model writes a short brief that cites every source."; };
  U.NEEDS_MAC.push("research");
  U.save_research = function () { return "Saving a brief to a file happens on her real Mac, and she asks first."; };
  U.NEEDS_MAC.push("save_research");
  U.write_document = function () { return "Drafting and saving a file happens on her real Mac, with the local model, and she asks first."; };
  U.NEEDS_MAC.push("write_document");
  ["see_screen", "see_image"].forEach(function (name) {
    U[name] = function () { return "Looking at pictures and the screen happens on her real Mac, with a vision model that runs there, and she asks first."; };
    U.NEEDS_MAC.push(name);
  });
  ["click_text", "type_text", "press_key"].forEach(function (name) {
    U[name] = function () { return "Clicking, typing and pressing keys happen on her real Mac, where she reads the screen to find what you named and asks before every step."; };
    U.NEEDS_MAC.push(name);
  });
  U.read_page = function () { return "Reading a page happens on her real Mac, which fetches it. Here I can open it for you: say \"go to\" and the address."; };
  U.summarize = function () { return "Summarizing happens on her real Mac, which reads the document or page and hands it to the biggest local model there. This stand-in has none of that."; };
  U.translate = function () { return "Translating happens on her real Mac, offline, through the biggest local model there. This stand-in has no model to do it with."; };
  var NO_PHOTOS = "That one edits a photo on your real Mac in Pixelmator, and this stand-in has no photos on disk. Ask me to draw something instead.";
  ["grayscale_image", "remove_background", "upscale_image", "enhance_image", "rotate_image", "flip_image", "resize_image", "crop_square", "convert_image", "image_info"]
    .forEach(function (name) { U[name] = function () { return NO_PHOTOS; }; U.NEEDS_MAC.push(name); });

  ROUTES.push.apply(ROUTES, [
    // deep research, same as tools_util.ROUTES
    [/^(?:research|do (?:some )?research (?:on|into)|deep dive (?:into|on)|write (?:me )?a (?:research )?brief (?:on|about)) (.+)$/i, function (m) { return ["research", m[1]]; }],
    [/^save (?:that|it|the brief|this brief)(?: to (.+))?$/i, function (m) { return ["save_research", m[1] || ""]; }],
    [/^(?:draft|write)(?: me)? (?:a |an )?(?:doc(?:ument)?|email|file)(?: about| for| on)? (.+)$/i, function (m) { return ["write_document", m[1]]; }],
    // her eyes, same as tools_util.ROUTES
    [/^(?:look at|describe|see|check out) (?:my |the )?screen(?:,? and (.+))?$|^what do you see(?: on (?:my |the )?screen)?$/i, function (m) { return ["see_screen", m[1] || ""]; }],
    [/^(?:what(?:'s| is) in|describe|look at) (\S+\.(?:png|jpe?g|heic|gif|webp|tiff?|bmp))(?:,? and (.+))?$/i, function (m) { return ["see_image", (m[2] || "") + "\t" + m[1]]; }],
    // her hands on the screen, same as tools_util.ROUTES: a named key before a click
    [/^(?:press|hit|push)(?: the)? (return|enter|tab|escape|esc|space|delete|backspace|up|down|left|right|page up|page down|home|end)(?: key| button)?$/i, function (m) { return ["press_key", m[1]]; }],
    [/^(?:click|tap|press)(?: on)?(?: the)? ["']?(.+?)["']?(?: button| link| tab)?$/i, function (m) { return ["click_text", m[1]]; }],
    [/^type(?: in| out)? ["']?(.+?)["']?$/i, function (m) { return ["type_text", m[1]]; }],
    // only by name, same as tools_util.ROUTES
    [/^(?:ask|have|let) (claude|chatgpt|gpt(?:-?\d[\w.]*)?|gemini|(?:an? |the )?(?:llm|(?:bigger|big) model)|qwen[\w.:-]*|llama[\w.:-]*|mistral[\w.:-]*|gemma[\w.:-]*|phi[\w.:-]*|deepseek[\w.:-]*)(?: to| about| whether| if|:|,)?\s+(.+)$|^(?:hey )?(claude|chatgpt|gpt(?:-?\d[\w.]*)?|gemini|(?:an? |the )?(?:llm|(?:bigger|big) model)|qwen[\w.:-]*|llama[\w.:-]*|mistral[\w.:-]*|gemma[\w.:-]*|phi[\w.:-]*|deepseek[\w.:-]*)[,:]\s*(.+)$/i, function (m) { return ["ask_llm", (m[1] || m[3]) + "\t" + (m[2] || m[4])]; }],
    // a time in one zone to another: ahead of convert_units, same as tools_util.ROUTES
    [/^(?:what(?:'s| is)(?: the time)?|what time is|when is|convert)?\s*((?:noon|midnight|\d{1,2}:\d{2}(?:\s*(?:am|pm|a\.m\.|p\.m\.))?|\d{1,2}\s*(?:am|pm|a\.m\.|p\.m\.))\s+.*\b(?:in|to)\s+.+)$/i,
     function (m) { return ["convert_time", m[1]]; }],
    [/^(?:calc(?:ulate)?|compute|work out|math)[: ]+(.+)$/i, function (m) { return ["calculate", m[1]]; }],
    [/^(?:convert )?(-?\d+) (?:to|in|into) roman(?: numerals?)?$/i, function (m) { return ["roman_numeral", m[1]]; }],
    [/^convert (.+)$/i, function (m) { return ["convert_units", m[1]]; }],
    [/^what time is it in (.+)$|^(?:what(?:'s| is) )?(?:the )?time in (.+)$/i, function (m) { return ["time_in", (m[1] || m[2])]; }],
    [/^what(?:'s| is)(?: the)? date(?: today)?$|^what day is it(?: today)?$|^today'?s date$/i, function (m) { return ["current_date", ""]; }],
    [/^(?:how many )?days? between (.+?) and (.+)$/i, function (m) { return ["date_math", "between " + m[1] + " and " + m[2]]; }],
    [/^(?:how many )?days? (?:until|till|to) (.+)$|^how long (?:until|till) (.+)$/i, function (m) { return ["days_until", (m[1] || m[2])]; }],
    [/^(?:what(?:'s| is)(?: the date)? |what day is |when is |what date is )?((?:\d{1,6}|a|an|one|two|three|four|five|six|seven|eight|nine|ten) (?:day|week|month|year)s? (?:from(?: .+)?|ago|after .+|before .+))$/i,
     function (m) { return ["date_math", m[1]]; }],
    [/^(?:what )?day of (?:the )?week (?:is|was|will be|for) (.+)$|^what day (?:is|was|will be) ((?:\w+ \d{1,2}(?:st|nd|rd|th)?,? \d{3,4})|(?:\d{1,2} \w+ \d{3,4})|\d{4}-\d{2}-\d{2})$/i,
     function (m) { return ["date_math", "weekday " + (m[1] || m[2])]; }],
    [/^(?:flip|toss) a coin$/i, function (m) { return ["flip_coin", ""]; }],
    [/^roll (?:a |an )?(\d*d\d+)$/i, function (m) { return ["roll_dice", m[1]]; }],
    [/^roll (?:a |the )?(?:dice|die)$/i, function (m) { return ["roll_dice", "1d6"]; }],
    [/^(?:pick |give me |generate )?(?:a )?random number(?: (?:between|from) (.+))?$/i, function (m) { return ["random_number", (m[1] || "")]; }],
    [/^(?:generate|make|create|give me)(?: me)? (?:a |an )?(?:strong |secure |random )?password(?:(?: of| with)? (\d+)(?: char\w*)?)?$/i, function (m) { return ["make_password", (m[1] || "16")]; }],
    [/^(?:generate|make|create|give me)(?: me)? (?:a |an )?(?:new |random )?(?:uuid|guid)$/i, function (m) { return ["make_uuid", ""]; }],
    [/^sha-?256(?: of)?[: ]+(.+)$|^hash(?: of|:) (.+)$/i, function (m) { return ["hash_text", ((m[1] || m[2]))]; }],
    [/^base64 encode[: ]+(.+)$/i, function (m) { return ["base64_encode", m[1]]; }],
    [/^base64 decode[: ]+(.+)$/i, function (m) { return ["base64_decode", m[1]]; }],
    [/^(?:count (?:the )?words in|word count(?: of)?)[: ]+(.+)$/i, function (m) { return ["word_count", m[1]]; }],
    [/^reverse(?: the)? (?:text|words?|string)[: ]+(.+)$|^reverse: (.+)$/i, function (m) { return ["reverse_text", ((m[1] || m[2]))]; }],
    [/^(?:shout|uppercase)[: ]+(.+)$/i, function (m) { return ["shout", m[1]]; }],
    [/^morse(?: code)?(?: for| of)?[: ]+(.+)$/i, function (m) { return ["morse_code", m[1]]; }],
    [/^(?:pretty ?print|format|prettify) json[: ]+(.+)$/i, function (m) { return ["json_pretty", m[1]]; }],
    [/^is (-?\d+) (?:a )?prime$|^(?:prime factors of|factor|factorize) (-?\d+)$/i, function (m) { return ["is_prime", (m[1] || m[2])]; }],
    [/^roman numerals? (?:for |of )?(-?\d+)$|^(-?\d+) in roman numerals$/i, function (m) { return ["roman_numeral", (m[1] || m[2])]; }],
    [/^(?:(?:what(?:'s| is) )?(?:the |a )?tip on|tip(?: for)?) (-?\$?-?\d+(?:\.\d+)?)$/i, function (m) { return ["tip", m[1]]; }],
    [/^(?:check )?disk space$|^how much (?:disk |storage )?space (?:do i have|is (?:left|free))(?: left)?$|^how much storage (?:do i have|is left)$/i, function (m) { return ["disk_space", ""]; }],
    [/^how long has (?:my mac|this mac|it) been (?:on|up|running)$|^uptime$/i, function (m) { return ["uptime", ""]; }],
    [/^(?:how much )?(?:ram|memory)(?: (?:do i have|is free|is left|am i using))?$|^(?:ram|memory) usage$/i, function (m) { return ["memory_usage", ""]; }],
    [/^(?:cpu|processor) (?:load|usage)$|^how busy is (?:my mac|the cpu)$|^load average$/i, function (m) { return ["cpu_load", ""]; }],
    [/^(?:what(?:'s| is) )?my (?:local )?ip(?: address)?$/i, function (m) { return ["ip_address", ""]; }],
    [/^(?:what|which) wi-?fi(?: network)?(?: am i (?:on|connected to))?$|^wi-?fi name$/i, function (m) { return ["wifi_name", ""]; }],
    [/^(?:system|mac) info$|^what mac (?:is this|am i on)$|^about this mac$/i, function (m) { return ["system_info", ""]; }],
    [/^copy (.+) to (?:the |my )?clipboard$/i, function (m) { return ["copy_to_clipboard", m[1]]; }],
    [/^(?:lock|sleep)(?: the| my)? (?:screen|display)$/i, function (m) { return ["sleep_display", ""]; }],
    [/^(?:reveal|show)(?: me)? (.+?) in finder$/i, function (m) { return ["reveal_in_finder", m[1]]; }],
    [/^(?:list|show)(?: me)?(?: all)?(?: my)? shortcuts$|^what shortcuts do i have$/i, function (m) { return ["list_shortcuts", ""]; }],
    [/^(?:list|show)(?: me)?(?: all)?(?: my)? mcp tools$|^what mcp tools do i have$/i, function (m) { return ["list_mcp_tools", ""]; }],
    [/^call mcp (\S+ \S+(?: .+)?)$/i, function (m) { return ["call_mcp_tool", m[1]]; }],
    [/^(?:list|show)(?: me)?(?: all)?(?: my| the)?(?: open)? (?:chrome )?tabs$|^what tabs (?:do i have(?: open)?|are open)(?: in chrome)?$/i, function (m) { return ["list_tabs", ""]; }],
    [/^switch to tab (\d+(?:\.\d+)?)$|^switch to (?:the )?(.+?) tab$/i, function (m) { return ["switch_tab", ((m[1] || m[2]))]; }],
    [/^close tab (\d+(?:\.\d+)?)$|^close (?:the )?(.+?) tab$/i, function (m) { return ["close_tab", ((m[1] || m[2]))]; }],
    [/^read tab (\d+(?:\.\d+)?)$|^read (?!(?:this|the current) tab$)(?:the )?(.+?) tab$|^read (?:this|the current) tab$/i, function (m) { return ["read_tab", ((m[1] || m[2] || ""))]; }],
    [/^(?:read|ocr) (?:my |the )?screen$|^what(?:'s| is) on my screen$|^what does my screen say$/i, function (m) { return ["read_screen", ""]; }],
    [/^find (.+) on (?:my |the )?screen$|^is (.+) on (?:my |the )?screen$/i, function (m) { return ["read_screen", ((m[1] || m[2]))]; }],
    [/^read (?:the )?(?:document|pdf|doc|file called) (.+)$/i, function (m) { return ["read_document", m[1]]; }],
    [/^transcribe (?:the )?(?:video|audio|recording|file) (.+)$/i, function (m) { return ["transcribe_video", m[1]]; }],
    [/^what does (?:the )?(?:video|audio|recording) (.+) say$/i, function (m) { return ["transcribe_video", m[1]]; }],
    [/^find (.+?) in (?:the )?(?:document|pdf|doc) (.+)$/i, function (m) { return ["find_in_document", m[1] + "\t" + m[2]]; }],
    [/^what does (?:the )?(?:document|pdf|doc) (\S+) say about (.+)$/i, function (m) { return ["ask_document", "what does it say about " + m[2] + "\t" + m[1]]; }],
    [/^in (?:the )?(?:document|pdf|doc) (\S+?),? (.+)$/i, function (m) { return ["ask_document", m[2] + "\t" + m[1]]; }],
    [/^(?:on|from) my screen,? (.+)$/i, function (m) { return ["ask_screen", m[1]]; }],
    [/^remember that (.+)$/i, function (m) { return ["remember", m[1]]; }],
    [/^(?:recall|what do you remember about|what did i tell you about) (.+)$/i, function (m) { return ["recall", m[1]]; }],
    [/^forget (?:that |about )?(.+)$/i, function (m) { return ["forget", m[1]]; }],
    [/^run (?:the |my )?shortcut (.+)$|^run (.+) shortcut$/i, function (m) { return ["run_shortcut", ((m[1] || m[2]))]; }]
  ]);

  root.Samantha = { route: route, chain: chain, exact: exact, bare: bare, urlOf: urlOf, appMatch: appMatch, APPS: APPS, SITES: SITES,
                    stem: stem, keywords: keywords, isProject: isProject,
                    pageRoute: pageRoute, section: section, sound: sound, duration: duration, COLORS: COLORS, util: U };
})(typeof globalThis !== "undefined" ? globalThis : this);
