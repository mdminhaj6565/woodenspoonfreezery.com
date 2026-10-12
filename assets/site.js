(function () {
  var btn = document.querySelector('.menu-btn');
  var nav = document.getElementById('nav');
  if (btn && nav) {
    btn.addEventListener('click', function () {
      var open = nav.classList.toggle('open');
      btn.setAttribute('aria-expanded', open ? 'true' : 'false');
    });
  }
  // open the flavour card a visitor jumped to (#slug)
  if (location.hash) {
    var el = document.getElementById(location.hash.slice(1));
    if (el) { var d = el.querySelector('details'); if (d) d.open = true; }
  }
})();
