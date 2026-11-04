# -*- coding: utf-8 -*-
import glob, os, zipfile
from docx import Document
from docx.oxml.ns import qn

for f in sorted(glob.glob('*.docx')):
    try:
        d = Document(f)
        paras = d.paragraphs
        imgs = [r for r in d.part.rels.values() if 'image' in r.reltype]
        print(f"\n=== {f} | size={os.path.getsize(f)/1024:.0f}KB | paras={len(paras)} tables={len(d.tables)} images={len(imgs)}")
        # first non-empty paragraphs
        ne = [p.text.strip() for p in paras if p.text.strip()][:6]
        print('  head:', ' | '.join(x[:40] for x in ne))
        # sections
        for i, s in enumerate(d.sections):
            sectPr = s._sectPr
            pg = sectPr.find(qn('w:pgNumType'))
            print(f'  section{i}: start={s.start_type} pgNumType={pg.attrib if pg is not None else None}')
        # media files
        with zipfile.ZipFile(f) as z:
            media = [n for n in z.namelist() if n.startswith('word/media/')]
            print('  media:', len(media), media[:12])
    except Exception as e:
        print(f, 'ERR', e)
