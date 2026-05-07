#!/usr/bin/env python3
"""
Processa as imagens em ImagensPersonagens/ e cria 2 versoes pra cada:
- hero_<nome>.jpg (1280x720) - banner grande do post
- card_<nome>.jpg (560x360) - thumbnail dos feed-cards

Crop inteligente focado no rosto (heuristica: terco superior em fotos verticais).
Salva em img/personajes/

Uso: python prepare_images.py
"""
from PIL import Image
from pathlib import Path

ROOT = Path(__file__).parent
SOURCE_DIR = ROOT / 'ImagensPersonagens'
OUT_DIR = ROOT / 'img' / 'personajes'
OUT_DIR.mkdir(parents=True, exist_ok=True)


def smart_crop(img, target_w, target_h):
    """Crop centralizado, com heuristica pra fotos verticais (rosto no terco superior)."""
    src_w, src_h = img.size
    target_ratio = target_w / target_h
    src_ratio = src_w / src_h

    if abs(src_ratio - target_ratio) < 0.01:
        # Ja esta na proporcao certa
        return img.resize((target_w, target_h), Image.LANCZOS)

    if src_ratio > target_ratio:
        # Source mais largo: corta horizontal (centraliza)
        new_w = int(src_h * target_ratio)
        offset_x = (src_w - new_w) // 2
        crop = img.crop((offset_x, 0, offset_x + new_w, src_h))
    else:
        # Source mais alto: corta vertical (foca no terco superior pro rosto)
        new_h = int(src_w / target_ratio)
        # 15% do topo (rosto geralmente fica entre 10-40% da altura em fotos verticais)
        offset_y = max(0, int((src_h - new_h) * 0.10))
        crop = img.crop((0, offset_y, src_w, offset_y + new_h))

    return crop.resize((target_w, target_h), Image.LANCZOS)


def process_image(filepath):
    name = filepath.stem.lower().replace(' ', '-')
    print(f'Processando {filepath.name}...')

    try:
        img = Image.open(filepath).convert('RGB')

        # Hero: 1280x720 (16:9, pro article-hero do post)
        hero = smart_crop(img, 1280, 720)
        hero_path = OUT_DIR / f'hero_{name}.jpg'
        hero.save(hero_path, 'JPEG', quality=88, optimize=True)

        # Card: 560x360 (~16:10 pra feed-card)
        card = smart_crop(img, 560, 360)
        card_path = OUT_DIR / f'card_{name}.jpg'
        card.save(card_path, 'JPEG', quality=85, optimize=True)

        print(f'  OK -> hero_{name}.jpg + card_{name}.jpg')
        return name
    except Exception as e:
        print(f'  ERRO: {e}')
        return None


def main():
    if not SOURCE_DIR.exists():
        print('ERRO: pasta', SOURCE_DIR, 'nao existe')
        return

    chars = []
    for fp in sorted(SOURCE_DIR.glob('*.png')):
        n = process_image(fp)
        if n:
            chars.append(n)
    for fp in sorted(SOURCE_DIR.glob('*.jpg')):
        n = process_image(fp)
        if n:
            chars.append(n)

    print()
    print('=' * 60)
    print(f'Pronto: {len(chars)} personagens processados')
    print('Personagens disponiveis:', ', '.join(chars))
    print('Salvos em:', OUT_DIR)


if __name__ == '__main__':
    main()
