// Hero wall: one long conversation with Samantha, from her own FAQ (faq.json, the answers she was trained to give).
// Questions sit on the right, her replies type in on the left, the way the app streams them.
(function () {
  var wall = document.getElementById('twall'); if (!wall) return;
  var still = matchMedia('(prefers-reduced-motion: reduce)').matches;
  var QA = [["What is Turing?", "Turing is the project: the pipeline, the repo, this whole effort to build small language models on consumer hardware. It is not a model itself. Turing is fixed as a name, the way Anthropic is fixed as a company name."], ["Summarize what Turing is in one sentence.", "Turing is a pipeline for building small language models on consumer hardware."], ["What base model does Samantha use?", "Qwen2.5-0.5B-Instruct-4bit, downloaded from Hugging Face via the mlx-community org, run through Apple's MLX framework on-device."], ["What data was Samantha trained on?", "Primarily this repo's own docs (README, WHITEPAPER, roadmap.md, TROUBLESHOOTING.md, this FAQ, and eval result writeups), repeated a few times so they are not drowned out."], ["What is the honest win condition?", "Ask Samantha to draft something in house voice, or answer a real question about one of these projects, and have the answer be good enough to use without rewriting it. Not \"beat GPT.\""], ["Who maintains this project?", "Joshua Trommel, listed as the author in LICENSE and WHITEPAPER.md."], ["Does Turing use a paid API or cloud service to train?", "No. Training runs entirely on-device via Apple's MLX framework, no cloud GPU, no API cost. The only paid-adjacent thing involved is brain's Cloudflare Workers AI usage for retrieval embeddings, which is separate infrastructure, not part of training itself."], ["Can Samantha answer general-knowledge questions, not just project facts?", "Yes, for clean factual/definitional queries (\"what's the capital of France\"), via a DuckDuckGo-instant-answer-then-Wikipedia-summary fallback (general_knowledge() in ask.py, reusing nimble's existing pattern)."], ["Can it answer \"who's the president\" or \"who's the prime minister of X\" correctly?", "Yes, as of 2026-09-13. DDG and a plain Wikipedia summary both describe the office, never today's actual holder, that was a real limitation for months."], ["How do I boot into Samantha and chat with her?", "Run ./samantha from the turing repo root. It activates the venv and launches chat.py's plain text loop, type a question, get an answer, exit or Ctrl+C to quit."], ["What happens if I run ./samantha with no flags at all?", "Plain-text mode, the default. No flag means the ordinary line-by-line CLI (chat.py's chat() function), not the TUI. Only --tui changes that."]];
  var el = function (t, c, x) { var e = document.createElement(t); if (c) e.className = c; if (x != null) e.textContent = x; return e; };
  var wait = function (ms) { return new Promise(function (r) { setTimeout(r, ms); }); };
  // Oldest lines leave the top once the thread fills the hero, the way a chat scrolls.
  function add(node) { wall.appendChild(node); while (wall.scrollHeight > wall.clientHeight && wall.children.length > 2) wall.firstChild.remove(); return node; }
  function ask(qa) {
    add(el('p', 'me', qa[0]));
    var her = add(el('div', 'her')); her.appendChild(el('img')).src = 'mascot.svg'; var t = her.appendChild(el('p'));
    if (still) { t.textContent = qa[1]; return Promise.resolve(); }
    var w = qa[1].split(' ');
    return w.reduce(function (q, x, j) { return q.then(function () { t.textContent = w.slice(0, j + 1).join(' '); add(her); return wait(45); }); }, wait(700)).then(function () { return wait(1800); });
  }
  if (still) { QA.slice(0, 3).forEach(ask); return; }
  var k = 0;
  (function loop() { ask(QA[k++ % QA.length]).then(loop); })();
})();

// Hero parallax: the wall drifts at 0.45, the copy lifts at 0.2 and fades. Off under reduced motion.
(function () {
  var bg = document.querySelector('.hero-bg'), copy = document.querySelector('.hero-copy');
  if (!bg || matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  var t = 0;
  addEventListener('scroll', function () {
    if (t) return;
    t = requestAnimationFrame(function () {
      t = 0; var y = scrollY, h = innerHeight; if (y > h * 1.2) return;
      bg.style.setProperty('--py', (y * .45) + 'px');
      copy.style.transform = 'translate3d(0,' + (y * .2) + 'px,0)'; copy.style.opacity = Math.max(0, 1 - y / (h * .7));
    });
  }, { passive: true });
})();
