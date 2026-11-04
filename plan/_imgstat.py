# -*- coding: utf-8 -*-
import sys, io, glob, zipfile, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from PIL import Image
print('--- chapters/images ---')
for f in glob.glob('chapters/images/*.png'):
    im=Image.open(f)
    print(f, im.mode, im.size, 'dpi', im.info.get('dpi'))
    rgb=im.convert('RGB')
    px=list(rgb.getdata())
    colored=sum(1 for r,g,b in px if max(r,g,b)-min(r,g,b)>12)
    dark=sum(1 for r,g,b in px if max(r,g,b)<200)
    print('   colored%%=%.2f dark%%=%.2f colors=%d' % (colored*100/len(px), dark*100/len(px), len(rgb.getcolors(1000000) or [])))
print('--- docx media ---')
z=zipfile.ZipFile('毕业设计论文_导师修改版_第五章扩充格式优化.docx')
for n in z.namelist():
    if n.startswith('word/media/'):
        data=z.read(n)
        im=Image.open(io.BytesIO(data))
        rgb=im.convert('RGB'); px=list(rgb.getdata())
        colored=sum(1 for r,g,b in px if max(r,g,b)-min(r,g,b)>12)
        print(n, im.format, im.mode, im.size, len(data)//1024, 'KB colored%%=%.2f' % (colored*100/len(px)))
