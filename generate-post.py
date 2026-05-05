#!/usr/bin/env python3
"""
Gerador de posts pra Noticia Reality.

Pega um arquivo .txt e cospe um post HTML completo com todos os ads no lugar.

USO:
    python generate-post.py "caminho/do/arquivo.txt"
    python generate-post.py "caminho/do/arquivo.txt" --category gh --color blue
    python generate-post.py "caminho/do/arquivo.txt" --slug nome-customizado

FORMATO ESPERADO DO .txt:
    # HEADLINE: Titulo do post (opcional - se nao tiver usa o nome do arquivo)
    ## Subtitulo (opcional - vira H2)
    Texto do corpo.. paragrafos longos sao divididos em chunks de 3 frases automaticamente.

OPCOES:
    --category lcdlf|gh|farandula  (auto-detectado se omitido)
    --color    red|blue|purple|orange|gold|green  (default: depende da categoria)
    --slug     nome-do-arquivo-html  (default: derivado do titulo)
    --date     "07 de mayo de 2026"  (default: hoje)
    --update-home  inclui o post na lista "Ultima hora" da homepage

EXEMPLO:
    python generate-post.py "posts/JENI Y SANDRA SE PELEAN POR JOSH.txt"
    python generate-post.py "rascunho.txt" --category gh --color blue --update-home
"""

import sys
import os
import re
import html
import argparse
import unicodedata
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
POSTS_DIR = PROJECT_ROOT / 'posts'
INDEX_FILE = PROJECT_ROOT / 'index.html'

CATEGORIES = {
    'lcdlf': {'tag': 'LCDLF 6', 'name': 'La Casa de los Famosos', 'eyebrow': 'EXCLUSIVA', 'color': 'red'},
    'gh':    {'tag': 'Gran Hermano', 'name': 'Gran Hermano', 'eyebrow': 'EN VIVO', 'color': 'gold'},
    'farandula': {'tag': 'Farandula', 'name': 'Farandula', 'eyebrow': 'POLEMICA', 'color': 'purple'},
}

# Personagens reconhecidos pra auto-bold
NAMES = [
    # LCDLF 6
    'Caeli', 'Fabio Agostini', 'Fabio', 'Celinee Santos', 'Celinee', 'Kenny Rodriguez', 'Kenny',
    'Josh Martinez', 'Josh', 'Stefano Piccioni', 'Stefano', 'Curvy Zelma', 'Curvy', 'Yoridan Martinez', 'Yoridan',
    'Eduardo Antonio', 'El Divo', 'Horacio Pancheri', 'Horacio', 'Luis Coronel', 'Laura Zapata', 'Laura G',
    'Lupita Jones', 'Kunno', 'Zoe Bayona', 'Jimena Galego', 'Jeni', 'Sandra',
    # Gran Hermano
    'Tamara Paganini', 'Tamara', 'Pincoya', 'Jennifer Torres', 'Nazareno Pompei', 'Nazareno',
    'Brian Sarmiento', 'Brian', 'Yipio', 'Danelik', 'Grecia Colmenares', 'Grecia', 'Luana Fernandez', 'Luana',
    'Eduardo Carrera', 'Santiago del Moro', 'Yanina Zilli', 'Martin Rodriguez',
    'Gladys', 'La Bomba Tucumana', 'Daniela De Lucia', 'Juanicar', 'Franco Zunino', 'Titi Tcherkaski',
]

