// Mobile menu + dropdown toggles
(function () {
  var toggle = document.querySelector('.menu-toggle');
  var nav = document.getElementById('site-nav');
  if (toggle && nav) {
    toggle.addEventListener('click', function () {
      var open = nav.classList.toggle('open');
      toggle.setAttribute('aria-expanded', open);
      toggle.textContent = open ? 'Close' : 'Menu';
      document.body.style.overflow = open ? 'hidden' : '';
    });
  }
  document.querySelectorAll('.has-sub > button').forEach(function (btn) {
    btn.addEventListener('click', function () {
      var li = btn.parentElement;
      var open = !li.classList.contains('open');
      document.querySelectorAll('.has-sub.open').forEach(function (o) {
        o.classList.remove('open');
        o.querySelector('button').setAttribute('aria-expanded', 'false');
      });
      if (open) { li.classList.add('open'); btn.setAttribute('aria-expanded', 'true'); }
    });
  });
  document.addEventListener('click', function (e) {
    if (!e.target.closest('.has-sub')) {
      document.querySelectorAll('.has-sub.open').forEach(function (o) { o.classList.remove('open'); });
    }
  });
})();

// Videos: show the YouTube thumbnail; load the player only when clicked
document.querySelectorAll('.video[data-yt] .video-thumb').forEach(function (a) {
  a.addEventListener('click', function (e) {
    e.preventDefault();
    var box = a.parentElement;
    var f = document.createElement('iframe');
    f.src = 'https://www.youtube-nocookie.com/embed/' + box.getAttribute('data-yt') + '?autoplay=1&rel=0';
    f.title = 'Video';
    f.allow = 'accelerometer; autoplay; encrypted-media; picture-in-picture';
    f.allowFullscreen = true;
    box.replaceChildren(f);
  });
});
