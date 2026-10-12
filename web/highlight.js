// Colors the code in a reply: comments, strings, numbers and keywords. One scanner for every language; the fence's
// label only says whether "#" starts a comment and whether 'single quotes' are strings. It never throws and never
// stalls on half-typed code: an unterminated string or comment simply runs to the end. Spans are built with
// createElement and textContent, never innerHTML, because the text is model output.
// gui/Highlight.swift is the same scanner for the Mac and iPhone apps; keep the two in step.
// Run `node web/highlight.js` for the self-test.
(function (root) {
  var KEYWORDS = {};
  ('if else elif for while do return break continue switch case default goto func fn function def class struct enum union ' +
   'trait impl interface protocol extension let var const static mut pub use mod import from as export package type ' +
   'typealias in is not and or new delete try catch except finally throw throws raise defer guard where async await ' +
   'yield lambda with pass self this super true false nil null None True False void int char long short float double ' +
   'bool boolean string str unsigned signed u8 u16 u32 u64 usize i8 i16 i32 i64 isize f32 f64 String Int Bool Double ' +
   'Float Character Self then fi done esac').split(' ').forEach(function (w) { KEYWORDS[w] = 1; });
  var HASH = /^(?:python|py|bash|sh|shell|zsh|ruby|rb|yaml|yml|toml|r|perl|makefile|dockerfile)$/;
  var SQ = /^(?:js|javascript|jsx|ts|tsx|typescript|python|py|bash|sh|shell|zsh|ruby|rb|php|json|sql|yaml|yml|lua|perl)$/;

  // [{k: 'c' comment | 's' string | 'n' number | 'k' keyword | '' plain, t: text}], in order, covering the whole code.
  function tokens(code, lang) {
    code = String(code == null ? '' : code); lang = String(lang || '').toLowerCase();
    var hash = HASH.test(lang), sq = SQ.test(lang);
    var re = new RegExp([
      '(' + (hash ? '#[^\\n]*' : '//[^\\n]*|/\\*[\\s\\S]*?(?:\\*/|$)') + ')',
      '("""[\\s\\S]*?(?:"""|$)|\'\'\'[\\s\\S]*?(?:\'\'\'|$)|"(?:\\\\.|[^"\\\\\\n])*"?|`(?:\\\\.|[^`\\\\])*`?|' +
        (sq ? "'(?:\\\\.|[^'\\\\\\n])*'?" : "'(?:\\\\[^'\\n]*|[^'\\\\\\n])'") + ')',   // Rust's 'a is a lifetime, not a string
      '(0[xX][0-9a-fA-F_]+|\\d[\\d_]*(?:\\.\\d+)?(?:[eE][+-]?\\d+)?)',
      '(' + (hash ? '' : '#?') + '[A-Za-z_]\\w*)'                                                    // #include, #define in C
    ].join('|'), 'g');
    var out = [], at = 0, m;
    function plain(to) { if (to > at) out.push({ k: '', t: code.slice(at, to) }); }
    while ((m = re.exec(code))) {
      if (!m[0]) { re.lastIndex++; continue; }
      var k = m[1] ? 'c' : m[2] ? 's' : m[3] ? 'n' : (m[4].charAt(0) === '#' || KEYWORDS[m[4]]) ? 'k' : '';
      plain(m.index);
      out.push({ k: k, t: m[0] }); at = m.index + m[0].length;
    }
    plain(code.length);
    return out;
  }

  // Fills a <pre> with colored spans (class tk-c, tk-s, tk-n, tk-k) and text nodes for the rest.
  function paint(pre, code, lang) {
    pre.textContent = '';
    tokens(code, lang).forEach(function (t) {
      if (!t.k) return void pre.appendChild(document.createTextNode(t.t));
      var s = document.createElement('span'); s.className = 'tk-' + t.k; s.textContent = t.t; pre.appendChild(s);
    });
  }

  var api = { tokens: tokens, paint: paint };
  if (typeof module !== 'undefined' && module.exports) module.exports = api; else root.Highlight = api;

  if (typeof require !== 'undefined' && require.main === module) {
    var assert = require('assert');
    var kinds = function (code, lang) { return tokens(code, lang).filter(function (t) { return t.k; }).map(function (t) { return t.k + ':' + t.t; }); };
    assert.deepStrictEqual(kinds('#include <stdio.h>\nint x = 0x1F; // hi', 'c'), ['k:#include', 'k:int', 'n:0x1F', 'c:// hi']);
    assert.deepStrictEqual(kinds("# note\nx = 'a'  # tail", 'python'), ['c:# note', "s:'a'", 'c:# tail']);
    assert.deepStrictEqual(kinds("fn f<'a>(x: &'a str) -> char { 'c' }", 'rust'), ['k:fn', 'k:str', 'k:char', "s:'c'"]);
    assert.deepStrictEqual(kinds('const s = `a${b}`;', 'js'), ['k:const', 's:`a${b}`']);
    assert.deepStrictEqual(kinds('def f():\n    """if for\n    return"""\n    return 1.5', 'python'), ['k:def', 's:"""if for\n    return"""', 'k:return', 'n:1.5']);
    assert.deepStrictEqual(kinds('x1 = 2', 'swift'), ['n:2']);
    assert.deepStrictEqual(kinds('"abc', 'c'), ['s:"abc']);                       // unterminated: runs to the end, no throw
    assert.deepStrictEqual(kinds('/* open', 'c'), ['c:/* open']);
    assert.deepStrictEqual(kinds('', 'c'), []);
    ['let a = "b\\"c" // d\n', "echo 'x' `y` #z\n", 'if (a) { return "\n', '\u{1F600} "é" 0x', "'''", '"""'].forEach(function (s) {
      ['c', 'python', 'js', 'rust', 'bash', ''].forEach(function (l) {
        assert.strictEqual(tokens(s, l).map(function (t) { return t.t; }).join(''), s);   // tokens always cover the code exactly
      });
    });
    console.log('highlight ok');
  }
})(this);
