# -*- coding: utf-8 -*-
"""为论文截图添加细黑色矩形边框,不改变截图内容与尺寸。"""
from pathlib import Path
from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[1]
SHOT_DIR = ROOT / 'thesis_shots'
for path in sorted(SHOT_DIR.glob('*.png')):
    with Image.open(path) as src:
        image = src.convert('RGB')
        bordered = ImageOps.expand(image, border=2, fill='black')
        bordered.save(path, format='PNG', optimize=True)
        print(f'已加边框: {path.name} {image.size} -> {bordered.size}')
