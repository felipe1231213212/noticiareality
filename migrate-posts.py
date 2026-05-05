#!/usr/bin/env python3
"""
Migra posts antigos pro novo template G1 long-form.

Le cada arquivo HTML em posts/, extrai titulo + conteudo (h2/p),
e regenera com o novo template do generate-post.py.

Uso: python migrate-posts.py
"""

import re
import html as html_lib
import importlib.util
from pathlib import Path
from datetime import datetime

# Importa o generate-post.py
spec = importlib.util.spec_from_file_location("gen", Path(__file__).parent / "generate-post.py")
gen = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gen)

POSTS_DIR = Path(__file__).parent / 'posts'

SKIP_FILES = {'_TEMPLATE.html', 'triangulo-amoroso-destruye-la-casa.html'}


def extract_post(html_text):
    """Extrai title, blocks, color, tag, date de um post HTML existente."""

    # Title
    title_m = re.search(r'<h1[^>]*>(.+?)</h1>', html_text, re.DOTALL)
    title = title_m.group(1).strip() if title_m else 'Post sin titulo'
    title = re.sub(r'<[^>]+>', '', title)
    title = html_lib.unescape(title)

    # Color (post-hero-RED, post-hero-BLUE, etc)
    color_m = re.search(r'post-hero post-hero-(\w+)', html_text)
    color = color_m.group(1) if color_m else 'red'

    # Tag
    tag_m = re.search(r'<span class="post-hero-tag">([^<]+)</span>', html_text)
    tag = tag_m.group(1).strip() if tag_m else 'LCDLF 6'

    # Date
    date_m = re.search(r'<div class="post-meta">\s*<span>([^<]+)</span>', html_text)
    date = date_m.group(1).strip() if date_m else None

    # Article content - everything inside <article> until <div class="share-bar"> or </article>
    art_m = re.search(r'<article[^>]*>(.+?)(?:<div class="share-bar">|<div class="article-tags">|<div class="ad-banner|</article>)',
                       html_text, re.DOTALL)
    if not art_m:
        return None

    content = art_m.group(1)

    # Extract h2 and p blocks (em ordem)
    blocks = []
    for m in re.finditer(r'<(h2|p)\b[^>]*>(.+?)</\1>', content, re.DOTALL):
        kind = m.group(1)
        text = m.group(2).strip()
        # Skip if its post-meta or hero (already extracted)
        if 'post-hero' in m.group(0) or 'post-meta' in m.group(0):
            continue
        # Strip nested tags but keep <strong>
        text = re.sub(r'<(?!/?strong\b)[^>]+>', '', text)
        text = html_lib.unescape(text)
        text = re.sub(r'\s+', ' ', text).strip()
        if text:
            # Remove <strong> tags - generate-post.py vai re-aplicar bold
            text = re.sub(r'</?strong>', '', text)
            blocks.append((kind, text))

    # Detect category
    cat_key = 'gh' if any(k in (title + tag).lower() for k in ['gran hermano', 'generacion dorada', 'pincoya', 'tamara', 'nazareno', 'brian']) else 'lcdlf'

    return {
        'title': title,
        'blocks': blocks,
        'color': color,
        'tag': tag,
        'date': date,
        'cat_key': cat_key,
    }


def regenerate_post(filepath, data):
    """Regenera o post com novo template."""
    cat = gen.CATEGORIES[data['cat_key']]
    color = data['color']
    title = data['title']
    blocks = data['blocks']

    # First paragraph for description/subtitle
    first_p = next((t for k, t in blocks if k == 'p'), title)
    description = first_p[:160].rsplit(' ', 1)[0]
    if len(first_p) > 160: description += '...'

    subtitle = first_p[:200].rsplit(' ', 1)[0]
    if len(first_p) > 200: subtitle += '...'

    slug = filepath.stem

    # Hero text
    hero_words = title.split()
    if len(hero_words) >= 4:
        hero_text = ' '.join(hero_words[:3]).upper()
    else:
        hero_text = title.upper()
    if len(hero_text) > 30:
        hero_text = hero_text[:30]

    # Reading time
    word_count = sum(len(t.split()) for k, t in blocks)
    reading_time = max(2, word_count // 200)

    # Date
    date_str = data['date'] or gen.format_date()
    date_iso = datetime.now().strftime('%Y-%m-%dT%H:%M:%S')

    # Body
    body = gen.render_blocks(blocks)
    summary = gen.render_summary(gen.make_summary(blocks))

    keywords = ', '.join([cat['name'], cat['tag'], 'reality show', 'noticias', '2026', 'farandula latina'])
    title_url = title.replace(' ', '%20').replace('"', '')[:100]
    cat_anchor = 'gh' if data['cat_key'] == 'gh' else 'lcdlf'

    out = gen.POST_TEMPLATE.format(
        title=html_lib.escape(title, quote=True),
        title_url=title_url,
        description=html_lib.escape(description, quote=True),
        subtitle=html_lib.escape(subtitle, quote=True),
        hero_text=html_lib.escape(hero_text, quote=False),
        reading_time=reading_time,
        slug=slug,
        date_iso=date_iso,
        keywords=keywords,
        tag=cat['tag'],
        eyebrow=cat['eyebrow'],
        color=color,
        date=date_str,
        body=body,
        summary=summary,
        cat_anchor=cat_anchor,
    )

    with open(filepath, 'w', encoding='utf-8', newline='') as f:
        f.write(out)


def main():
    files = [f for f in POSTS_DIR.glob('*.html') if f.name not in SKIP_FILES]
    print(f'Migrando {len(files)} posts...\n')
    for f in files:
        with open(f, 'r', encoding='utf-8') as fp:
            html_text = fp.read()
        data = extract_post(html_text)
        if not data:
            print(f'  SKIP: {f.name} (sem conteudo extraivel)')
            continue
        try:
            regenerate_post(f, data)
            print(f'  OK: {f.name} ({len(data["blocks"])} blocos)')
        except Exception as e:
            print(f'  ERRO: {f.name} - {e}')


if __name__ == '__main__':
    main()
