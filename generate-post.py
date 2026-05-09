#!/usr/bin/env python3
"""
Gerador de posts pra Noticia Reality.

Usa o template noticiareality-article-es-v1.html e atualiza o pool JS
do index.html (post novo aparece no topo do feed).

USO:
    python generate-post.py "caminho/arquivo.txt"
    python generate-post.py "arquivo.txt" --slug nome-customizado --update-home
    python generate-post.py "arquivo.txt" --update-hero  (substitui hero principal)

FORMATO DO .txt:
    # HEADLINE: Titulo do post (opcional)
    Texto do corpo. Paragrafos separados por linha em branco.
"""
import sys, re, html as html_lib, argparse, unicodedata, random
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent
POSTS_DIR = ROOT / 'posts'
INDEX = ROOT / 'index.html'
TEMPLATE_FILE = ROOT / 'noticiareality-article-es-v1.html'

CHARACTERS = ['caeli','celinee','curvy','fabio','horacio','jeni','josh',
              'kenny','lorena','luis-coronel','sandra','stefano','veronica','yoridan']

CHAR_EMOJI = {'caeli':'👑','celinee':'💋','curvy':'🔥','fabio':'😈','horacio':'😎',
              'jeni':'🌟','josh':'🎭','kenny':'⚡','lorena':'💔','luis-coronel':'🎤',
              'sandra':'😱','stefano':'🎬','veronica':'💄','yoridan':'🎯'}

CHAR_BG = {'caeli':'linear-gradient(135deg,#4a0080,#c2185b)',
           'celinee':'linear-gradient(135deg,#880e4f,#ad1457)',
           'curvy':'linear-gradient(135deg,#b71c1c,#e65100)',
           'fabio':'linear-gradient(135deg,#1a237e,#283593)',
           'horacio':'linear-gradient(135deg,#3e2723,#5d4037)',
           'jeni':'linear-gradient(135deg,#d4970a,#f9a825)',
           'josh':'linear-gradient(135deg,#4a0080,#7b1fa2)',
           'kenny':'linear-gradient(135deg,#bf360c,#dd2c00)',
           'lorena':'linear-gradient(135deg,#880e4f,#c2185b)',
           'luis-coronel':'linear-gradient(135deg,#311b92,#512da8)',
           'sandra':'linear-gradient(135deg,#0d47a1,#1976d2)',
           'stefano':'linear-gradient(135deg,#004d40,#00695c)',
           'veronica':'linear-gradient(135deg,#ad1457,#d81b60)',
           'yoridan':'linear-gradient(135deg,#33691e,#558b2f)'}

GRADIENTS = ['g1','g2','g3','g4','g5','g6','g7','g8','g9','g10','g11','g12','g13','g14']
ICONS = ['👑','🔥','🎤','😱','💔','😤','🏆','💋','🎬','📺','💰','💍','🎯','📱']
MESES = ['enero','febrero','marzo','abril','mayo','junio','julio','agosto','septiembre','octubre','noviembre','diciembre']


def slugify(text):
    text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('ascii')
    text = re.sub(r'[^\w\s-]', '', text).strip().lower()
    text = re.sub(r'[\s_]+', '-', text)
    return re.sub(r'-+', '-', text)[:90]


def detect_char(slug_or_title):
    s = slug_or_title.lower()
    for c in CHARACTERS:
        if c in s:
            return c
    return None


def parse_txt(raw):
    title = None
    m = re.search(r'^#\s*HEADLINE:\s*(.+)$', raw, re.MULTILINE | re.IGNORECASE)
    if m:
        title = m.group(1).strip()
        raw = (raw[:m.start()] + raw[m.end():]).strip()

    paragraphs = []
    for para in re.split(r'\n\s*\n', raw.strip()):
        para = para.strip()
        if not para or para.startswith('#') or para.startswith('## '):
            continue
        flat = re.sub(r'\s+', ' ', para)
        if len(flat) > 20:
            paragraphs.append(flat)

    return title, paragraphs


