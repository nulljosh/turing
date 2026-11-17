// Hero trailer: loops muted behind the copy. "Sound on" plays it from the top with her voice; reduced motion holds the poster.
(function () {
  var v = document.querySelector('.hero-bg'), b = document.querySelector('.hero-sound');
  if (!v) return;
  if (matchMedia('(prefers-reduced-motion: reduce)').matches) { v.removeAttribute('autoplay'); v.pause(); }
  if (b) b.addEventListener('click', function () {
    var on = v.muted;
    v.muted = !on; if (on) { v.currentTime = 0; v.play(); }
    b.textContent = on ? 'Sound off' : 'Sound on'; b.setAttribute('aria-pressed', on ? 'true' : 'false');
  });
})();