MESES = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']
MESES_ABBR = ['ene', 'feb', 'mar', 'abr', 'mayo', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic']


def normalize_title(title):
    """Se titulo tiver >= 70% letras maiusculas, converte pra Sentence case."""
    letters = [c for c in title if c.isalpha()]
    if not letters:
        return title
    upper_ratio = sum(1 for c in letters if c.isupper()) / len(letters)
    if upper_ratio < 0.7:
        return title  # ja esta normal
    # Sentence case: primeira letra de cada frase maiuscula, resto minusculo
    # Mas mantem nomes proprios em capitalizado
    lower = title.lower()
    # Primeira letra do titulo
    result = lower[0].upper() + lower[1:]
    # Capitaliza nomes conhecidos
    for name in NAMES:
        pattern = r'\b' + re.escape(name.lower()) + r'\b'
        result = re.sub(pattern, name, result, flags=re.IGNORECASE)
    return result


def slugify(text):
    """Converte titulo pra slug de URL."""
    text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('ascii')
    text = re.sub(r'[^\w\s-]', '', text).strip().lower()
    text = re.sub(r'[\s_]+', '-', text)
    text = re.sub(r'-+', '-', text)
    return text[:90]


def detect_category(text, filename):
    """Auto-detecta categoria por palavras-chave."""
    combo = (text + ' ' + filename).lower()
    lcdlf_kw = ['lcdlf', 'casa de los famosos', 'caeli', 'fabio', 'celinee', 'josh', 'kunno',
                'laura zapata', 'kenny', 'jeni', 'sandra', 'curvy', 'stefano', 'telemundo']
    gh_kw    = ['gran hermano', 'pincoya', 'tamara', 'nazareno', 'santiago del moro',
                'telefe', 'generacion dorada', 'brian sarmiento', 'yipio', 'danelik']
    if sum(1 for k in gh_kw if k in combo) > sum(1 for k in lcdlf_kw if k in combo):
        return 'gh'
    return 'lcdlf'


def parse_content(raw):
    """Parsa o .txt em titulo + lista de blocos (h2, p)."""
    # Headline
    title = None
    m = re.search(r'^#\s*HEADLINE:\s*(.+)$', raw, re.MULTILINE | re.IGNORECASE)
    if m:
        title = m.group(1).strip()
        raw = (raw[:m.start()] + raw[m.end():]).strip()

    blocks = []
    paragraphs = re.split(r'\n\s*\n', raw.strip())

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        if para.startswith('## '):
            blocks.append(('h2', para[3:].strip()))
            continue
        if para.startswith('# '):
            continue  # ignora outros headers comentados
        # Junta linhas quebradas e separa em frases
        flat = re.sub(r'\s+', ' ', para)
        sentences = re.split(r'(?<=[.!?])\s+', flat)
        sentences = [s.strip() for s in sentences if s.strip()]
        # Grupos de 3 frases por paragrafo
        for i in range(0, len(sentences), 3):
            chunk = ' '.join(sentences[i:i+3]).strip()
            if chunk:
                blocks.append(('p', chunk))

    return title, blocks


def bold_names(escaped_text):
    """Coloca <strong> em nomes conhecidos. Recebe texto JA escapado."""
    for name in sorted(NAMES, key=len, reverse=True):
        # Match exato com word boundaries (cuida de hifens em nomes compostos)
        pattern = r'\b' + re.escape(name) + r'\b'
        escaped_text = re.sub(pattern, lambda m: '<strong>' + m.group(0) + '</strong>', escaped_text)
    return escaped_text


def make_summary(blocks):
    """Gera 3-4 bullets de resumo a partir das primeiras frases."""
    paragraphs = [t for k, t in blocks if k == 'p']
    if not paragraphs:
        return []
    bullets = []
    for p in paragraphs[:5]:
        sents = re.split(r'(?<=[.!?])\s+', p)
        if sents and sents[0]:
            s = sents[0].strip()
            if len(s) > 30:
                bullets.append(s[:140].rsplit(' ', 1)[0] + ('...' if len(s) > 140 else ''))
        if len(bullets) >= 4:
            break
    return bullets


def render_blocks(blocks):
    """Renderiza blocos em HTML, intercalando ads (G1-style scroll depth)."""
    out = []
    paragraph_count = 0
    ad_inserted = 0
    AD_EVERY_N_PARAS = 3

    AD_INLINE_HTML = (
        '          <div class="ad-separator">Continua despues de la publicidad</div>\n'
        '          <div class="ad-banner ad-inline">\n'
        '            <iframe src="/ads/300x250.html" width="300" height="250" scrolling="no" loading="lazy" class="ad-iframe"\n'
        '              sandbox="allow-scripts allow-same-origin allow-popups allow-popups-to-escape-sandbox allow-top-navigation-by-user-activation"></iframe>\n'
        '          </div>\n'
        '          <div class="ad-separator ad-separator-bottom"></div>'
    )

    AD_INLINE_LARGE = (
        '          <div class="ad-separator">Continua despues de la publicidad</div>\n'
        '          <div class="ad-banner ad-inline">\n'
        '            <iframe src="/ads/728x90.html" width="728" height="90" scrolling="no" loading="lazy" class="ad-iframe"\n'
        '              sandbox="allow-scripts allow-same-origin allow-popups allow-popups-to-escape-sandbox allow-top-navigation-by-user-activation"></iframe>\n'
        '          </div>\n'
        '          <div class="ad-separator ad-separator-bottom"></div>'
    )

    for kind, text in blocks:
        esc = html.escape(text, quote=False)
        esc = bold_names(esc)
        if kind == 'h2':
            # Se ja tem N paragrafos, insere ad ANTES do h2
            if paragraph_count >= AD_EVERY_N_PARAS:
                out.append(AD_INLINE_HTML if ad_inserted % 2 == 0 else AD_INLINE_LARGE)
                ad_inserted += 1
                paragraph_count = 0
            out.append('          <h2>{}</h2>'.format(esc))
        else:
            out.append('          <p>{}</p>'.format(esc))
            paragraph_count += 1
            # A cada N paragrafos seguidos sem h2, tambem insere ad
            if paragraph_count >= AD_EVERY_N_PARAS:
                out.append(AD_INLINE_HTML if ad_inserted % 2 == 0 else AD_INLINE_LARGE)
                ad_inserted += 1
                paragraph_count = 0

    return '\n\n'.join(out)


def render_summary(bullets):
    if not bullets:
        return ''
    items = '\n'.join('              <li>{}</li>'.format(html.escape(b, quote=False)) for b in bullets)
    return (
        '          <details class="summary-box" open>\n'
        '            <summary>Ver resumen rapido</summary>\n'
        '            <ul>\n'
        '{}\n'
        '            </ul>\n'
        '          </details>'
    ).format(items)


def format_date(dt=None):
    d = dt or datetime.now()
    return '{:02d} de {} de {}'.format(d.day, MESES[d.month-1], d.year)


def format_date_short(dt=None):
    d = dt or datetime.now()
    return '{:02d} {} {}'.format(d.day, MESES_ABBR[d.month-1], d.year)


# ========== TEMPLATE ==========
POST_TEMPLATE = '''<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title} - Noticia Reality</title>
  <meta name="description" content="{description}">
  <meta name="keywords" content="{keywords}">
  <meta property="og:title" content="{title}">
  <meta property="og:description" content="{description}">
  <meta property="og:type" content="article">
  <link rel="stylesheet" href="../style.css">
</head>
<body>
  <div class="top-bar"><div class="container"><span>Noticia Reality</span><div><a href="/sobre.html">Nosotros</a><a href="/contato.html">Contacto</a><a href="/privacidade.html">Privacidad</a></div></div></div>
  <header><div class="container"><a href="/" class="logo">NOTICIA<span>REALITY</span></a></div></header>
  <nav class="main-nav"><div class="container"><a href="/">Inicio</a><a href="/#lcdlf">La Casa de los Famosos</a><a href="/#gh">Gran Hermano</a><a href="/#farandula">Farandula</a><a href="/#videos">Videos</a></div></nav>

  <div class="container">
    <div class="content-with-sidebar" style="padding-top:24px;">
      <div>
        <a href="/" class="back-link">&larr; Volver al inicio</a>
        <article class="post-content">
          <div class="post-hero post-hero-{color}">
            <span class="post-hero-tag">{tag}</span>
            <span class="post-hero-eyebrow">{eyebrow}</span>
          </div>
          <h1>{title}</h1>
          <div class="post-meta">
            <span>{date}</span>
            <span class="tag" style="margin:0;">{tag}</span>
          </div>

{summary}

{body}

          <div class="article-tags">
            <a href="/#{cat_anchor}">{tag}</a>
            <a href="/">Reality shows</a>
            <a href="/">2026</a>
            <a href="/">Farandula latina</a>
          </div>

          <!-- ADSTERRA: Banner 468x60 antes share-bar (sandboxed) -->
          <div class="ad-banner ad-after-content">
            <iframe src="/ads/468x60.html" width="468" height="60" scrolling="no" loading="lazy" class="ad-iframe"
              sandbox="allow-scripts allow-same-origin allow-popups allow-popups-to-escape-sandbox allow-top-navigation-by-user-activation"></iframe>
          </div>

          <div class="share-bar">
            <span>Compartir:</span>
            <a href="#" class="share-btn fb">Facebook</a>
            <a href="#" class="share-btn tw">Twitter</a>
            <a href="#" class="share-btn wa">WhatsApp</a>
          </div>

          <!-- NEWSLETTER CTA -->
          <div class="newsletter" style="margin: 32px 0;">
            <div class="newsletter-content">
              <span class="newsletter-eyebrow">Newsletter diaria</span>
              <h3>No te pierdas ningun chisme</h3>
              <p>Recibe los eliminados, peleas y momentos virales en tu correo.</p>
              <form class="newsletter-form" onsubmit="event.preventDefault(); this.querySelector('button').textContent='&#10003; Suscrito';">
                <input type="email" placeholder="tu@correo.com" required>
                <button type="submit">Suscribirme</button>
              </form>
            </div>
          </div>

          <!-- MAS LEIDAS POS-ARTIGO -->
          <section class="related-section">
            <h3>Mas <span class="accent">leidas</span></h3>
            <div class="more-portal-list">
              <a href="nazareno-eliminado-gran-hermano.html" class="feed-stream-item">
                <div class="feed-img"><div class="post-card-img img-blue"><span class="img-headline">NAZARENO</span></div></div>
                <div class="feed-body">
                  <span class="feed-eyebrow">Gran Hermano</span>
                  <h3>Nazareno eliminado tras pelea con Pincoya</h3>
                  <span class="feed-meta">05 mayo 2026</span>
                </div>
              </a>
              <a href="josh-lider-lcdlf-semana-11.html" class="feed-stream-item">
                <div class="feed-img"><div class="post-card-img img-red"><span class="img-headline">JOSH</span></div></div>
                <div class="feed-body">
                  <span class="feed-eyebrow">LCDLF 6</span>
                  <h3>Josh es el nuevo lider de LCDLF 6</h3>
                  <span class="feed-meta">05 mayo 2026</span>
                </div>
              </a>
              <a href="laura-g-eliminada-lcdlf.html" class="feed-stream-item">
                <div class="feed-img"><div class="post-card-img img-purple"><span class="img-headline">LAURA G</span></div></div>
                <div class="feed-body">
                  <span class="feed-eyebrow">LCDLF 6</span>
                  <h3>Laura G, novena eliminada de LCDLF 6</h3>
                  <span class="feed-meta">21 abril 2026</span>
                </div>
              </a>
              <a href="tamara-paganini-lider-gh.html" class="feed-stream-item">
                <div class="feed-img"><div class="post-card-img img-gold"><span class="img-headline">TAMARA</span></div></div>
                <div class="feed-body">
                  <span class="feed-eyebrow">Gran Hermano</span>
                  <h3>Tamara Paganini, lider de la semana 10</h3>
                  <span class="feed-meta">28 abril 2026</span>
                </div>
              </a>
            </div>
          </section>
        </article>
        <!-- ADSTERRA: Banner 728x90 (sandboxed) -->
        <div class="ad-banner ad-after-content">
          <iframe src="/ads/728x90.html" width="728" height="90" scrolling="no" loading="lazy" class="ad-iframe"
            sandbox="allow-scripts allow-same-origin allow-popups allow-popups-to-escape-sandbox allow-top-navigation-by-user-activation"></iframe>
        </div>
      </div>

      <aside class="sidebar">
        <!-- ADSTERRA: Banner 300x250 (sandboxed) -->
        <div class="ad-banner ad-sidebar">
          <iframe src="/ads/300x250.html" width="300" height="250" scrolling="no" loading="lazy" class="ad-iframe"
            sandbox="allow-scripts allow-same-origin allow-popups allow-popups-to-escape-sandbox allow-top-navigation-by-user-activation"></iframe>
        </div>
        <div class="widget">
          <h3>Mas Leidos</h3>
          <div class="trending-item"><span class="trending-num">1</span><div><h4><a href="nazareno-eliminado-gran-hermano.html">Nazareno eliminado de GH 2026</a></h4><p class="meta">05 mayo 2026</p></div></div>
          <div class="trending-item"><span class="trending-num">2</span><div><h4><a href="josh-lider-lcdlf-semana-11.html">Josh, lider de LCDLF 6</a></h4><p class="meta">05 mayo 2026</p></div></div>
          <div class="trending-item"><span class="trending-num">3</span><div><h4><a href="laura-g-eliminada-lcdlf.html">Laura G eliminada</a></h4><p class="meta">21 abril 2026</p></div></div>
          <div class="trending-item"><span class="trending-num">4</span><div><h4><a href="tamara-paganini-lider-gh.html">Tamara Paganini, lider de GH</a></h4><p class="meta">28 abril 2026</p></div></div>
        </div>

        <!-- ADSTERRA: Banner 160x300 (sandboxed) -->
        <div class="ad-banner ad-sidebar">
          <iframe src="/ads/160x300.html" width="160" height="300" scrolling="no" loading="lazy" class="ad-iframe"
            sandbox="allow-scripts allow-same-origin allow-popups allow-popups-to-escape-sandbox allow-top-navigation-by-user-activation"></iframe>
        </div>

        <!-- ADSTERRA: Native Banner sidebar (sandboxed) -->
        <div class="ad-banner ad-sidebar">
          <iframe src="/ads/adsterra-native.html" width="300" height="250" scrolling="no" loading="lazy" class="ad-iframe"
            sandbox="allow-scripts allow-same-origin allow-popups allow-popups-to-escape-sandbox allow-top-navigation-by-user-activation"></iframe>
        </div>
      </aside>
    </div>
  </div>

  <footer><div class="container"><div class="footer-grid"><div class="footer-col"><h3>Noticia Reality</h3><p>Tu fuente numero uno de noticias de reality shows latinos.</p></div><div class="footer-col"><h3>Secciones</h3><a href="/">Inicio</a><a href="/#lcdlf">LCDLF</a><a href="/#gh">Gran Hermano</a></div><div class="footer-col"><h3>Legal</h3><a href="/sobre.html">Nosotros</a><a href="/contato.html">Contacto</a><a href="/privacidade.html">Privacidad</a><a href="/termos.html">Terminos</a></div></div><div class="footer-bottom"><p>&copy; 2026 Noticia Reality - Todos los derechos reservados</p></div></div></footer>
<script src="/assets/aggressive-ads.js" defer></script>
</body>
</html>
'''


def update_homepage(slug, title, tag, color_card, date_short):
    """Insere o post no topo da secao 'Ultima hora' do index.html."""
    if not INDEX_FILE.exists():
        return False
    with open(INDEX_FILE, 'r', encoding='utf-8') as f:
        idx = f.read()

    short_title = title[:80] + ('...' if len(title) > 80 else '')
    img_text = title.split()[0][:8].upper() if title else 'NEW'

    color_map = {'red': 'img-red', 'blue': 'img-blue', 'purple': 'img-purple',
                 'orange': 'img-orange', 'gold': 'img-gold', 'green': 'img-green'}
    img_cls = color_map.get(color_card, 'img-red')

    new_card = '''<a href="posts/{slug}.html" class="latest-item">
            <div class="latest-item-img post-card-img {img_cls}">
              <span class="img-headline" style="font-size:0.9rem;">{img_text}</span>
            </div>
            <div class="latest-item-body">
              <span class="category">{tag}</span>
              <h4>{short_title}</h4>
              <span class="meta">{date_short} &bull; 4 min</span>
            </div>
          </a>'''.format(
        slug=slug, img_cls=img_cls, img_text=html.escape(img_text), tag=html.escape(tag),
        short_title=html.escape(short_title), date_short=date_short
    )

    # Insere logo apos <div class="latest-list">
    new_idx, n = re.subn(r'(<div class="latest-list">\s*\n\s*)', r'\1          ' + new_card + '\n          ', idx, count=1)
    if n > 0:
        with open(INDEX_FILE, 'w', encoding='utf-8', newline='') as f:
            f.write(new_idx)
        return True
    return False


def main():
    parser = argparse.ArgumentParser(description='Gera post HTML do Noticia Reality a partir de .txt')
    parser.add_argument('txt_file', help='Caminho para o arquivo .txt')
    parser.add_argument('--category', choices=['lcdlf', 'gh', 'farandula'], help='Categoria (auto-detectada se omitida)')
    parser.add_argument('--color', choices=['red', 'blue', 'purple', 'orange', 'gold', 'green'], help='Cor do hero')
    parser.add_argument('--date', help='Data formato DD de mes de YYYY (default: hoje)')
    parser.add_argument('--slug', help='Slug customizado pro nome do arquivo')
    parser.add_argument('--update-home', action='store_true', help='Adicionar o post na homepage')
    args = parser.parse_args()

    txt_path = Path(args.txt_file)
    if not txt_path.exists():
        print('ERRO: arquivo nao encontrado: ' + str(txt_path))
        sys.exit(1)

    with open(txt_path, 'r', encoding='utf-8') as f:
        raw = f.read()

    filename_no_ext = txt_path.stem

    title, blocks = parse_content(raw)
    if not title:
        title = filename_no_ext.strip()
    title = normalize_title(title)

    category_key = args.category or detect_category(raw, filename_no_ext)
    cat = CATEGORIES[category_key]
    color = args.color or cat['color']

    first_p = next((t for k, t in blocks if k == 'p'), title)
    description = (first_p[:160].rsplit(' ', 1)[0] if len(first_p) > 160 else first_p)
    if len(first_p) > 160:
        description += '...'

    slug = args.slug or slugify(title)
    keywords = ', '.join([cat['name'], cat['tag'], 'reality show', 'noticias', '2026', 'farandula latina'])
    date_str = args.date or format_date()
    date_short = format_date_short()

    body = render_blocks(blocks)
    summary = render_summary(make_summary(blocks))
    cat_anchor = 'gh' if category_key == 'gh' else 'lcdlf'
    out = POST_TEMPLATE.format(
        title=html.escape(title, quote=True),
        description=html.escape(description, quote=True),
        keywords=keywords,
        tag=cat['tag'],
        eyebrow=cat['eyebrow'],
        color=color,
        date=date_str,
        body=body,
        summary=summary,
        cat_anchor=cat_anchor,
    )

    output_path = POSTS_DIR / (slug + '.html')
    with open(output_path, 'w', encoding='utf-8', newline='') as f:
        f.write(out)

    print('=' * 60)
    print('Post criado com sucesso!')
    print('=' * 60)
    print('Arquivo:    ' + str(output_path))
    print('URL:        https://noticiareality.blog/posts/{}.html'.format(slug))
    print('Titulo:     ' + title)
    print('Categoria:  ' + category_key + ' / ' + cat['tag'])
    print('Cor hero:   ' + color)
    print('Data:       ' + date_str)
    print('Paragrafos: ' + str(sum(1 for k, _ in blocks if k == 'p')))
    print('Subtitulos: ' + str(sum(1 for k, _ in blocks if k == 'h2')))

    if args.update_home:
        if update_homepage(slug, title, cat['tag'], color, date_short):
            print('Homepage:   ATUALIZADA (post adicionado em "Ultima hora")')
        else:
            print('Homepage:   nao foi possivel atualizar (verificar manualmente)')

    print('=' * 60)
    print('Proximo passo: cd noticiareality && git add . && git commit -m "novo post" && git push')


if __name__ == '__main__':
    main()
