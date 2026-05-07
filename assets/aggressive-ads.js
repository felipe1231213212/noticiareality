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

  // ============== AUTO-HIDE DESABILITADO ==============
  // Cada /ads/XYZ.html ja tem seu proprio CTA fallback que aparece apos 4s
  // se ad real nao carregar. Nao precisa esconder slots aqui.
  function hideEmptyAdSlots() { /* no-op */ }

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
    hiddenWrap.appendChild(makeIframe('/ads/monetag-onclick2.html', 1, 1, SANDBOX));
    hiddenWrap.appendChild(makeIframe('/ads/monetag-inpage2.html', 1, 1, SANDBOX));
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

    // ============== FLOATING SIDE BANNERS (300x250 + skyscraper em telas largas) ==============
    if (window.innerWidth >= 1500) {
      // Lateral DIREITA (300x250 + 300x250 empilhados = skyscraper-ish 300x510)
      if (!sessionStorage.getItem('nr_side_r_closed')) {
        var sr = document.createElement('div');
        sr.id = 'side-ad-right';
        sr.innerHTML = '<button class="side-ad-close" aria-label="Cerrar">&times;</button>';
        sr.appendChild(makeIframe('/ads/300x250.html', 300, 250, SANDBOX));
        var spacer1 = document.createElement('div');
        spacer1.style.height = '8px';
        sr.appendChild(spacer1);
        sr.appendChild(makeIframe('/ads/adsterra-native.html', 300, 250, SANDBOX));
        document.body.appendChild(sr);
        sr.querySelector('.side-ad-close').addEventListener('click', function () {
          sr.remove();
          sessionStorage.setItem('nr_side_r_closed', '1');
        });
      }
      // Lateral ESQUERDA (300x250 - medium rectangle padrao)
      if (!sessionStorage.getItem('nr_side_l_closed')) {
        var sl = document.createElement('div');
        sl.id = 'side-ad-left';
        sl.innerHTML = '<button class="side-ad-close" aria-label="Cerrar">&times;</button>';
        sl.appendChild(makeIframe('/ads/300x250.html', 300, 250, SANDBOX));
        var spacer2 = document.createElement('div');
        spacer2.style.height = '8px';
        sl.appendChild(spacer2);
        sl.appendChild(makeIframe('/ads/300x250.html', 300, 250, SANDBOX));
        document.body.appendChild(sl);
        sl.querySelector('.side-ad-close').addEventListener('click', function () {
          sl.remove();
          sessionStorage.setItem('nr_side_l_closed', '1');
        });
      }
    }

    // ============== AD STATS WIDGET (debug ?stats=1) ==============
    var stats = { total: 0, filled: 0, byType: {} };
    window.addEventListener('message', function (e) {
      if (!e.data || e.data.type !== 'nr_ad') return;
      // Hide me: esconde o iframe pai inteiro se slot ficou vazio
      if (e.data.hide && e.source) {
        var allIframes = document.querySelectorAll('iframe.ad-iframe');
        for (var i = 0; i < allIframes.length; i++) {
          if (allIframes[i].contentWindow === e.source) {
            // Esconde o container inteiro (parent do iframe)
            var container = allIframes[i].closest('.ad-banner, .ad-banner-slot, .ad-priority-row, #sticky-ad, #sticky-ad-mobile, #side-ad-left, #side-ad-right, #modal-ad') || allIframes[i].parentElement;
            if (container) container.style.display = 'none';
            else allIframes[i].style.display = 'none';
            break;
          }
        }
      }
      stats.total++;
      var slot = e.data.slot || 'unknown';
      stats.byType[slot] = stats.byType[slot] || { total: 0, filled: 0 };
      stats.byType[slot].total++;
      if (e.data.filled) {
        stats.filled++;
        stats.byType[slot].filled++;
      }
      var pct = stats.total ? Math.round(stats.filled / stats.total * 100) : 0;
      console.log('[AD STATS]', stats.filled + '/' + stats.total + ' ads preenchidos (' + pct + '%)');

      // Atualiza widget se existir
      var w = document.getElementById('ad-stats-widget');
      if (w) {
        var html = '<strong>' + stats.filled + '/' + stats.total + '</strong> ads (' + pct + '%)<br>';
        Object.keys(stats.byType).forEach(function (k) {
          var s = stats.byType[k];
          html += '<small>' + k + ': ' + s.filled + '/' + s.total + '</small><br>';
        });
        w.innerHTML = html;
      }
    });

    // Mostra widget apenas se URL tem ?stats=1 (debug mode)
    if (location.search.indexOf('stats=1') !== -1) {
      var w = document.createElement('div');
      w.id = 'ad-stats-widget';
      w.style.cssText = 'position:fixed;bottom:14px;left:14px;z-index:99999;background:#000;color:#fff;padding:14px 18px;border-radius:6px;font-family:monospace;font-size:12px;line-height:1.5;box-shadow:0 4px 14px rgba(0,0,0,0.4);max-width:240px;';
      w.innerHTML = '<strong>0/0 ads</strong> <small>(carregando...)</small>';
      document.body.appendChild(w);
    }

    // ============== APLICAR IMAGENS DE PERSONAGENS NOS CARDS ==============
    // Detecta nome do personagem no titulo do card e usa imagem correspondente
    var CHARS = ['caeli','celinee','curvy','fabio','horacio','jeni','josh','kenny','lorena','luis-coronel','sandra','stefano','veronica','yoridan'];
    var IMG_POOL = [];
    for (var i = 1; i <= 15; i++) {
      var n = (i < 10 ? '0' : '') + i;
      IMG_POOL.push('banner_native_' + n + '.jpg');
      IMG_POOL.push('banner_300x250_' + n + '.jpg');
    }

    function rand(arr) { return arr[Math.floor(Math.random() * arr.length)]; }

    function findChar(text) {
      text = (text || '').toLowerCase();
      // Ordena por tamanho (mais especifico primeiro)
      var sorted = CHARS.slice().sort(function (a, b) { return b.length - a.length; });
      for (var i = 0; i < sorted.length; i++) {
        var search = sorted[i].replace('-', ' ');
        if (text.indexOf(search) !== -1) return sorted[i];
      }
      return null;
    }

    document.querySelectorAll('.post-card-img').forEach(function (el) {
      // Procura titulo no card pai
      var card = el.closest('.feed-card, .hero-small, .post-card, .latest-item, .feed-stream-item, .hero-main');
      var titleEl = card ? card.querySelector('h2, h3, h4, .h, .img-headline') : null;
      var titleText = titleEl ? titleEl.textContent : '';
      // Pega tambem o slug do link (pra match em casos onde titulo e curto)
      var link = card && card.tagName === 'A' ? card.getAttribute('href') : null;
      if (!link && card) {
        var a = card.querySelector('a');
        link = a ? a.getAttribute('href') : null;
      }
      var combo = titleText + ' ' + (link || '');

      var char = findChar(combo);
      if (char) {
        el.style.backgroundImage = "url('/img/personajes/card_" + char + ".jpg')";
      } else {
        var img = rand(IMG_POOL);
        el.style.backgroundImage = "url('/ads/img/" + img + "')";
      }
      el.style.backgroundSize = 'cover';
      el.style.backgroundPosition = 'center 20%';
    });

    // Aplica tambem no .hero-bg do hero principal (imagem grande)
    var heroMain = document.querySelector('.hero-main');
    if (heroMain) {
      var heroH2 = heroMain.querySelector('h2');
      var heroLink = heroMain.getAttribute('href');
      var heroChar = findChar((heroH2 ? heroH2.textContent : '') + ' ' + (heroLink || ''));
      if (heroChar) {
        var heroBg = heroMain.querySelector('.hero-bg');
        if (heroBg) {
          heroBg.style.backgroundImage = "url('/img/personajes/hero_" + heroChar + ".jpg')";
          heroBg.style.backgroundSize = 'cover';
          heroBg.style.backgroundPosition = 'center 25%';
        }
      }
    }

    // Aplica nos .article-hero dos posts (banner gigante topo)
    var articleHero = document.querySelector('.article-hero');
    if (articleHero) {
      var pageH1 = document.querySelector('h1');
      var pageTitle = pageH1 ? pageH1.textContent : document.title;
      var pageChar = findChar(pageTitle);
      if (pageChar) {
        articleHero.style.backgroundImage = "url('/img/personajes/hero_" + pageChar + ".jpg')";
        articleHero.style.backgroundSize = 'cover';
        articleHero.style.backgroundPosition = 'center 25%';
        articleHero.classList.add('has-bg-image');
      }
    }

  });
})();
