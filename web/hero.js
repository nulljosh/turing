// Hero trailer (title cards cut, so no text fights the headline): loops muted behind the copy. "Sound on" plays it from the top with her voice; reduced motion holds the poster.
(function () {
  var v = document.querySelector('.hero-bg'), b = document.querySelector('.hero-sound');
  if (!v) return;
  if (matchMedia('(prefers-reduced-motion: reduce)').matches) { v.removeAttribute('autoplay'); v.pause(); }
  else { var p = v.play(); if (p && p.catch) p.catch(function () {}); }
  if (b) b.addEventListener('click', function () {
    var on = v.muted;
    v.muted = !on; if (on) { v.currentTime = 0; v.play(); }
    b.textContent = on ? 'Sound off' : 'Sound on'; b.setAttribute('aria-pressed', on ? 'true' : 'false');
  });
})();
