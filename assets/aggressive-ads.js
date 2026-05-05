(function () {
  var SANDBOX = "allow-scripts allow-same-origin allow-popups allow-popups-to-escape-sandbox allow-top-navigation-by-user-activation";

  function ready(fn) {
    if (document.readyState !== 'loading') fn();
    else document.addEventListener('DOMContentLoaded', fn);
  }

  ready(function () {

    // ============== STICKY BOTTOM BAR (728x90 desktop only) ==============
    if (window.innerWidth > 768 && !sessionStorage.getItem('nr_sticky_closed')) {
      var sticky = document.createElement('div');
      sticky.id = 'sticky-ad';
      sticky.innerHTML =
        '<button class="sticky-ad-close" aria-label="Cerrar">&times;</button>' +
        '<iframe src="/ads/728x90.html" width="728" height="90" scrolling="no" loading="lazy" class="ad-iframe" sandbox="' + SANDBOX + '"></iframe>';
      document.body.appendChild(sticky);
      sticky.querySelector('.sticky-ad-close').addEventListener('click', function () {
        sticky.remove();
        sessionStorage.setItem('nr_sticky_closed', '1');
      });
    }

    // ============== MODAL POPUP (after 5s, once per session) ==============
    if (!sessionStorage.getItem('nr_modal_shown')) {
      setTimeout(function () {
        var modal = document.createElement('div');
        modal.id = 'modal-ad';
        modal.innerHTML =
          '<div class="modal-ad-inner">' +
            '<button class="modal-ad-close" aria-label="Cerrar">&times;</button>' +
            '<span class="modal-ad-label">Publicidad</span>' +
            '<iframe src="/ads/300x250.html" width="300" height="250" scrolling="no" loading="lazy" class="ad-iframe" sandbox="' + SANDBOX + '"></iframe>' +
          '</div>';
        document.body.appendChild(modal);
        modal.querySelector('.modal-ad-close').addEventListener('click', function () {
          modal.remove();
        });
        modal.addEventListener('click', function (e) {
          if (e.target === modal) modal.remove();
        });
        sessionStorage.setItem('nr_modal_shown', '1');
      }, 5000);
    }

  });
})();
