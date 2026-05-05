(function () {
  var SANDBOX = "allow-scripts allow-same-origin allow-popups allow-popups-to-escape-sandbox allow-top-navigation-by-user-activation";

  // ============== AD GUARD: bloqueia redirect agressivo da pagina principal ==============
  var lastUserClick = 0;
  document.addEventListener('click', function () { lastUserClick = Date.now(); }, true);
  document.addEventListener('keydown', function () { lastUserClick = Date.now(); }, true);

  window.addEventListener('beforeunload', function (e) {
    var sinceClick = Date.now() - lastUserClick;
    var nav = (performance.getEntriesByType && performance.getEntriesByType('navigation')[0]) || {};
    var sinceLoad = Date.now() - (nav.startTime || 0);
    // Se o user nao clicou nos ultimos 2s E a pagina ja carregou ha pelo menos 1s,
    // significa que algum script tentou redirect sem interacao do usuario.
    if (sinceClick > 2000 && sinceLoad > 1000) {
      console.warn('[AD GUARD] Redirect bloqueado (sem interacao do usuario)');
      e.preventDefault();
      e.returnValue = '';
      return '';
    }
  });

  // ============== AUTO-HIDE de slots vazios ==============
  function hideEmptyAdSlots() {
    var iframes = document.querySelectorAll('iframe.ad-iframe');
    iframes.forEach(function (iframe) {
      try {
        var doc = iframe.contentDocument;
        // Se o iframe carregou mas esta visualmente vazio, esconde o container
        if (doc && doc.body && doc.body.children.length <= 1) {
          var hasVisibleContent = false;
          var children = doc.body.querySelectorAll('iframe, img, ins, div[id*="placement"]');
          children.forEach(function (el) {
            var rect = el.getBoundingClientRect();
            if (rect.width > 10 && rect.height > 10) hasVisibleContent = true;
          });
          if (!hasVisibleContent && iframe.parentElement) {
            iframe.parentElement.style.display = 'none';
          }
        }
      } catch (err) {
        // Cross-origin: nao da pra inspecionar, deixa visivel mesmo
      }
    });
  }

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

    // Roda o auto-hide depois de 4s pra dar tempo dos ads carregarem
    setTimeout(hideEmptyAdSlots, 4000);
    setTimeout(hideEmptyAdSlots, 10000);

  });
})();
