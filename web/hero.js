// Hero trailer: loops muted under the copy; under reduced motion it holds its poster until someone presses play.
(function () {
  if (!matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  document.querySelectorAll('.hero-trailer, .hero-glow').forEach(function (v) { v.removeAttribute('autoplay'); v.pause(); });
})();