def build_article_body(paragraphs, char):
    """Pagina em 2 paginas com lead + ads inline."""
    if not paragraphs:
        paragraphs = ['Esta noticia esta siendo actualizada en tiempo real.']
    half = max(1, len(paragraphs) // 2)
    p1, p2 = paragraphs[:half], paragraphs[half:]

    char_emoji = CHAR_EMOJI.get(char, '🔥')
    char_bg = CHAR_BG.get(char, 'linear-gradient(135deg,#4a0080,#c2185b)')

    def render_page(num, paras, total):
        if not paras:
            return ''
        out = f'    <section class="page-section{" active" if num == 1 else ""}" data-page="{num}">\n'
        for i, p in enumerate(paras):
            cls = ' class="lead"' if (num == 1 and i == 0) else ''
            out += f'      <p{cls}>{p}</p>\n'
            if i == 2 and num == 1:
                out += '''      <div style="margin:24px auto;max-width:300px"><iframe src="/ads/300x250-clean.html" style="width:300px;height:250px;max-width:100%;border:0;background:transparent;display:block" scrolling="no" sandbox="allow-scripts allow-same-origin allow-popups allow-popups-to-escape-sandbox"></iframe></div>\n'''
            if i == 5:
                out += f'''      <figure class="inline-figure">
        <div class="fig-img" style="background:{char_bg}">{char_emoji}</div>
        <figcaption>Imagen ilustrativa de la situacion descrita.</figcaption>
      </figure>\n'''
            if i == 7 and num == 1:
                out += '''      <div style="margin:28px 0"><iframe src="/ads/728x90-clean.html" style="width:728px;height:90px;max-width:100%;border:0;background:transparent;display:block;margin:0 auto" scrolling="no" sandbox="allow-scripts allow-same-origin allow-popups allow-popups-to-escape-sandbox"></iframe></div>\n'''
        if num < total:
            out += f'''      <div style="margin:32px 0;text-align:center"><button onclick="goToPage({num+1})" style="background:var(--hot);color:#fff;border:none;padding:14px 32px;border-radius:30px;font-family:inherit;font-size:14px;font-weight:900;cursor:pointer;text-transform:uppercase;letter-spacing:.5px">Leer pagina {num+1} de {total} →</button></div>\n'''
        out += '    </section>\n'
        return out

    total = 2 if p2 else 1
    return render_page(1, p1, total) + (render_page(2, p2, total) if p2 else '')


def featured_img(char):
    bg = CHAR_BG.get(char, 'linear-gradient(135deg,#4a0080,#c2185b)')
    if char:
        return (f'<div class="featured-img" '
                f'style="background:url(/img/personajes/hero_{char}.jpg) center/cover,{bg};'
                f'background-blend-mode:multiply"></div>')
    return f'<div class="featured-img" style="background:{bg}">{CHAR_EMOJI.get(char, "🔥")}</div>'


def build_post(title, paragraphs, slug, char):
    """Aplica template novo no post."""
    template = TEMPLATE_FILE.read_text(encoding='utf-8')
    h = template

    desc = (paragraphs[0] if paragraphs else title)[:200]
    dek = desc[:180]
    today = datetime.now()
    date_str = f'{today.day} de {MESES[today.month-1]} de {today.year}'

    # Title + meta
    h = re.sub(r'<title>[^<]+</title>', f'<title>{html_lib.escape(title)} | NoticiaReality</title>', h, count=1)
    h = re.sub(r'<meta name="description" content="[^"]+"', f'<meta name="description" content="{html_lib.escape(desc)}"', h, count=1)
    # Breadcrumb
    h = h.replace('<span class="current">La traición que sacudió La Casa de los Famosos 6…</span>',
                  f'<span class="current">{html_lib.escape(title[:60])}{"..." if len(title)>60 else ""}</span>')
    # Article header
    h = re.sub(r'<span class="article-cat">[^<]+</span>', '<span class="article-cat">La Casa 6 · Reality</span>', h, count=1)
    h = re.sub(r'<h1 class="article-title">[^<]+</h1>', f'<h1 class="article-title">{html_lib.escape(title)}</h1>', h, count=1)
    h = re.sub(r'<p class="article-dek">[^<]+</p>', f'<p class="article-dek">{html_lib.escape(dek)}</p>', h, count=1)
    h = re.sub(r'<span class="pub-date">[^<]+</span>', f'<span class="pub-date">Publicado el {date_str} · Actualizado hace 2h</span>', h, count=1)
    # Featured image
    h = re.sub(r'<div class="featured-img"[^>]*>[^<]*</div>', featured_img(char), h, count=1)
    h = re.sub(r'<div class="featured-caption">.*?</div>',
               f'<div class="featured-caption"><span>Imagen ilustrativa: {html_lib.escape(title[:80])}</span><span>Foto: NoticiaReality</span></div>',
               h, count=1, flags=re.DOTALL)
    # Inline leader 728x90 sandboxed
    h = re.sub(r'<div class="inline-leader">\s*<a[^>]*class="inline-leader-ad"[^>]*>.*?</a>\s*</div>',
               '<div class="inline-leader"><iframe src="/ads/728x90-clean.html" style="width:728px;height:90px;max-width:100%;border:0;background:transparent;display:block;margin:0 auto" scrolling="no" sandbox="allow-scripts allow-same-origin allow-popups allow-popups-to-escape-sandbox"></iframe></div>',
               h, count=1, flags=re.DOTALL)
    # Article body
    body = build_article_body(paragraphs, char)
    h = re.sub(r'(<div class="article-body">\s*)(.*?)(\s*</div><!-- /article-body -->)',
               lambda m: m.group(1) + '\n' + body + m.group(3),
               h, count=1, flags=re.DOTALL)
    # Share buttons funcionais
    share_url = f'https://noticiareality.blog/posts/{slug}.html'
    share_text = title.replace('"', '\\"')
    fb = f'https://www.facebook.com/sharer/sharer.php?u={share_url}'
    tw = f'https://twitter.com/intent/tweet?text={html_lib.escape(share_text)}&url={share_url}'
    wa = f'https://api.whatsapp.com/send?text={html_lib.escape(share_text)}%20{share_url}'
    tg = f'https://t.me/share/url?url={share_url}&text={html_lib.escape(share_text)}'
    h = h.replace('<button class="share-btn fb" title="Compartir en Facebook">f</button>',
                  f'<a class="share-btn fb" href="{fb}" target="_blank" rel="noopener">f</a>')
    h = h.replace('<button class="share-btn tw" title="Compartir en X">𝕏</button>',
                  f'<a class="share-btn tw" href="{tw}" target="_blank" rel="noopener">𝕏</a>')
    h = h.replace('<button class="share-btn wa" title="Compartir en WhatsApp">📱</button>',
                  f'<a class="share-btn wa" href="{wa}" target="_blank" rel="noopener">📱</a>')
    h = h.replace('<button class="share-btn tg" title="Compartir en Telegram">✈</button>',
                  f'<a class="share-btn tg" href="{tg}" target="_blank" rel="noopener">✈</a>')

    # Inicio link
    h = h.replace('<a href="#">Inicio</a>', '<a href="/">Inicio</a>')
    # adClick rotacao em onclicks decorativos
    h = h.replace("window.open('#','_blank')",
                  "window.adClick&&window.adClick()||window.open('https://omg10.com/4/10967488','_blank','noopener')")

    # adClick + listener antes de </body>
    if 'window.adClick=function' not in h:
        ad_script = '''
<script>
window.adClick=function(){
  var links=['https://omg10.com/4/10967488','https://omg10.com/4/10967489','https://www.profitablecpmratenetwork.com/dd06dn3nu?key=bb878784d262344eb40ff3dd6b2981b3'];
  window.open(links[Math.floor(Math.random()*links.length)],'_blank','noopener,noreferrer');
};
window.addEventListener('message', function(e){
  if (e.data && e.data.type === 'nr_ad_click') window.adClick();
});
</script>
'''
        h = h.replace('</body>', ad_script + '</body>')

    return h


def update_pool(title, desc, slug, char):
    """Adiciona post no INICIO do array pool (JS) do index.html."""
    if not INDEX.exists():
        return False
    h = INDEX.read_text(encoding='utf-8')

    # Constroi entry JSON do pool
    if char:
        img_html = f"<img src='/img/personajes/card_{char}.jpg' style='width:100%;height:100%;object-fit:cover'>"
        ico = ''
    else:
        img_html = ''
        ico = random.choice(ICONS)
    g = random.choice(GRADIENTS)

    # Sanitiza
    safe_title = re.sub(r'[\x00-\x1f]', '', title).replace('"', "'")
    safe_desc = re.sub(r'[\x00-\x1f]', '', desc[:130]).replace('"', "'")

    entry = (
        '{"cat": "La Casa 6", "color": "var(--hot)", '
        f'"ico": "{ico}", "img": "{img_html}", "g": "{g}", '
        f'"title": "{safe_title}", "desc": "{safe_desc}", '
        f'"time": "hace 5 minutos", "views": "12k", '
        f'"url": "/posts/{slug}.html"}}'
    )

    # Insere no inicio do pool
    pat = re.compile(r'(const pool=\[)', re.MULTILINE)
    new = pat.sub(r'\1' + entry + ',', h, count=1)
    if new == h:
        return False
    INDEX.write_text(new, encoding='utf-8')
    return True


def update_hero(title, desc, slug, char):
    """Substitui o hero principal pelo post novo."""
    if not INDEX.exists() or not char:
        return False
    h = INDEX.read_text(encoding='utf-8')

    bg = f"background:url(/img/personajes/hero_{char}.jpg) center/cover"
    cat_label = 'La Casa 6 · Polémica'
    emoji = CHAR_EMOJI.get(char, '🔥')

    new_main = f'''<a href="/posts/{slug}.html" class="card hero-main">
      <div class="fake-img g1" style="{bg};aspect-ratio:16/9;position:relative">
        <div style="position:absolute;inset:0;background:linear-gradient(180deg,transparent 50%,rgba(0,0,0,.45));pointer-events:none"></div>
        <div style="position:absolute;bottom:14px;left:18px;color:#fff;font-size:11px;background:rgba(0,0,0,.55);padding:4px 10px;border-radius:3px;font-weight:700;letter-spacing:.5px;backdrop-filter:blur(4px)">📷 GALERÍA · DESTAQUE</div>
      </div>
      <div class="card-body">
        <span class="cat bbb">{cat_label}</span>
        <h2>{emoji} {html_lib.escape(title)}</h2>
        <p>{html_lib.escape(desc[:200])}</p>
        <div class="meta">🕐 hace 5 minutos · 4 min · 📊 nuevo</div>
      </div>
    </a>'''

    new = re.sub(r'<a[^>]+class="card hero-main"[^>]*>.*?</a>(?=\s*<a[^>]*class="card hero-side")',
                 new_main, h, count=1, flags=re.DOTALL)
    if new != h:
        INDEX.write_text(new, encoding='utf-8')
        return True
    return False


def main():
    parser = argparse.ArgumentParser(description='Gera post Noticia Reality a partir de .txt')
    parser.add_argument('txt_file')
    parser.add_argument('--slug')
    parser.add_argument('--update-home', action='store_true', help='Adiciona no pool do home (default: true)')
    parser.add_argument('--update-hero', action='store_true', help='Substitui hero principal do home')
    parser.add_argument('--no-update-home', action='store_true')
    args = parser.parse_args()

    txt_path = Path(args.txt_file)
    if not txt_path.exists():
        print('ERRO: arquivo nao encontrado:', txt_path)
        sys.exit(1)

    raw = txt_path.read_text(encoding='utf-8')
    title, paragraphs = parse_txt(raw)
    if not title:
        title = txt_path.stem.strip()

    slug = args.slug or slugify(title)
    char = detect_char(slug) or detect_char(title)

    # Build post
    out = build_post(title, paragraphs, slug, char)
    output_path = POSTS_DIR / (slug + '.html')
    output_path.write_text(out, encoding='utf-8')

    print('=' * 60)
    print(f'Post criado: {output_path}')
    print(f'URL:        https://noticiareality.blog/posts/{slug}.html')
    print(f'Titulo:     {title}')
    print(f'Personagem: {char or "nenhum detectado"}')
    print(f'Paragrafos: {len(paragraphs)}')

    # Update home (default ligado)
    if not args.no_update_home:
        desc = (paragraphs[0] if paragraphs else title)[:200]
        if update_pool(title, desc, slug, char):
            print('Pool home: ATUALIZADO (post no topo do feed)')
        else:
            print('Pool home: nao atualizado (verificar index.html)')

    if args.update_hero and char:
        if update_hero(title, desc, slug, char):
            print('Hero home: ATUALIZADO (post novo no card principal)')
        else:
            print('Hero home: nao atualizado (verificar)')

    print('=' * 60)
    print('Para publicar: git add . && git commit -m "novo post" && git push')


if __name__ == '__main__':
    main()
