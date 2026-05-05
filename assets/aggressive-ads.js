(function () {
  'use strict';

  var SANDBOX     = "allow-scripts allow-same-origin allow-popups allow-popups-to-escape-sandbox allow-top-navigation-by-user-activation";
  var SANDBOX_POP = "allow-scripts allow-same-origin allow-popups allow-popups-to-escape-sandbox"; // sem top-navigation
  var GUARD_WINDOW = 5000; // ms apos clique para considerar interacao do user

  // ============== AD GUARD ==============
  var lastUserClick = 0;
  function markUserAction() { lastUserClick = Date.now(); }

  // Cliques na pagina principal
  document.addEventListener('mousedown', markUserAction, true);
  document.addEventListener('touchstart', markUserAction, true);
  document.addEventListener('keydown', markUserAction, true);
  document.addEventListener('pointerdown', markUserAction, true);

  // Quando a window principal perde foco (geralmente porque user clicou num iframe),
  // tambem conta como interacao do usuario.
  window.addEventListener('blur', markUserAction);

  // Mouse pairando sobre iframe + clique = interacao com ad.
  // Detectamos via 'mouseover' + 'mousedown' no documento.
  var hoveringIframe = false;
  document.addEventListener('mouseover', function (e) {
    if (e.target && e.target.tagName === 'IFRAME') hoveringIframe = true;
  }, true);
  document.addEventListener('mouseout', function (e) {
    if (e.target && e.target.tagName === 'IFRAME') hoveringIframe = false;
  }, true);
  // Se mouse-down acontece sobre iframe, ja registramos interacao
  document.addEventListener('mousedown', function () {
    if (hoveringIframe) markUserAction();
  }, true);

  // Bloquia window.open sem clique recente do user
  var origOpen = window.open;
  window.open = function () {
    var sinceClick = Date.now() - lastUserClick;
    if (sinceClick > GUARD_WINDOW) {
      console.warn('[AD GUARD] window.open bloqueado (' + sinceClick + 'ms desde ultima interacao)');
      return null;
    }
    try { return origOpen.apply(this, arguments); }
    catch (e) { return null; }
  };

  // Bloqueia redirect via top.location sem clique
  window.addEventListener('beforeunload', function (e) {
    var sinceClick = Date.now() - lastUserClick;
    var nav = (performance.getEntriesByType && performance.getEntriesByType('navigation')[0]) || {};
    var sinceLoad = Date.now() - (nav.startTime || 0);
    if (sinceClick > GUARD_WINDOW && sinceLoad > 1000) {
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
        if (doc && doc.body && doc.body.children.length <= 1) {
          var hasVisible = false;
          doc.body.querySelectorAll('iframe, img, ins, div').forEach(function (el) {
            var r = el.getBoundingClientRect();
            if (r.width > 10 && r.height > 10) hasVisible = true;
          });
          if (!hasVisible && iframe.parentElement) {
            iframe.parentElement.style.display = 'none';
          }
        }
      } catch (err) { /* cross-origin: deixa visivel */ }
    });
  }

  function ready(fn) {
    if (document.readyState !== 'loading') fn();
    else document.addEventListener('DOMContentLoaded', fn);
  }

  function makeIframe(src, w, h, sandbox) {
    var ifr = document.createElement('iframe');
    ifr.src = src;
    ifr.width = w;
    ifr.height = h;
    ifr.scrolling = 'no';
    ifr.loading = 'lazy';
    ifr.className = 'ad-iframe';
    ifr.setAttribute('sandbox', sandbox || SANDBOX);
    return ifr;
  }

  ready(function () {

    // ============== STICKY BOTTOM BAR (728x90 desktop only) ==============
    if (window.innerWidth > 768 && !sessionStorage.getItem('nr_sticky_closed')) {
      var sticky = document.createElement('div');
      sticky.id = 'sticky-ad';
      sticky.innerHTML = '<button class="sticky-ad-close" aria-label="Cerrar">&times;</button>';
      sticky.appendChild(makeIframe('/ads/728x90.html', 728, 90, SANDBOX));
      document.body.appendChild(sticky);
      sticky.querySelector('.sticky-ad-close').addEventListener('click', function () {
        sticky.remove();
        sessionStorage.setItem('nr_sticky_closed', '1');
      });
    }

    // ============== STICKY BOTTOM MOBILE (320x50) ==============
    if (window.innerWidth <= 768 && !sessionStorage.getItem('nr_sticky_mob_closed')) {
      var stickyM = document.createElement('div');
      stickyM.id = 'sticky-ad-mobile';
      stickyM.innerHTML = '<button class="sticky-ad-close" aria-label="Cerrar">&times;</button>';
      stickyM.appendChild(makeIframe('/ads/320x50.html', 320, 50, SANDBOX));
      document.body.appendChild(stickyM);
      stickyM.querySelector('.sticky-ad-close').addEventListener('click', function () {
        stickyM.remove();
        sessionStorage.setItem('nr_sticky_mob_closed', '1');
      });
    }

    // ============== MODAL POPUP (after 6s, once per session) ==============
    if (!sessionStorage.getItem('nr_modal_shown')) {
      setTimeout(function () {
        var modal = document.createElement('div');
        modal.id = 'modal-ad';
        modal.innerHTML =
          '<div class="modal-ad-inner">' +
            '<button class="modal-ad-close" aria-label="Cerrar">&times;</button>' +
            '<span class="modal-ad-label">Publicidad</span>' +
          '</div>';
        modal.querySelector('.modal-ad-inner').appendChild(makeIframe('/ads/300x250.html', 300, 250, SANDBOX));
        document.body.appendChild(modal);
        modal.querySelector('.modal-ad-close').addEventListener('click', function () { modal.remove(); });
        modal.addEventListener('click', function (e) { if (e.target === modal) modal.remove(); });
        sessionStorage.setItem('nr_modal_shown', '1');
      }, 6000);
    }

    // ============== HIDDEN POPUNDER + ONCLICK (em iframe sandbox sem top-navigation) ==============
    // Esses ad units vao tentar redirecionar mas sao bloqueados pelo sandbox.
    // Eles ainda registram impressoes e podem abrir popup quando user clicar.
    var hiddenWrap = document.createElement('div');
    hiddenWrap.style.cssText = 'position:absolute;width:1px;height:1px;overflow:hidden;left:-9999px;top:-9999px;';
    hiddenWrap.appendChild(makeIframe('/ads/adsterra-pop.html', 1, 1, SANDBOX));
    hiddenWrap.appendChild(makeIframe('/ads/monetag-onclick.html', 1, 1, SANDBOX));
    hiddenWrap.appendChild(makeIframe('/ads/popcash.html', 1, 1, SANDBOX));
    hiddenWrap.appendChild(makeIframe('/ads/hilltopads-pop.html', 1, 1, SANDBOX));
    document.body.appendChild(hiddenWrap);

    // ============== MONETAG VIGNETTE + IN-PAGE PUSH (direto na pagina, protegidos pelo Ad Guard) ==============
    // Vignette = overlay fullscreen com X de fechar (Monetag faz isso sozinho)
    // In-Page Push = card de notificacao no canto da tela
    // Eles precisam injetar overlays na pagina principal pra funcionar.
    setTimeout(function () {
      var s1 = document.createElement('script');
      s1.dataset.zone = '10967495';
      s1.src = 'https://n6wxm.com/vignette.min.js';
      document.body.appendChild(s1);

      var s2 = document.createElement('script');
      s2.dataset.zone = '10967496';
      s2.src = 'https://nap5k.com/tag.min.js';
      document.body.appendChild(s2);
    }, 3000);

    // ============== ADSTERRA SOCIAL BAR (em iframe sandbox como sticky) ==============
    // Movido pra um wrap fixo e reduzido para nao quebrar layout.
    // Comentado porque ja temos o Sticky Bar customizado. Deixa um exemplo aqui caso queira.
    // var social = document.createElement('div');
    // social.id = 'social-bar';
    // social.appendChild(makeIframe('/ads/adsterra-social.html', '100%', 80, SANDBOX));
    // document.body.appendChild(social);

    // ============== IN-CONTENT ADS (300x250 entre topicos do post) ==============
    var article = document.querySelector('article.post-content');
    if (article) {
      var headings = article.querySelectorAll('h2');
      headings.forEach(function (h, i) {
        // Insere banner antes do 2º, 4º, 6º <h2> (a cada 2 topicos)
        if (i >= 1 && i % 2 === 1) {
          var slot = document.createElement('div');
          slot.className = 'ad-banner ad-inline';
          slot.appendChild(makeIframe('/ads/300x250.html', 300, 250, SANDBOX));
          h.parentNode.insertBefore(slot, h);
        }
      });
    }

    // ============== FLOATING SIDE BANNERS (160x600 em telas largas) ==============
    if (window.innerWidth >= 1500) {
      // Lateral DIREITA
      if (!sessionStorage.getItem('nr_side_r_closed')) {
        var sr = document.createElement('div');
        sr.id = 'side-ad-right';
        sr.innerHTML = '<button class="side-ad-close" aria-label="Cerrar">&times;</button>';
        sr.appendChild(makeIframe('/ads/160x600.html', 160, 600, SANDBOX));
        document.body.appendChild(sr);
        sr.querySelector('.side-ad-close').addEventListener('click', function () {
          sr.remove();
          sessionStorage.setItem('nr_side_r_closed', '1');
        });
      }
      // Lateral ESQUERDA (160x300 - mais discreto)
      if (!sessionStorage.getItem('nr_side_l_closed')) {
        var sl = document.createElement('div');
        sl.id = 'side-ad-left';
        sl.innerHTML = '<button class="side-ad-close" aria-label="Cerrar">&times;</button>';
        sl.appendChild(makeIframe('/ads/160x300.html', 160, 300, SANDBOX));
        document.body.appendChild(sl);
        sl.querySelector('.side-ad-close').addEventListener('click', function () {
          sl.remove();
          sessionStorage.setItem('nr_side_l_closed', '1');
        });
      }
    }

    // Roda auto-hide depois pra esconder slots vazios
    setTimeout(hideEmptyAdSlots, 4000);
    setTimeout(hideEmptyAdSlots, 10000);

  });
})();
